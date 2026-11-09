"""Company edition agent logic, shared by the CLI and the GUI.

Flow: an employee enters a company ID (given by their manager) and their own name/email, agrees to the
policy, and this computer is linked to that company's server. Activity summaries are then uploaded.
"""
import json
import platform
import socket
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

from app_usage_cli import builder, config

# Only these fields ever leave the machine (no pid, exe path, window id, or commands).
FIELDS = ("id", "app", "start", "end", "elapsed_seconds", "focused_seconds", "titles")


class ServerError(Exception):
    def __init__(self, message, code=0):
        super().__init__(message)
        self.code = code


def _call(server, method, path, body=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(server.rstrip("/") + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            detail = json.loads(raw).get("detail", raw)
        except ValueError:
            detail = raw
        raise ServerError(str(detail)[:200], e.code)
    except urllib.error.URLError as e:
        raise ServerError(f"cannot reach {server} ({e.reason})")
    except (TimeoutError, OSError, ValueError) as e:
        raise ServerError(f"cannot reach {server} ({e})")


# ---------- helpers ----------
def normalize_server(server):
    server = (server or "").strip().rstrip("/")
    if server and "://" not in server:
        server = "http://" + server
    return server


def parse_company_id(text, server=""):
    """Accepts 'ABCD1234' or the single-string form 'ABCD1234@https://company.example.com'."""
    text = (text or "").strip()
    if "@" in text:
        text, _, server = text.partition("@")
    return text.strip().upper(), normalize_server(server)


def info():
    """The stored enrolment, or None."""
    return config.load_config().get("company")


def _update(**fields):
    cfg = config.load_config()
    if "company" in cfg:
        cfg["company"].update(fields)
        config.save_config(cfg)


def describe(policy):
    lines = [f"This program records and sends to {policy['org_name']}:",
             "  - which application was in the foreground, and for how long",
             "  - start/end times of each activity (idle and locked time is not counted)"]
    lines.append("  - window titles (these can include document or web page names)" if policy.get("capture_titles")
                 else "  (window titles are NOT collected)")
    lines += ["",
              "It does not record keystrokes, screenshots, or file contents.",
              "Nothing from before you join is ever sent.",
              "You can preview exactly what is sent, or leave the company, at any time."]
    return "\n".join(lines)


# ---------- enrolment ----------
def lookup(server, company_id):
    """Check a company ID. Returns {'name': ..., 'policy': ...}; raises ServerError."""
    code, server = parse_company_id(company_id, server)
    if not server:
        raise ServerError("enter the server address your manager gave you")
    if not code:
        raise ServerError("enter your company ID")
    return _call(server, "GET", f"/api/v1/company/{code}")


def join(server, company_id, name, email=""):
    """Create this employee's profile and link this computer. Returns the stored enrolment."""
    if info():
        raise ServerError("this computer is already enrolled; leave the company first")
    code, server = parse_company_id(company_id, server)
    name = (name or "").strip()
    if not name:
        raise ServerError("enter your name")
    res = _call(server, "POST", "/api/v1/enroll",
                {"company_id": code, "name": name, "email": (email or "").strip(),
                 "hostname": socket.gethostname(), "os": platform.system()})
    now = datetime.now()
    cfg = config.load_config()
    cfg["company"] = {"server": server, "token": res["token"], "employee": res["employee"],
                      "email": (email or "").strip(), "company_name": res["policy"]["org_name"],
                      "status": res["status"], "policy": res["policy"],
                      "enrolled_at": now.isoformat(timespec="seconds"),
                      "since": now.date().isoformat()}  # nothing from before enrolment is ever uploaded
    config.save_config(cfg)
    return cfg["company"]


def refresh():
    """Ask the server for this device's current status (e.g. approved yet?). Returns the stored enrolment."""
    c = info()
    if not c:
        return None
    try:
        res = _call(c["server"], "GET", "/api/v1/me", token=c["token"])
        _update(status=res["status"], policy=res["policy"], company_name=res["policy"]["org_name"], reachable=True)
    except ServerError as e:
        if e.code == 401:
            _update(status="revoked", reachable=True)
        else:
            _update(reachable=False)
    return info()


def unenroll():
    """Stop uploading and unlink this computer. Returns a note if the server could not be told."""
    c = info()
    if not c:
        return None
    note = None
    try:
        _call(c["server"], "POST", "/api/v1/unenroll", {}, c["token"])
    except ServerError as e:
        if e.code != 401:
            note = f"The server could not be told ({e}). Your manager can remove this device there."
    cfg = config.load_config()
    cfg.pop("company", None)
    config.save_config(cfg)
    return note


# ---------- uploading ----------
def collect(c):
    out, day = [], date.fromisoformat(c["since"])
    while day <= date.today():
        f = config.get_analytics_dir() / f"{day}.jsonl"
        if f.exists():
            for a in builder.build(builder.read_jsonl(f), []):
                if a["start"] < c["enrolled_at"]:
                    continue
                row = {k: a[k] for k in FIELDS if k in a}
                if not c["policy"].get("capture_titles"):
                    row["titles"] = []
                out.append(row)
        day += timedelta(days=1)
    return out


def sync(force=False):
    """Upload everything recorded since enrolment (the server de-duplicates by activity id).

    Always returns a dict: {'ok', 'sent', 'status', 'message'}. The tracker's heartbeat events keep the
    open activity's duration current, so a forced sync is accurate to within about 30 seconds.
    """
    c = info()
    if not c:
        return {"ok": False, "sent": 0, "status": "none", "message": "Not enrolled."}
    acts = collect(c)
    res = {}
    try:
        for i in range(0, max(len(acts), 1), 500):  # always send once: it doubles as a heartbeat
            res = _call(c["server"], "POST", "/api/v1/ingest", {"activities": acts[i:i + 500]}, c["token"])
    except ServerError as e:
        if e.code == 401:
            _update(status="revoked")
            return {"ok": False, "sent": 0, "status": "revoked",
                    "message": "This computer is no longer authorised by the company; uploads stopped."}
        _update(reachable=False)
        return {"ok": False, "sent": 0, "status": c.get("status", "?"),
                "message": f"Upload failed ({e}). It will retry automatically."}
    status = res.get("status", "active")
    _update(status=status, policy=res["policy"], reachable=True,
            since=(date.today() - timedelta(days=1)).isoformat() if res.get("ok") else c["since"],
            last_sync=datetime.now().isoformat(timespec="seconds"),
            last_sent=len(acts) if res.get("ok") else 0)
    if not res.get("ok"):
        return {"ok": False, "sent": 0, "status": status,
                "message": "Waiting for your manager to approve you. Nothing has been uploaded yet."}
    return {"ok": True, "sent": len(acts), "status": status, "message": f"Uploaded {len(acts)} activities."}


def preview_data():
    c = info()
    return {"activities": collect(c) if c else []}


# ---------- CLI entry points ----------
def cli_enroll(server, company_id, name="", email="", assume_yes=False):
    if info():
        sys.exit("Already enrolled. Run 'app-usage unenroll' first.")
    try:
        co = lookup(server, company_id)
    except ServerError as e:
        sys.exit(f"Could not look up the company: {e}")
    print(f"Company: {co['name']}\n")
    print(describe(co["policy"]))
    name = name or input("\nYour name: ").strip()
    email = email or ("" if assume_yes else input("Work email (optional): ").strip())
    if not assume_yes and input("\nDo you agree to this and want to enrol this computer? [y/N] ").strip().lower() != "y":
        return print("Not enrolled. Nothing was sent.")
    try:
        c = join(server, company_id, name, email)
    except ServerError as e:
        sys.exit(f"Enrolment failed: {e}")
    if c["status"] == "pending":
        print(f"Registered as {c['employee']}. Waiting for your manager to approve you; nothing is uploaded until then.")
    else:
        print(f"Enrolled as {c['employee']}. Activity from now on will be uploaded every few minutes.")


def cli_sync():
    print(sync(force=True)["message"])


def preview():
    if not info():
        return print("Not enrolled; nothing is sent.")
    print(json.dumps(preview_data(), indent=2))


def status():
    c = refresh()
    if not c:
        return print("Not enrolled. Activity is only stored on this computer.")
    print(f"Company:  {c.get('company_name', '')}\nEnrolled: {c['employee']}\nStatus:   {c.get('status', '?')}\n"
          f"Server:   {c['server']}\nSince:    {c['enrolled_at']}\n")
    print(describe(c["policy"]))


def cli_unenroll():
    if not info():
        return print("Not enrolled.")
    note = unenroll()
    print(note or "Unenrolled. Nothing more will be uploaded.")
