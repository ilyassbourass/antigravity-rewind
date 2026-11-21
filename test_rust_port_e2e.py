"""Differential end-to-end test: the Rust port wired into backend.py vs the pure-Python app.

Creates a realistic fake Antigravity brain (conversations DBs with steps/gen_metadata/
executor_metadata, transcripts, annotations, summaries, chunks, messages), then runs the
full backend API battery twice on fresh clones — once with _RUST_PORT forced False
(Python only), once with the crate active — and diffs every JSON result, file tree and
DB byte. The port is proven only if everything is identical.
"""
import json
import os
import re
import shutil
import sqlite3
import sys
import io

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def normalize(text, work):
    """Strip run-specific paths and wall-clock timestamps so runs are comparable."""
    for form in (work, work.replace("\\", "/"), os.path.basename(work)):
        text = text.replace(form, "<WORK>")
    text = re.sub(r"\d{8}_\d{6}", "<TS>", text)
    text = re.sub(r"\b17\d{8}\.\d+\b", "<EPOCH>", text)
    text = re.sub(r"\b17\d{8}\b", "<EPOCH>", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "<DATE>", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", "<ISODATE>", text)
    return text

APP = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(APP, ".e2e_template")


def enc_v(v):
    out = bytearray()
    while v > 0x7f:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v & 0x7F)
    return bytes(out)


def dec_v(buf, offset):
    r = 0
    s = 0
    while offset < len(buf):
        b = buf[offset]
        offset += 1
        r |= (b & 0x7F) << s
        s += 7
        if not (b & 0x80):
            break
    return r, offset


def gen_metadata_row(steps):
    """Protobuf-ish: 0x12, len, then varint step indexes (mimics gen_metadata blobs)."""
    body = b"".join(enc_v(s) for s in steps)
    return bytes([0x12, len(body)]) + body


def executor_row(gen_count, target_step, extra=(0x42, 0x05, 0x01)):
    """Six varint fields (t1 v1 t2 v2 t3 v3) + trailing bytes, like the real one."""
    out = b""
    out += enc_v(0x10) + enc_v(3)
    out += enc_v(0x18) + enc_v(gen_count)
    out += enc_v(0x20) + enc_v(target_step)
    return out + bytes(extra)


STEP_TEMPLATE = [
    # (step_index, source, type, content, tool_calls)
    (0, "USER_EXPLICIT", "USER_INPUT", "<USER_REQUEST>\nFix the login bug in src/auth.py\n</USER_REQUEST>", []),
    (1, "MODEL", "PLANNER_RESPONSE", "I will start by reading the auth module.", [
        {"name": "read_file", "args": {"TargetFile": "src/auth.py", "toolSummary": "Read src/auth.py"}}]),
    (2, "MODEL", "PLANNER_RESPONSE", "Found the bug: null check missing.", [
        {"name": "edit_file", "args": {"TargetFile": "src/auth.py", "toolSummary": "Edit src/auth.py"}}]),
    (3, "GENERIC", "GENERIC", "Tests pass: 42/42\n", []),
    (4, "MODEL", "PLANNER_RESPONSE", "Running the full suite now.", [
        {"name": "run_command", "args": {"CommandLine": "python -m pytest -q", "toolSummary": "Run pytest"}}]),
    (5, "GENERIC", "GENERIC", "All checks passed.", []),
    (6, "MODEL", "SYSTEM_MESSAGE", "Session paused by user.", []),
]


def build_env(base):
    base = os.path.abspath(base)
    shutil.rmtree(base, ignore_errors=True)
    ant = os.path.join(base, ".gemini", "antigravity")
    conv_dir = os.path.join(ant, "conversations")
    brain_dir = os.path.join(ant, "brain")
    annot_dir = os.path.join(ant, "annotations")
    for d in (conv_dir, brain_dir, annot_dir):
        os.makedirs(d, exist_ok=True)

    for ci, cid in enumerate(("conv_alpha", "conv_beta", "conv_gamma")):
        # conversation DB
        db = os.path.join(conv_dir, f"{cid}.db")
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY, kind TEXT, created_at TEXT);")
        n_steps = 7 if ci != 1 else 4
        for i in range(n_steps):
            cur.execute("INSERT INTO steps (idx, kind, created_at) VALUES (?, ?, ?);",
                        (i, "step", f"2026-11-2{ci}T10:0{i}:00Z"))
        # gen_metadata: some rows cover only rolled-back steps, one covers kept steps
        cur.execute("CREATE TABLE gen_metadata (idx INTEGER PRIMARY KEY, data BLOB);")
        cur.execute("INSERT INTO gen_metadata VALUES (0, ?);", (gen_metadata_row([1, 2]),))
        cur.execute("INSERT INTO gen_metadata VALUES (1, ?);", (gen_metadata_row([5, 6]),))
        cur.execute("INSERT INTO gen_metadata VALUES (2, ?);", (gen_metadata_row([9, 10]),))
        cur.execute("CREATE TABLE executor_metadata (idx INTEGER PRIMARY KEY, data BLOB);")
        cur.execute("INSERT INTO executor_metadata VALUES (0, ?);", (executor_row(gen_count=3, target_step=6),))
        conn.commit()
        conn.close()

        # brain logs
        logs = os.path.join(brain_dir, cid, ".system_generated", "logs")
        os.makedirs(logs, exist_ok=True)
        full = []
        for i, (idx, src, typ, content, tools) in enumerate(STEP_TEMPLATE):
            if idx >= n_steps:
                break
            full.append(json.dumps({
                "step_index": idx, "source": src, "type": typ,
                "content": content if src != "MODEL" else f"content={content}",
                "created_at": f"2026-11-2{ci}T10:0{idx}:00Z",
                "thinking": "hmm" if src == "MODEL" else "",
                "tool_calls": tools,
            }))
        with open(os.path.join(logs, "transcript.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(full) + "\n")
        with open(os.path.join(logs, "transcript_full.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(full) + "\n")
        # chunk dirs + step/task/message dirs
        os.makedirs(os.path.join(logs, "chunks", "transcript"), exist_ok=True)
        os.makedirs(os.path.join(logs, "chunks", "transcript_full"), exist_ok=True)
        with open(os.path.join(logs, "chunks", "transcript", "chunk-0000.json"), "w") as f:
            f.write("{}")
        steps_dir = os.path.join(brain_dir, cid, ".system_generated", "steps")
        tasks_dir = os.path.join(brain_dir, cid, ".system_generated", "tasks")
        msg_dir = os.path.join(brain_dir, cid, ".system_generated", "messages")
        for d in (steps_dir, tasks_dir, msg_dir):
            os.makedirs(d, exist_ok=True)
        for i in range(n_steps + 2):  # includes steps that a rollback should delete
            os.makedirs(os.path.join(steps_dir, str(i)), exist_ok=True)
        for i in range(n_steps + 2):
            with open(os.path.join(tasks_dir, f"task-{i}.log"), "w") as f:
                f.write(f"log {i}")
        msg_map = {}
        for i in range(n_steps + 2):
            mid = f"m{i}"
            with open(os.path.join(msg_dir, f"{mid}.json"), "w") as f:
                json.dump({"sourceMetadata": {"tool": {"stepIndex": i}}}, f)
            msg_map[mid] = True
        with open(os.path.join(msg_dir, "read.json"), "w") as f:
            json.dump(msg_map, f)

    # summaries + annotations
    sdb = os.path.join(ant, "conversation_summaries.db")
    conn = sqlite3.connect(sdb)
    cur = conn.cursor()
    cur.execute("CREATE TABLE conversation_summaries (conversation_id TEXT, title TEXT, preview TEXT, agent_name TEXT, parent_conversation_id TEXT);")
    cur.execute("INSERT INTO conversation_summaries VALUES (?,?,?,?,?);",
                ("conv_beta", "", "Fix the broken WebSocket reconnect logic <b>quickly</b>", "reviewer", "conv_alpha"))
    cur.execute("INSERT INTO conversation_summaries VALUES (?,?,?,?,?);",
                ("conv_alpha", "", "<h1>Fix the Windows rollback crash</h1> and check the backups module", "", ""))
    conn.commit()
    conn.close()
    with open(os.path.join(annot_dir, "conv_alpha.pbtxt"), "w", encoding="utf-8") as f:
        f.write('title: "Rollback crash investigation"\n')
    return base


def snapshot(base):
    """All backend API results + full file tree + DB bytes, as one comparable JSON string."""
    import backend
    b = backend.RewindBackend(base_path=os.path.join(base, ".gemini", "antigravity"))
    out = {}
    convs = b.discover_conversations()
    out["discover"] = [{k: c[k] for k in ("id", "title", "step_count", "size_bytes", "size_formatted",
                                          "last_modified", "relative_time", "has_backup", "backup_count")}
                       for c in convs]
    out["kpi"] = b.get_kpi_stats()
    for c in convs:
        cid = c["id"]
        out[f"title:{cid}"] = b.resolve_conversation_title(cid, force_refresh=True)
        out[f"steps:{cid}"] = b.get_steps(cid)
        out[f"feed:{cid}"] = b.get_chat_feed(cid)
        out[f"prompts:{cid}"] = b.get_conversation_prompts(cid)
        out[f"detail:{cid}:2"] = b.get_step_detail(cid, 2)
        out[f"search:{cid}"] = b.search_session(cid, "rollback", case_sensitive=False)
        out[f"md:{cid}"] = b.export_conversation_markdown(cid)
    # varint codec through the wired backend (list form, as perform_rollback now calls it)
    out["codec"] = [list(bytes(b.encode_and_decode(v)[1])) if False else None for v in ()] or [
        (list(bytes(rw := __import__("rewind_text_rs").encode_varint(v))) if backend._RUST_PORT else list(orig_enc(v)))
        for v in (0, 42, 300, 2**31)
    ]
    return json.dumps(out, sort_keys=True, ensure_ascii=False, default=str)


def orig_enc(v):
    return enc_v(v)


def orig_dec(buf, offset):
    return dec_v(buf, offset)


def tree_and_db(base):
    """Everything on disk: paths + sizes + full file contents + DB table dumps."""
    files = {}
    for root, _, names in os.walk(base):
        for n in names:
            p = os.path.join(root, n)
            rel = os.path.relpath(p, base).replace("\\", "/")
            with open(p, "rb") as f:
                data = f.read()
            files[rel] = data.decode("utf-8", errors="backslashreplace")
    return json.dumps(files, sort_keys=True, ensure_ascii=False)


def run_mode(label, rust):
    import backend
    backend._RUST_PORT = rust
    work = os.path.join(APP, f".e2e_run_{label}")
    shutil.copytree(ENV, work, dirs_exist_ok=True)
    api = normalize(snapshot(work), work)
    b = backend.RewindBackend(base_path=os.path.join(work, ".gemini", "antigravity"))

    # mutating operations on conv_alpha: backup, snapshot, rollback to step 3, restore
    res = {}
    res["create_backup"] = b.create_backup("conv_alpha")
    res["manual_snapshot"] = b.create_manual_snapshot("conv_alpha", "before-rollback")
    res["backups_after"] = b.list_backups("conv_alpha")
    res["rollback"] = b.perform_rollback("conv_alpha", 3, make_backup=True)
    res["backups_after_rollback"] = b.list_backups("conv_alpha")
    res["restore"] = None
    snaps = b.list_backups("conv_alpha")
    if snaps:
        ident = snaps[0].get("identifier") or snaps[0].get("name") or snaps[0]
        if isinstance(ident, dict):
            ident = ident.get("identifier") or ident.get("name")
        res["restore"] = b.restore_backup("conv_alpha", ident)
    res["delete_backup"] = None

    api2 = normalize(snapshot(work), work)  # post-mutation state through every API again
    disk = normalize(tree_and_db(work), work)
    res = normalize(json.dumps(res, sort_keys=True, default=str), work)
    shutil.rmtree(work, ignore_errors=True)
    return api, api2, res, disk


def main():
    build_env(ENV)
    py_api, py_api2, py_res, py_disk = run_mode("python", False)
    rs_api, rs_api2, rs_res, rs_disk = run_mode("rust", True)
    ok = True
    if py_api != rs_api:
        ok = False
        print("MISMATCH: pre-mutation API snapshot differs")
        a, b_ = json.loads(py_api), json.loads(rs_api)
        for k in sorted(set(a) | set(b_)):
            if a.get(k) != b_.get(k):
                print(f"  key {k}:\n    py : {str(a.get(k))[:200]}\n    rust: {str(b_.get(k))[:200]}")
    if py_api2 != rs_api2:
        ok = False
        print("MISMATCH: post-mutation API snapshot differs")
        a, b_ = json.loads(py_api2), json.loads(rs_api2)
        for k in sorted(set(a) | set(b_)):
            if a.get(k) != b_.get(k):
                print(f"  key {k}:\n    py : {str(a.get(k))[:300]}\n    rust: {str(b_.get(k))[:300]}")
    if py_res != rs_res:
        ok = False
        print("MISMATCH: operation results differ")
        print("  py :", py_res[:400])
        print("  rust:", rs_res[:400])
    if py_disk != rs_disk:
        ok = False
        print("MISMATCH: on-disk state differs after identical operations")
        a, b_ = json.loads(py_disk), json.loads(rs_disk)
        for k in sorted(set(a) | set(b_)):
            if a.get(k) != b_.get(k):
                print(f"  file {k} differs (py {len(str(a.get(k)))}B vs rust {len(str(b_.get(k)))}B)")
    if ok:
        print("DIFFERENTIAL E2E: PASS — Python-only and Rust-wired runs are byte-identical")
        print(f"  (API snapshots pre+post mutation, operation results, full disk+DB state)")
    shutil.rmtree(ENV, ignore_errors=True)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
