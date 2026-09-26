import os
import sys
import json
import threading
import subprocess
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from backend import RewindBackend

backend = RewindBackend()
PORT = 8123
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS

class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_POST(self):
        if self.path.startswith("/api/"):
            method_name = self.path.replace("/api/", "").split("?")[0]
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            data = {}
            if body:
                try:
                    data = json.loads(body)
                except:
                    pass
            args = data.get("args", [])

            res = None
            try:
                if method_name == "get_kpi_stats":
                    res = backend.get_kpi_stats()
                elif method_name == "discover_conversations":
                    res = backend.discover_conversations()
                elif method_name == "get_steps":
                    cid = args[0] if len(args) > 0 else ""
                    res = backend.get_steps(cid)
                elif method_name == "get_chat_feed":
                    cid = args[0] if len(args) > 0 else ""
                    limit = args[1] if len(args) > 1 else 250
                    res = backend.get_chat_feed(cid, limit=limit)
                elif method_name == "get_step_detail":
                    cid = args[0] if len(args) > 0 else ""
                    step = args[1] if len(args) > 1 else 0
                    res = backend.get_step_detail(cid, step)
                elif method_name == "perform_rollback":
                    cid = args[0]
                    step = args[1]
                    bk = args[2] if len(args) > 2 else True
                    res = backend.perform_rollback(cid, step, bk)
                elif method_name == "list_backups":
                    cid = args[0]
                    res = backend.list_backups(cid)
                elif method_name == "create_manual_snapshot":
                    cid = args[0]
                    lbl = args[1] if len(args) > 1 else "snapshot"
                    res = backend.create_manual_snapshot(cid, lbl)
                elif method_name == "delete_backup":
                    cid = args[0]
                    bp = args[1]
                    res = backend.delete_backup(cid, bp)
                elif method_name == "restore_backup":
                    cid = args[0]
                    bp = args[1]
                    res = backend.restore_backup(cid, bp)
                elif method_name == "open_antigravity_folder":
                    res = backend.open_antigravity_folder()
                else:
                    res = {"error": f"Unknown method: {method_name}"}
            except Exception as e:
                res = {"error": str(e)}

            response_bytes = json.dumps(res).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response_bytes)
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress noisy HTTP logs
        pass


def launch_edge_app(port):
    browser_candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    browser_exe = None
    for ep in browser_candidates:
        if os.path.exists(ep):
            browser_exe = ep
            break

    user_data = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "antigravity_rewind_app_data")
    url = f"http://127.0.0.1:{port}/index.html"

    if browser_exe:
        cmd = [
            browser_exe,
            f"--app={url}",
            f"--user-data-dir={user_data}",
            "--window-size=1280,820"
        ]
        subprocess.Popen(cmd)
    else:
        import webbrowser
        webbrowser.open(url)


def main():
    if "--list" in sys.argv:
        convs = backend.discover_conversations()
        print(f"\nFound {len(convs)} conversations:")
        for c in convs:
            print(f"[{c['id']}] {c['title']} ({c['step_count']} steps)")
        return

    # Find free port
    port = PORT
    server = None
    for p in range(PORT, PORT + 20):
        try:
            server = HTTPServer(("127.0.0.1", p), AppHandler)
            port = p
            break
        except:
            continue

    if not server:
        print("[ERROR] Could not bind to any port.")
        return

    print(f"Starting Antigravity Rewind Desktop Server on http://127.0.0.1:{port}...")
    threading.Thread(target=server.serve_forever, daemon=True).start()

    print("Launching Desktop App Window...")
    launch_edge_app(port)

    # Keep main thread alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main()
