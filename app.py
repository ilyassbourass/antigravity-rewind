import os
import sys
import json
import threading
import subprocess
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from backend import RewindBackend

backend = RewindBackend()
PORT = 8123

# Build list of candidate directories for static assets (supporting PyInstaller onefile, onedir, or plain Python)
CANDIDATE_DIRS = []
if getattr(sys, 'frozen', False):
    if hasattr(sys, '_MEIPASS'):
        CANDIDATE_DIRS.append(sys._MEIPASS)
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if exe_dir not in CANDIDATE_DIRS:
        CANDIDATE_DIRS.append(exe_dir)
    internal_dir = os.path.join(exe_dir, "_internal")
    if os.path.isdir(internal_dir) and internal_dir not in CANDIDATE_DIRS:
        CANDIDATE_DIRS.append(internal_dir)

src_dir = os.path.dirname(os.path.abspath(__file__))
if src_dir not in CANDIDATE_DIRS:
    CANDIDATE_DIRS.append(src_dir)

BASE_DIR = CANDIDATE_DIRS[0] if CANDIDATE_DIRS else os.path.dirname(os.path.abspath(__file__))

class AppHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def translate_path(self, path):
        # Clean path
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path.lstrip('/')
        if not clean_path:
            clean_path = 'index.html'

        for base in CANDIDATE_DIRS:
            candidate = os.path.normpath(os.path.join(base, clean_path))
            if os.path.isfile(candidate):
                return candidate

        return super().translate_path(path)

    def do_GET(self):
        if self.path.startswith("/api/export/"):
            parsed = urllib.parse.urlparse(self.path)
            cid = parsed.path.replace("/api/export/", "").split("/")[0]
            params = urllib.parse.parse_qs(parsed.query)
            include_thinking = params.get("thinking", ["1"])[0].lower() in ["1", "true", "yes"]
            include_tools = params.get("tools", ["1"])[0].lower() in ["1", "true", "yes"]
            res = backend.export_conversation_markdown(cid, include_thinking, include_tools)
            if res.get("success"):
                md_bytes = res["markdown"].encode("utf-8")
                fn = res.get("filename", "session.md")
                self.send_response(200)
                self.send_header("Content-Type", "text/markdown; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{fn}"')
                self.send_header("Content-Length", str(len(md_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(md_bytes)
                return
            else:
                err_bytes = json.dumps(res).encode("utf-8")
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(err_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(err_bytes)
                return
        super().do_GET()

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
                    limit = args[1] if len(args) > 1 else 0
                    res = backend.get_chat_feed(cid, limit=limit)
                elif method_name == "get_conversation_prompts":
                    cid = args[0] if len(args) > 0 else ""
                    res = backend.get_conversation_prompts(cid)
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
                elif method_name == "restart_antigravity":
                    res = backend.restart_antigravity()
                elif method_name == "export_conversation_markdown":
                    cid = args[0] if len(args) > 0 else ""
                    include_thinking = args[1] if len(args) > 1 else True
                    include_tools = args[2] if len(args) > 2 else True
                    res = backend.export_conversation_markdown(cid, include_thinking, include_tools)
                elif method_name == "search_session":
                    cid = args[0] if len(args) > 0 else ""
                    query = args[1] if len(args) > 1 else ""
                    case_sensitive = args[2] if len(args) > 2 else False
                    res = backend.search_session(cid, query, case_sensitive=case_sensitive)
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
            try:
                self.wfile.write(response_bytes)
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
                pass
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
    url = f"http://127.0.0.1:{port}/index.html"
    import time
    browser_candidates = [
        # 1. Brave Browser (User's primary browser on this system - verified working without lock errors)
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
        # 2. Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        # 3. Native Edge
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]

    for browser in browser_candidates:
        if os.path.isfile(browser):
            try:
                cmd = [browser, f"--app={url}", "--window-size=1280,820"]
                proc = subprocess.Popen(cmd)
                time.sleep(0.4)
                # If still running or exited with 0 (handed off to running browser instance), we succeeded!
                if proc.poll() is None or proc.returncode == 0:
                    return
            except Exception:
                continue

    # 4. Reliable OS fallback: Native Windows ShellExecute / default browser
    try:
        os.startfile(url)
    except Exception:
        import webbrowser
        webbrowser.open(url)


def is_server_alive(port):
    try:
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/index.html", timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def main():
    if "--list" in sys.argv:
        convs = backend.discover_conversations()
        print(f"\nFound {len(convs)} conversations:")
        for c in convs:
            print(f"[{c['id']}] {c['title']} ({c['step_count']} steps)")
        return

    # 1. Single-Instance Check: If Antigravity Rewind is already running, activate window and exit
    for p in range(PORT, PORT + 20):
        if is_server_alive(p):
            print(f"Antigravity Rewind is already running on http://127.0.0.1:{p}. Activating window...")
            launch_edge_app(p)
            return

    # 2. Find free port to bind server
    port = PORT
    server = None
    for p in range(PORT, PORT + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), AppHandler)
            port = p
            break
        except Exception:
            continue

    if not server:
        print("[ERROR] Could not bind to any port.")
        return

    print(f"Starting Antigravity Rewind Desktop Server on http://127.0.0.1:{port}...")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    import time
    time.sleep(0.25)

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
