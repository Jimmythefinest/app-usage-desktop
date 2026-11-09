"""Company edition server (multi-company): manager accounts, enrolment, ingest, analytics, dashboard."""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Persistent storage: one SQLite file in a fixed folder (mount/back up this folder in production).
DATA_DIR = Path(os.getenv("AU_DATA_DIR", Path.home() / ".local" / "share" / "app_usage_server"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = os.getenv("AU_DB", str(DATA_DIR / "server.db"))
ALLOW_SIGNUP = os.getenv("AU_ALLOW_SIGNUP", "1") == "1"  # set to 0 once your companies exist
STATIC = Path(__file__).parent / "static"
SESSION_DAYS = 7
LABELS = ("productive", "neutral", "unproductive")
SEED = {"code": "productive", "pycharm": "productive", "idea": "productive", "gnome-terminal": "productive",
        "windowsterminal": "productive", "libreoffice": "productive", "excel": "productive", "winword": "productive",
        "spotify": "unproductive", "steam": "unproductive", "vlc": "unproductive", "netflix": "unproductive"}
SCHEMA = """
CREATE TABLE IF NOT EXISTS companies(id INTEGER PRIMARY KEY, name TEXT NOT NULL, join_code TEXT UNIQUE NOT NULL,
  capture_titles INTEGER DEFAULT 0, require_approval INTEGER DEFAULT 1, created TEXT);
CREATE TABLE IF NOT EXISTS managers(id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, email TEXT UNIQUE NOT NULL,
  pw TEXT NOT NULL, created TEXT);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, manager_id INTEGER NOT NULL, expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS employees(id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL, name TEXT NOT NULL,
  email TEXT, status TEXT NOT NULL, created TEXT);
CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, token_hash TEXT UNIQUE,
  hostname TEXT, os TEXT, enrolled_at TEXT, last_seen TEXT, revoked INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS activities(device_id INTEGER, id TEXT, app TEXT, start TEXT, stop TEXT,
  elapsed INTEGER, focused INTEGER, titles TEXT, PRIMARY KEY(device_id, id));
CREATE INDEX IF NOT EXISTS act_start ON activities(start);
CREATE TABLE IF NOT EXISTS categories(company_id INTEGER, app TEXT, label TEXT, PRIMARY KEY(company_id, app));
"""


def conn():
    c = sqlite3.connect(DB_PATH, timeout=10)
    c.row_factory = sqlite3.Row
    return c


with conn() as _c:
    _c.execute("PRAGMA journal_mode=WAL")
    _c.executescript(SCHEMA)

app = FastAPI(title="App Usage - Company Edition")
now_iso = lambda: datetime.now().isoformat(timespec="seconds")
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
norm = lambda a: (a or "").lower().removesuffix(".exe")


# ---------- passwords & sessions ----------
def _scrypt(pw, salt):
    return hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1).hex()


def hash_pw(pw):
    salt = secrets.token_bytes(16)
    return salt.hex() + "$" + _scrypt(pw, salt)


def check_pw(pw, stored):
    salt, h = stored.split("$")
    return hmac.compare_digest(_scrypt(pw, bytes.fromhex(salt)), h)


FAILS = {}  # email -> recent failure timestamps (simple in-memory brute-force limit)


def new_session(c, manager_id):
    token = secrets.token_urlsafe(32)
    c.execute("INSERT INTO sessions VALUES (?,?,?)", (sha(token), manager_id, time.time() + SESSION_DAYS * 86400))
    return token


def bearer(h):
    return h.removeprefix("Bearer ").strip()


def manager(authorization: str = Header("")):
    with conn() as c:
        r = c.execute("""SELECT m.*, s.expires FROM sessions s JOIN managers m ON m.id=s.manager_id
            WHERE s.token_hash=?""", (sha(bearer(authorization)),)).fetchone()
    if not r or r["expires"] < time.time():
        raise HTTPException(401, "please log in")
    return r


def device(authorization: str = Header("")):
    with conn() as c:
        r = c.execute("""SELECT d.*, e.status, e.company_id, e.name AS emp_name FROM devices d
            JOIN employees e ON e.id=d.employee_id
            WHERE d.token_hash=? AND d.revoked=0 AND e.status!='rejected'""", (sha(bearer(authorization)),)).fetchone()
    if not r:
        raise HTTPException(401, "unknown or revoked device")
    return r


def policy_of(co):
    return {"org_name": co["name"], "capture_titles": bool(co["capture_titles"])}


def company_row(c, cid):
    return c.execute("SELECT * FROM companies WHERE id=?", (cid,)).fetchone()


# ---------- public: manager accounts ----------
class SignupIn(BaseModel):
    company_name: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


@app.post("/api/v1/signup")
def signup(b: SignupIn):
    if not ALLOW_SIGNUP:
        raise HTTPException(403, "sign-ups are disabled on this server")
    email = b.email.strip().lower()
    if "@" not in email or len(b.password) < 10 or not b.company_name.strip():
        raise HTTPException(400, "need a company name, a valid email and a password of 10+ characters")
    with conn() as c:
        if c.execute("SELECT 1 FROM managers WHERE email=?", (email,)).fetchone():
            raise HTTPException(409, "that email already has an account")
        code = secrets.token_hex(4).upper()
        cid = c.execute("INSERT INTO companies(name,join_code,created) VALUES (?,?,?)",
                        (b.company_name.strip()[:100], code, now_iso())).lastrowid
        mid = c.execute("INSERT INTO managers(company_id,email,pw,created) VALUES (?,?,?,?)",
                        (cid, email, hash_pw(b.password), now_iso())).lastrowid
        c.executemany("INSERT INTO categories VALUES (?,?,?)", [(cid, a, l) for a, l in SEED.items()])
        return {"token": new_session(c, mid)}


@app.post("/api/v1/login")
def login(b: LoginIn):
    email = b.email.strip().lower()
    recent = [t for t in FAILS.get(email, []) if t > time.time() - 900]
    if len(recent) >= 5:
        raise HTTPException(429, "too many failed attempts; try again in 15 minutes")
    with conn() as c:
        m = c.execute("SELECT * FROM managers WHERE email=?", (email,)).fetchone()
        if not m or not check_pw(b.password, m["pw"]):
            FAILS[email] = recent + [time.time()]
            raise HTTPException(401, "wrong email or password")
        FAILS.pop(email, None)
        return {"token": new_session(c, m["id"])}


@app.post("/api/v1/logout")
def logout(authorization: str = Header("")):
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE token_hash=?", (sha(bearer(authorization)),))
    return {"ok": True}


# ---------- device-facing ----------
class EnrollIn(BaseModel):
    company_id: str
    name: str
    email: str = ""
    hostname: str = ""
    os: str = ""


class Act(BaseModel):
    id: str
    app: str
    start: str
    end: str
    elapsed_seconds: int = 0
    focused_seconds: int = 0
    titles: List[str] = []


class IngestIn(BaseModel):
    activities: List[Act]


@app.get("/api/v1/company/{code}")
def company_info(code: str):
    with conn() as c:
        co = c.execute("SELECT * FROM companies WHERE join_code=?", (code.strip().upper(),)).fetchone()
    if not co:
        raise HTTPException(404, "unknown company ID")
    return {"name": co["name"], "policy": policy_of(co)}


@app.post("/api/v1/enroll")
def enroll(b: EnrollIn):
    if not b.name.strip():
        raise HTTPException(400, "name is required")
    token = secrets.token_urlsafe(32)
    with conn() as c:
        co = c.execute("SELECT * FROM companies WHERE join_code=?", (b.company_id.strip().upper(),)).fetchone()
        if not co:
            raise HTTPException(404, "unknown company ID")
        status = "pending" if co["require_approval"] else "active"
        eid = c.execute("INSERT INTO employees(company_id,name,email,status,created) VALUES (?,?,?,?,?)",
                        (co["id"], b.name.strip()[:100], b.email.strip()[:150], status, now_iso())).lastrowid
        c.execute("INSERT INTO devices(employee_id,token_hash,hostname,os,enrolled_at) VALUES (?,?,?,?,?)",
                  (eid, sha(token), b.hostname[:100], b.os[:30], now_iso()))
    return {"token": token, "status": status, "employee": b.name.strip(), "policy": policy_of(co)}


@app.get("/api/v1/me")
def me(dev=Depends(device)):
    with conn() as c:
        co = company_row(c, dev["company_id"])
    return {"status": dev["status"], "employee": dev["emp_name"], "policy": policy_of(co)}


@app.post("/api/v1/ingest")
def ingest(b: IngestIn, dev=Depends(device)):
    with conn() as c:
        co = company_row(c, dev["company_id"])
        pol = policy_of(co)  # enforced here too, whatever the agent sends
        c.execute("UPDATE devices SET last_seen=? WHERE id=?", (now_iso(), dev["id"]))
        if dev["status"] != "active":
            return {"ok": False, "status": dev["status"], "policy": pol}
        for a in b.activities[:5000]:
            titles = json.dumps(a.titles[:20]) if pol["capture_titles"] else "[]"
            c.execute("""INSERT INTO activities VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(device_id,id) DO UPDATE SET stop=excluded.stop, elapsed=excluded.elapsed,
                focused=excluded.focused, titles=excluded.titles""",
                      (dev["id"], a.id, a.app[:100], a.start, a.end, a.elapsed_seconds, a.focused_seconds, titles))
    return {"ok": True, "status": "active", "policy": pol}


@app.post("/api/v1/unenroll")
def unenroll(dev=Depends(device)):
    with conn() as c:
        c.execute("UPDATE devices SET revoked=1 WHERE id=?", (dev["id"],))
    return {"ok": True}


# ---------- manager-facing (always scoped to the manager's own company) ----------
class CategoryIn(BaseModel):
    app: str
    label: str


class CompanyIn(BaseModel):
    name: str
    capture_titles: bool
    require_approval: bool


def own_employee(c, m, eid):
    e = c.execute("SELECT * FROM employees WHERE id=? AND company_id=?", (eid, m["company_id"])).fetchone()
    if not e:
        raise HTTPException(404, "no such employee")
    return e


@app.get("/api/v1/manager/company")
def get_company(m=Depends(manager)):
    with conn() as c:
        co = company_row(c, m["company_id"])
    return {"name": co["name"], "join_code": co["join_code"], "capture_titles": bool(co["capture_titles"]),
            "require_approval": bool(co["require_approval"]), "email": m["email"]}


@app.put("/api/v1/manager/company")
def set_company(b: CompanyIn, m=Depends(manager)):
    with conn() as c:
        c.execute("UPDATE companies SET name=?, capture_titles=?, require_approval=? WHERE id=?",
                  (b.name.strip()[:100] or "Company", int(b.capture_titles), int(b.require_approval), m["company_id"]))
    return get_company(m)


def cat_map(c, cid):
    return {r["app"]: r["label"] for r in c.execute("SELECT app,label FROM categories WHERE company_id=?", (cid,))}


@app.get("/api/v1/manager/employees")
def employees(m=Depends(manager)):
    today = datetime.now().strftime("%Y-%m-%d")
    out = []
    with conn() as c:
        cm = cat_map(c, m["company_id"])
        for e in c.execute("SELECT * FROM employees WHERE company_id=? AND status!='rejected' ORDER BY name",
                           (m["company_id"],)).fetchall():
            devs = c.execute("SELECT hostname,os,last_seen,revoked FROM devices WHERE employee_id=?", (e["id"],)).fetchall()
            rows = c.execute("""SELECT a.app, SUM(a.focused) s FROM activities a JOIN devices d ON d.id=a.device_id
                WHERE d.employee_id=? AND a.start>=? GROUP BY a.app""", (e["id"], today)).fetchall()
            tot = sum(r["s"] for r in rows)
            prod = sum(r["s"] for r in rows if cm.get(norm(r["app"])) == "productive")
            out.append({"id": e["id"], "name": e["name"], "email": e["email"], "status": e["status"],
                        "devices": [dict(d) for d in devs],
                        "last_seen": max((d["last_seen"] or "" for d in devs), default=""),
                        "today_seconds": tot, "today_productive": prod})
    return out


@app.post("/api/v1/manager/employees/{eid}/approve")
def approve(eid: int, m=Depends(manager)):
    with conn() as c:
        own_employee(c, m, eid)
        c.execute("UPDATE employees SET status='active' WHERE id=?", (eid,))
    return {"ok": True}


@app.post("/api/v1/manager/employees/{eid}/reject")
def reject(eid: int, m=Depends(manager)):
    with conn() as c:
        own_employee(c, m, eid)
        c.execute("UPDATE employees SET status='rejected' WHERE id=?", (eid,))
    return {"ok": True}


@app.delete("/api/v1/manager/employees/{eid}")
def delete_employee(eid: int, m=Depends(manager)):
    with conn() as c:
        own_employee(c, m, eid)
        c.execute("DELETE FROM activities WHERE device_id IN (SELECT id FROM devices WHERE employee_id=?)", (eid,))
        c.execute("DELETE FROM devices WHERE employee_id=?", (eid,))
        c.execute("DELETE FROM employees WHERE id=?", (eid,))
    return {"ok": True}


@app.get("/api/v1/manager/employees/{eid}/summary")
def summary(eid: int, days: int = 7, m=Depends(manager)):
    since = (datetime.now() - timedelta(days=max(1, min(days, 90)) - 1)).strftime("%Y-%m-%d")
    with conn() as c:
        e = own_employee(c, m, eid)
        cm = cat_map(c, m["company_id"])
        rows = c.execute("""SELECT substr(a.start,1,10) day, a.app, SUM(a.focused) s FROM activities a
            JOIN devices d ON d.id=a.device_id WHERE d.employee_id=? AND a.start>=? GROUP BY day, a.app""",
                         (eid, since)).fetchall()
    per_day, apps = {}, {}
    for r in rows:
        k = cm.get(norm(r["app"]), "neutral")
        d = per_day.setdefault(r["day"], {"day": r["day"], **{x: 0 for x in LABELS}})
        d[k] += r["s"]
        a = apps.setdefault(r["app"], {"app": r["app"], "category": k, "seconds": 0})
        a["seconds"] += r["s"]
    return {"employee": e["name"], "days": sorted(per_day.values(), key=lambda x: x["day"]),
            "top_apps": sorted(apps.values(), key=lambda x: -x["seconds"])[:15]}


@app.put("/api/v1/manager/categories")
def set_category(b: CategoryIn, m=Depends(manager)):
    if b.label not in LABELS:
        raise HTTPException(400, "label must be one of " + ", ".join(LABELS))
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO categories VALUES (?,?,?)", (m["company_id"], norm(b.app), b.label))
    return {"ok": True}


@app.get("/")
def dashboard():
    return FileResponse(STATIC / "dashboard.html")
