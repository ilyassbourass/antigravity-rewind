"""Baseline + post-optimization benchmark of the real backend APIs on the big env."""
import json
import os
import statistics
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

ENV = os.path.join(HERE, os.environ.get("BENCH_ENV", ".bench_env"), ".gemini", "antigravity")


def timed(fn, *a, **k):
    t0 = time.perf_counter()
    r = fn(*a, **k)
    return (time.perf_counter() - t0) * 1000.0, r


def median_ms(fn, n=5, *a, **k):
    xs = []
    r = None
    for _ in range(n):
        ms, r = timed(fn, *a, **k)
        xs.append(ms)
    return statistics.median(xs), r


def main():
    global STEPS
    STEPS = 10000
    import backend as _b
    b = _b.RewindBackend(base_path=ENV)
    cid = "bench_conv_00"
    rows = []

    def rec(name, ms, extra=""):
        rows.append((name, ms, extra))
        print(f"{name:34s} {ms:9.1f} ms  {extra}")

    ms, _ = median_ms(b.discover_conversations, 5)
    rec("discover_conversations", ms)
    ms, _ = median_ms(b.get_kpi_stats, 5)
    rec("get_kpi_stats", ms)
    ms, _ = median_ms(b.get_steps, 5, cid)
    rec("get_steps", ms, f"({STEPS} steps)")
    ms, _ = median_ms(b.get_chat_feed, 5, cid, 0)
    rec("get_chat_feed (full)", ms)
    ms, _ = median_ms(b.get_chat_feed, 5, cid, 30)
    rec("get_chat_feed (limit 30)", ms)
    ms, _ = median_ms(b.get_conversation_prompts, 5, cid)
    rec("get_conversation_prompts", ms)
    ms, _ = median_ms(b.get_step_detail, 5, cid, 700)
    rec("get_step_detail", ms)
    ms, _ = median_ms(b.search_session, 3, cid, "rollback")
    rec("search_session", ms)
    ms, _ = median_ms(b.export_conversation_markdown, 3, cid)
    rec("export_conversation_markdown", ms)
    ms, _ = median_ms(b.perform_rollback, 3, cid, STEPS - 1, True)
    rec("perform_rollback(full)", ms)
    # dashboard realistic load: discover + kpi + steps + feed for 3 convs
    def dashboard():
        cs = b.discover_conversations()
        b.get_kpi_stats()
        for c in cs[:3]:
            b.get_steps(c["id"])
            b.get_chat_feed(c["id"], 0)
    ms, _ = median_ms(dashboard, 3)
    rec("dashboard load (3 convs)", ms)
    return rows


if __name__ == "__main__":
    import backend
    print(f"RUST_PORT={backend._RUST_PORT}")
    main()
