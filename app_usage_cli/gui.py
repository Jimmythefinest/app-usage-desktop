"""Desktop window for the company edition: join a company with a company ID, then see status / sync / leave."""
import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from app_usage_cli import company, config, service

REFRESH_MS = 30_000


def tracker_running():
    """True/False on Linux (systemd user service), None where we cannot tell."""
    if sys.platform == "win32":
        return None
    try:
        r = subprocess.run(["systemctl", "--user", "is-active", "app-usage.service"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() == "active"
    except Exception:
        return None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("App Usage")
        self.geometry("520x620")
        self.minsize(460, 560)
        self.q = queue.Queue()
        self.looked_up = False
        self.container = ttk.Frame(self, padding=16)
        self.container.pack(fill="both", expand=True)
        self.after(100, self._drain)
        self.show()

    # ----- background work: results come back on the Tk thread via a queue -----
    def bg(self, fn, done):
        def run():
            try:
                self.q.put((done, fn(), None))
            except Exception as e:  # noqa: BLE001 - surfaced to the user
                self.q.put((done, None, e))
        threading.Thread(target=run, daemon=True).start()

    def _drain(self):
        try:
            while True:
                done, res, err = self.q.get_nowait()
                done(res, err)
        except queue.Empty:
            pass
        self.after(100, self._drain)

    def clear(self):
        for w in self.container.winfo_children():
            w.destroy()

    def show(self):
        self.clear()
        (self.build_status if company.info() else self.build_enrol)()

    # ----- enrol screen -----
    def build_enrol(self):
        f = self.container
        self.looked_up = False
        ttk.Label(f, text="Join your company", font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        ttk.Label(f, text="Enter the company ID and server address your manager gave you.",
                  wraplength=470).pack(anchor="w", pady=(2, 10))
        self.v = {k: tk.StringVar() for k in ("server", "cid", "name", "email")}
        self.v["server"].set(os.environ.get("AU_SERVER", config.load_config().get("last_server", "")))
        for label, key in (("Server address", "server"), ("Company ID", "cid"),
                           ("Your name", "name"), ("Work email (optional)", "email")):
            ttk.Label(f, text=label).pack(anchor="w")
            ttk.Entry(f, textvariable=self.v[key]).pack(fill="x", pady=(0, 8))
        self.lookup_btn = ttk.Button(f, text="Look up company", command=self.do_lookup)
        self.lookup_btn.pack(anchor="w")
        self.policy = scrolledtext.ScrolledText(f, height=10, wrap="word", state="disabled")
        self.policy.pack(fill="both", expand=True, pady=10)
        self.set_text(self.policy, "Look up your company to see exactly what is collected before you agree.")
        self.agree = tk.BooleanVar()
        self.agree_cb = ttk.Checkbutton(f, text="I have read this and agree", variable=self.agree,
                                        command=self.update_join, state="disabled")
        self.agree_cb.pack(anchor="w")
        self.join_btn = ttk.Button(f, text="Join", command=self.do_join, state="disabled")
        self.join_btn.pack(anchor="e", pady=(8, 0))
        self.msg = ttk.Label(f, text="", foreground="#b3261e", wraplength=470)
        self.msg.pack(anchor="w")

    @staticmethod
    def set_text(widget, text):
        widget.config(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.config(state="disabled")

    def update_join(self):
        ok = self.looked_up and self.agree.get()
        self.join_btn.config(state="normal" if ok else "disabled")

    def do_lookup(self):
        self.msg.config(text="")
        self.lookup_btn.config(state="disabled")
        server, cid = self.v["server"].get(), self.v["cid"].get()

        def done(res, err):
            self.lookup_btn.config(state="normal")
            if err:
                self.looked_up = False
                self.agree_cb.config(state="disabled")
                return self.msg.config(text=str(err))
            self.looked_up = True
            self.set_text(self.policy, f"Company: {res['name']}\n\n" + company.describe(res["policy"]))
            self.agree_cb.config(state="normal")
            self.update_join()
        self.bg(lambda: company.lookup(server, cid), done)

    def do_join(self):
        self.join_btn.config(state="disabled")
        server, cid = self.v["server"].get(), self.v["cid"].get()
        name, email = self.v["name"].get(), self.v["email"].get()

        def done(res, err):
            if err:
                self.update_join()
                return self.msg.config(text=str(err))
            cfg = config.load_config()
            cfg["last_server"] = res["server"]
            config.save_config(cfg)
            self.show()
        self.bg(lambda: company.join(server, cid, name, email), done)

    # ----- status screen -----
    def build_status(self):
        f = self.container
        ttk.Label(f, text="App Usage", font=("TkDefaultFont", 16, "bold")).pack(anchor="w")
        self.info = {}
        grid = ttk.Frame(f)
        grid.pack(fill="x", pady=8)
        for i, (key, label) in enumerate((("company", "Company"), ("who", "You"), ("status", "Status"),
                                          ("tracker", "Tracker"), ("last", "Last upload"))):
            ttk.Label(grid, text=label + ":", width=12).grid(row=i, column=0, sticky="w")
            self.info[key] = ttk.Label(grid, text="", wraplength=340, justify="left")
            self.info[key].grid(row=i, column=1, sticky="w")
        self.policy = scrolledtext.ScrolledText(f, height=9, wrap="word", state="disabled")
        self.policy.pack(fill="both", expand=True, pady=8)
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.sync_btn = ttk.Button(row, text="Sync now", command=self.do_sync)
        self.sync_btn.pack(side="left")
        ttk.Button(row, text="Preview data", command=self.do_preview).pack(side="left", padx=6)
        self.login_btn = ttk.Button(row, text="Start at login", command=self.do_login_start)
        self.login_btn.pack(side="left")
        ttk.Button(f, text="Leave company…", command=self.do_unenroll).pack(anchor="e", pady=(10, 0))
        self.msg = ttk.Label(f, text="", wraplength=470)
        self.msg.pack(anchor="w", pady=(6, 0))
        self.render_status(company.info())
        self.refresh_loop()

    def render_status(self, c):
        if not c or not hasattr(self, "info") or not self.info.get("company") or not self.info["company"].winfo_exists():
            return
        st = c.get("status", "?")
        text = {"active": "Active - uploading", "pending": "Waiting for your manager to approve you",
                "revoked": "Removed by the company - nothing is uploaded"}.get(st, st)
        if c.get("reachable") is False:
            text += " (server unreachable)"
        run = tracker_running()
        self.info["company"].config(text=c.get("company_name", ""))
        self.info["who"].config(text=c["employee"] + (f" ({c['email']})" if c.get("email") else ""))
        self.info["status"].config(text=text)
        self.info["tracker"].config(text={True: "Running", False: "Not running - press Start at login",
                                          None: "Unknown"}[run])
        last = c.get("last_sync")
        self.info["last"].config(text=f"{last.replace('T', ' ')} ({c.get('last_sent', 0)} activities)" if last else "Not yet")
        self.set_text(self.policy, company.describe(c["policy"]))

    def refresh_loop(self):
        if not company.info() or not self.info["company"].winfo_exists():
            return
        self.bg(company.refresh, lambda res, err: self.render_status(res))
        self.after(REFRESH_MS, self.refresh_loop)

    def do_sync(self):
        self.sync_btn.config(state="disabled")
        self.msg.config(text="Uploading…", foreground="")

        def done(res, err):
            self.sync_btn.config(state="normal")
            if err:
                return self.msg.config(text=str(err), foreground="#b3261e")
            self.msg.config(text=res["message"], foreground="" if res["ok"] else "#b3261e")
            self.render_status(company.info())
        self.bg(lambda: company.sync(force=True), done)

    def do_preview(self):
        win = tk.Toplevel(self)
        win.title("Exactly what is sent")
        win.geometry("620x480")
        box = scrolledtext.ScrolledText(win, wrap="none")
        box.pack(fill="both", expand=True)
        self.set_text(box, "Loading…")
        self.bg(company.preview_data,
                lambda res, err: self.set_text(box, str(err) if err else json.dumps(res, indent=2)))

    def do_login_start(self):
        def go():
            if sys.platform == "win32":
                service._create_startup_shortcut(sys.executable)
            else:
                service.install_service()
            return tracker_running()
        self.login_btn.config(state="disabled")

        def done(res, err):
            self.login_btn.config(state="normal")
            self.msg.config(text=str(err) if err else "The tracker will now start when you log in.",
                            foreground="#b3261e" if err else "")
            self.render_status(company.info())
        self.bg(go, done)

    def do_unenroll(self):
        if not messagebox.askyesno("Leave company", "Stop uploading and unlink this computer?\n\n"
                                   "Data already sent stays with the company until they delete it."):
            return

        def done(note, err):
            if note or err:
                messagebox.showinfo("Left company", str(err or note))
            self.show()
        self.bg(company.unenroll, done)


def main():
    try:
        app = App()
    except tk.TclError as e:
        sys.exit(f"Cannot open a window here ({e}). Use the command line instead: app-usage --help")
    app.mainloop()


if __name__ == "__main__":
    main()
