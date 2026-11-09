# App Usage - company server (multi-company)

    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    .venv/bin/uvicorn app_usage_server.main:app --host 0.0.0.0 --port 8000

1. Open `/` in a browser and **create an account** (company name, email, password). Each manager account owns one company.
2. The dashboard shows your **company ID**. Give employees that ID plus the server address.
3. Employees open the *App Usage* window, enter server + company ID + their own name/email, read the policy, tick agree, Join.
4. With "require approval" on (default) new employees appear under *Pending approvals* until you approve them.

Storage: one SQLite file, `~/.local/share/app_usage_server/server.db` (override the folder with `AU_DATA_DIR`). Back that folder up.
Set `AU_ALLOW_SIGNUP=0` once your companies exist to stop strangers creating accounts.
Companies are isolated: every manager query is scoped to that manager's company.
Put it behind HTTPS (reverse proxy) before using it beyond a test network.
