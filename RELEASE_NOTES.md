# 🚀 Antigravity Rewind v1.0.0 — Initial Release

### ⏪ The Surgical Time Machine & Conversation Manager for Google Antigravity

**Antigravity Rewind** is an open-source standalone desktop application designed specifically for **Google Antigravity**. It solves the critical workflow frustrations developers face in long agentic coding sessions: runaway thinking loops, unprompted tool sequences, context-polluting refusal blocks (*"I cannot assist with that"*), and Antigravity's known native undo disappearing session bugs.

---

### 🌟 Release Highlights & What's New in v1.0.0

- **⚡ Injected In-Chat Undo Actions**:
  - Hover over any user message, thinking block, command execution group, or assistant turn to reveal a surgical `Undo from here` button.
  - Choose between *Undo this item & everything after* or *Keep this item as the last message*.
- **👻 Real-Time Ghost Pruning Diff**:
  - Hovering over an undo button dynamically dims all future turns in crimson, previewing exact rollback impact before confirming.
- **🔄 1-Click "Restart Antigravity" Integration**:
  - Automated modal prompt (`Yes, Restart` / `No, Later`) after performing any undo or restore.
  - Safely closes `Antigravity.exe`, releases SQLite database locks, and relaunches the editor with your restored session.
- **🛡️ 6-Layer Atomic SQLite Rollback Engine**:
  - Maintains 100% byte parity across SQLite `steps` table, `transcript.jsonl`, `transcript_full.jsonl`, 100 KB virtual scroll chunks, and WAL checkpoints.
  - Zero risk to project source files.
- **📸 Time Machine Snapshots with Exact Timestamps**:
  - Automatic snapshots before every rollback, plus manual snapshot notes.
  - View real timestamps (`YYYY-MM-DD HH:MM:SS`), milestone step tags, thread titles, and active state indicators.
- **🚀 Ultra-Fast Tail Deque Streaming**:
  - Benchmarked on 18,790+ step enterprise sessions — loads in 0.15 seconds with zero UI freeze.
  - Instant bottom placement on conversation switch (no slow animated scrolling from turn 0).
- **🌓 Authentic Antigravity Design**:
  - Charcoal/Obsidian Dark Theme and Paper Light Theme.
  - Monospace typography, warm gold badges, code cards with 1-click copy.
- **📦 Zero-Install Windows Executable**:
  - Download `AntigravityRewind.exe` below, double-click, and run immediately. No Python or Node.js required!

---

### 📦 Download & Verification

| Asset | Platform | Description |
| :--- | :--- | :--- |
| **`AntigravityRewind.exe`** | Windows 10 / 11 (x64) | Standalone single-file desktop executable (14.1 MB) |

---

### 🧪 Quality & Test Verification
- Tested with Playwright end-to-end automation suite (`verify_playwright_e2e.py`) on live Antigravity workspaces.
- 100% test pass rate with 0 leaked browser alerts.

---

### 🤝 Feedback & Community
Encountered an issue or have a feature idea? File an issue on [GitHub Issues](https://github.com/ilyassbourass/antigravity-rewind/issues).  
If you find Antigravity Rewind helpful, please leave a **Star ⭐** on the repository!
