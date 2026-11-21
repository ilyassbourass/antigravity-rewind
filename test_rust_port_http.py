"""HTTP-level differential test: drive the real app server (app.py AppHandler) against a
fake Antigravity brain, twice — Rust-wired vs Python-only — and diff every response."""
import importlib
import json
import os
import shutil
import sys
import threading
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import test_rust_port_e2e as t

CIDS = ["conv_alpha", "conv_beta", "conv_gamma"]


def call(port, method, args=None, expect_ok=True):
    body = json.dumps({"args": args or []}).encode()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/{method}", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return f"{r.status}:{r.read().decode('utf-8', 'replace')}"
    except urllib.error.HTTPError as e:
        return f"{e.code}:{e.read().decode('utf-8', 'replace')}"


def get_export(port, cid):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/export/{cid}", timeout=15) as r:
            return f"{r.status}:{r.read().decode('utf-8', 'replace')}"
    except Exception as e:
        return f"ERR:{type(e).__name__}"


def battery(port, work_home):
    out = {}
    out["kpi"] = call(port, "get_kpi_stats")
    out["discover"] = call(port, "discover_conversations")
    for cid in CIDS:
        out[f"steps:{cid}"] = call(port, "get_steps", [cid])
        out[f"feed:{cid}"] = call(port, "get_chat_feed", [cid, 0])
        out[f"prompts:{cid}"] = call(port, "get_conversation_prompts", [cid])
        out[f"detail:{cid}"] = call(port, "get_step_detail", [cid, 2])
        out[f"search:{cid}"] = call(port, "search_session", [cid, "rollback", False])
        out[f"backups:{cid}"] = call(port, "list_backups", [cid])
        out[f"export:{cid}"] = get_export(port, cid)
    # mutations on conv_alpha through the real HTTP API
    out["snapshot"] = call(port, "create_manual_snapshot", ["conv_alpha", "http-smoke"])
    out["rollback"] = call(port, "perform_rollback", ["conv_alpha", 3, True])
    out["backups_after"] = call(port, "list_backups", ["conv_alpha"])
    snaps = json.loads(out["backups_after"].split(":", 1)[1])
    ident = None
    if snaps:
        ident = snaps[0].get("identifier") or snaps[0].get("name")
    out["restore"] = call(port, "restore_backup", ["conv_alpha", ident]) if ident else "none"
    out["steps_after"] = call(port, "get_steps", ["conv_alpha"])
    out["feed_after"] = call(port, "get_chat_feed", ["conv_alpha", 0])
    return {k: t.normalize(v, str(work_home)) if isinstance(v, str) else v for k, v in out.items()}


def run_mode(rust):
    work = os.path.join(HERE, ".http_run")
    work_home = work
    home = os.path.join(work, "home")
    t.build_env(home)
    shutil.rmtree(work, ignore_errors=True)
    t.build_env(home)

    os.environ["USERPROFILE"] = home  # app.py's RewindBackend() reads this
    import app, backend
    importlib.reload(backend)
    backend._RUST_PORT = rust
    app.backend = backend.RewindBackend()  # app.py's global `backend` is an instance, not the module

    server = __import__("http.server", fromlist=["ThreadingHTTPServer"]).ThreadingHTTPServer(
        ("127.0.0.1", 0), app.AppHandler)
    port = server.server_address[1]
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()

    assert backend._RUST_PORT == rust, "Rust flag did not stick"
    assert backend.RewindBackend().base_path == os.path.join(home, ".gemini", "antigravity")
    res = battery(port, work_home)
    server.shutdown()
    shutil.rmtree(work, ignore_errors=True)
    return json.dumps(res, sort_keys=True)


def main():
    t.build_env(t.ENV)
    py = run_mode(False)
    rs = run_mode(True)
    a, b = json.loads(py), json.loads(rs)
    ok = True
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            ok = False
            print(f"MISMATCH {k}:")
            print("  py  :", str(a.get(k))[:220])
            print("  rust:", str(b.get(k))[:220])
    if ok:
        n = len(a)
        print(f"HTTP DIFFERENTIAL: PASS — all {n} endpoint responses identical (Rust-wired vs Python-only)")
        print("  covered: kpi, discover, steps, chat feed, prompts, step detail, search, backups,")
        print("  markdown export over HTTP, create snapshot, perform_rollback, restore_backup")
    t.ENV and shutil.rmtree(t.ENV, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
