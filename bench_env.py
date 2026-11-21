"""Builds a LARGE realistic Antigravity brain for benchmarking (no tiny fixtures)."""
import json
import os
import random
import shutil
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def enc_v(v):
    out = bytearray()
    while v > 0x7F:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v & 0x7F)
    return bytes(out)


def gen_metadata_row(steps):
    body = b"".join(enc_v(s) for s in steps)
    return bytes([0x12, len(body)]) + body


def build(base, n_convs=6, steps_per_conv=1200, seed=7):
    rng = random.Random(seed)
    base = os.path.abspath(base)
    shutil.rmtree(base, ignore_errors=True)
    ant = os.path.join(base, ".gemini", "antigravity")
    conv_dir, brain_dir, annot_dir = (os.path.join(ant, d) for d in ("conversations", "brain", "annotations"))
    for d in (conv_dir, brain_dir, annot_dir):
        os.makedirs(d, exist_ok=True)

    tools = ["read_file", "edit_file", "run_command", "search_code", "write_file"]
    topics = ["auth", "parser", "rollback", "database", "ui", "network"]
    for ci in range(n_convs):
        cid = f"bench_conv_{ci:02d}"
        db = os.path.join(conv_dir, f"{cid}.db")
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY, kind TEXT, created_at TEXT);")
        cur.executemany("INSERT INTO steps (idx, kind, created_at) VALUES (?, ?, ?);",
                        [(i, "step", f"2026-11-1{ci % 10}T10:00:{i % 60:02d}Z") for i in range(steps_per_conv)])
        cur.execute("CREATE TABLE gen_metadata (idx INTEGER PRIMARY KEY, data BLOB);")
        for gi in range(0, steps_per_conv, 50):
            cur.execute("INSERT INTO gen_metadata VALUES (?, ?);",
                        (gi // 50, gen_metadata_row(list(range(gi, min(gi + 50, steps_per_conv))))))
        cur.execute("CREATE TABLE executor_metadata (idx INTEGER PRIMARY KEY, data BLOB);")
        out = b""
        out += enc_v(0x10) + enc_v(3)
        out += enc_v(0x18) + enc_v(steps_per_conv // 50)
        out += enc_v(0x20) + enc_v(steps_per_conv - 1)
        cur.execute("INSERT INTO executor_metadata VALUES (0, ?);", (out + bytes([0x42, 0x05, 0x01]),))
        conn.commit()
        conn.close()

        logs = os.path.join(brain_dir, cid, ".system_generated", "logs")
        os.makedirs(logs, exist_ok=True)
        topic = topics[ci % len(topics)]
        lines = []
        for i in range(steps_per_conv):
            roll = rng.random()
            if roll < 0.12:
                src, typ, content, tools_ = "USER_EXPLICIT", "USER_INPUT", f"<USER_REQUEST>\nNow {topic}: change {rng.randint(1, 999)} lines in the {topic} module and verify\n</USER_REQUEST>", []
            elif roll < 0.55:
                src, typ = "MODEL", "PLANNER_RESPONSE"
                content = f"Working on {topic} step {i}: analyzed the call graph, found {rng.randint(1, 40)} references, planning the edit for module {topic}_{rng.randint(1, 20)}.py"
                t = tools[rng.randrange(len(tools))]
                tools_ = [{"name": t, "args": {"TargetFile": f"src/{topic}_{rng.randint(1,20)}.py",
                                               "CommandLine": f"python -m pytest tests/{topic}_test_{rng.randint(1,9)}.py -x -q",
                                               "toolSummary": f"{t} src/{topic}_{rng.randint(1,20)}.py"}}]
            elif roll < 0.9:
                src, typ, content, tools_ = "GENERIC", "GENERIC", ("output line " + "x" * rng.randint(20, 300) + f" result={rng.random()}") + "\n", []
            else:
                src, typ, content, tools_ = "MODEL", "SYSTEM_MESSAGE", f"System: checkpoint {i} for {topic}", []
            lines.append(json.dumps({
                "step_index": i, "source": src, "type": typ,
                "content": content if src != "MODEL" else f"content={content}",
                "created_at": f"2026-11-1{ci % 10}T10:{i // 60 % 60:02d}:{i % 60:02d}Z",
                "thinking": ("thinking " * rng.randint(10, 120)) if src == "MODEL" else "",
                "tool_calls": tools_,
            }))
        with open(os.path.join(logs, "transcript.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        with open(os.path.join(logs, "transcript_full.jsonl"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    sdb = os.path.join(ant, "conversation_summaries.db")
    conn = sqlite3.connect(sdb)
    cur = conn.cursor()
    cur.execute("CREATE TABLE conversation_summaries (conversation_id TEXT, title TEXT, preview TEXT, agent_name TEXT, parent_conversation_id TEXT);")
    for ci in range(n_convs):
        cid = f"bench_conv_{ci:02d}"
        cur.execute("INSERT INTO conversation_summaries VALUES (?,?,?,?,?);",
                    (cid, "", f"Session {ci}: <b>fix the {topics[ci % len(topics)]} module</b> and validate everything", "", ""))
    conn.commit()
    conn.close()
    return ant


if __name__ == "__main__":
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".bench_env")
    ant = build(base)
    total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(ant) for f in fs)
    print(f"built {n if False else ''}{len(os.listdir(os.path.join(ant, 'conversations')))} conversations under {ant} ({total/1e6:.1f} MB)")
