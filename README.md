# ⚡ Antigravity Rewind • Desktop Time Machine & Rollback Engine

[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue.svg)](https://github.com)
[![Architecture](https://img.shields.io/badge/engine-6--Layer%20Atomic%20Rollback-indigo.svg)](https://github.com)
[![Status](https://img.shields.io/badge/status-Production%20Verified%20(100%25)-success.svg)](https://github.com)
[![Zero Install](https://img.shields.io/badge/binary-Zero--Install%20Standalone%20EXE-emerald.svg)](https://github.com)
[![Themes](https://img.shields.io/badge/themes-Dark%20(Antigravity)%20%7C%20Light%20(Paper)-amber.svg)](https://github.com)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A high-performance standalone desktop time machine and trajectory inspector for **Google Antigravity**. Built from first principles to match the authentic Antigravity 2.0 interface, enabling developers to inspect, undo, prune, and roll back any AI session to an exact message, tool, or thinking step with 100% byte-for-byte SQLite and transcript parity.

---

## 🌟 Key Features

### 1. 🎯 Pixel-Perfect Antigravity 2.0 Interface
- **Exact Visual Replica**: Authentic Antigravity workspace layout, monospace typography, warm gold badges, and markdown code cards with one-click copy.
- **Full Thinking Monologue Display**: Spacious, unconstrained thinking blocks styled identically to Google Antigravity (`Thinking for 14s ⌵`), supporting full expansion without cramped 240px clipping.
- **Bottom Prompt Bar & Step Jumper**: Matches the Antigravity prompt bar with model indicator (`+ Gemini 3.8 Flash High ⌃`) and fast step-jumping.

### 2. ⚡ Injected In-Chat Undo Actions
- Injected **Undo** controls appear seamlessly on hover beside every:
  - 💬 **User Request**
  - 🧠 **Thinking Step**
  - 🛠️ **Tool Execution Group** (files explored, searches, commands executed)
  - 📝 **File Edit** (with +lines / -lines diff badges)
  - 🤖 **Assistant Response**
- **Ghost Pruning Diff**: Hovering over any Undo action dims subsequent messages in the chat feed with a crimson dashed indicator so you can see exactly what will be pruned before confirming.
- **Flexible Rollback Modes**: Choose whether to undo the selected item and everything after, or keep the item as the final message.

### 3. 🌓 Dynamic Dark & Light Themes
- **Dark (Antigravity)**: Exact charcoal/obsidian palette with subtle glass borders.
- **Light (Paper)**: High-contrast slate and paper styling for bright daylight environments.
- **Instant Toggle**: Toggle via the sun/moon button in the chat header or the Settings modal; preference persists automatically in local storage.

### 4. 🚀 Blazing Fast & Zero Scroll Lag
- **Tail Deque Stream Loading**: Large conversation trajectories (verified on **18,790+ step** enterprise sessions like FaizVPN) load in **0.18 seconds** using tail stream buffers.
- **Instant Bottom Placement**: When switching conversations, the feed instantly positions at the latest message without slow animated scrolling from step 0. Smooth scrolling is reserved for the floating `↓` button.
- **On-Demand Full History**: Large chats display an "earlier messages" milestone banner allowing 1-click loading of complete history on demand.

### 5. 🛡️ Time Machine Snapshots & Reversible Restores
- **Automatic Backups**: Automatic snapshot created before every rollback.
- **Native Inline Confirmation**: Revert snapshots directly inside the drawer without disruptive browser alert popups.
- **Active Milestone Tag**: Real-time status indicators show which snapshot matches the live conversation.
- **Manual Snapshots**: Save milestone snapshots with custom notes at any point.

### 6. ⚙️ Settings Modal & Quick Utilities
- **Antigravity Data Store Connection**: Displays current brain directory (`.gemini/antigravity`) status with a 1-click button to open the directory directly in Windows Explorer.
- **Safety Defaults**: Toggle automatic backups and SQLite WAL checkpoints/vacuuming.
- **Keyboard Shortcuts Cheat Sheet**:
  - `Ctrl + R`: Refresh conversation data
  - `Ctrl + H`: Toggle Snapshots drawer
  - `Ctrl + ,`: Open Settings & Preferences
  - `Esc`: Close any open modal or drawer

---

## 🏛️ The 6-Layer Atomic Rollback Engine

Antigravity stores conversation state across SQLite databases, chunk caches, and JSONL streams. `Antigravity Rewind` surgically updates all 6 layers simultaneously:

1. **SQLite Database (`conversations/<id>.db`)**:
   - Prunes the `steps` table where `idx > target_step`.
   - Executes `PRAGMA wal_checkpoint(TRUNCATE)` and `VACUUM` to ensure database integrity.
2. **Transcript Stream (`brain/<id>/.system_generated/logs/transcript.jsonl`)**:
   - Truncates compact event log stream at the target step index.
3. **Full Transcript Stream (`brain/<id>/.system_generated/logs/transcript_full.jsonl`)**:
   - Truncates full payload event log stream at the target step index.
4. **Virtual Scroll Chunks (`chunks/transcript/` & `chunks/transcript_full/`)**:
   - Re-slices fixed 100 KB (`102,400 bytes`) chunk files with byte parity to prevent IDE scroll crashes.
5. **Step Execution Artifacts (`steps/<step_idx>/`)**:
   - Cleans up orphaned output folders for post-cut steps.
6. **Task Logs & Cross-Step Messages (`tasks/` & `messages/`)**:
   - Removes post-cut `task-<id>.log` files and updates message queues.

---

## 🚀 How to Run

### Standalone Executable (Zero Installation)
Double-click `AntigravityRewind.exe` in the project directory, or run from shell:
```bash
AntigravityRewind.exe
```
Launches in an ultra-clean borderless desktop window using your installed Chrome or Edge browser engine.

### Running from Source
```bash
# Install dependencies
pip install -r requirements.txt  # Or: pip install playwright

# Launch desktop app
python app.py
```

### Building the Executable
```bash
build_exe.bat
```
Produces a completely self-contained `AntigravityRewind.exe` with application icon, offline tailwind, lucide icons, and marked.js bundled.

---

## 🧪 End-to-End Human Verification Suite

Antigravity Rewind includes a comprehensive Playwright automation suite (`verify_playwright_e2e.py`) that tests real-world interactions without mocking:
```bash
python verify_playwright_e2e.py
```
Verified test suite covers:
1. Application launch & conversation discovery.
2. Sidebar conversation selection & feed rendering.
3. Snapshots drawer opening & metadata validation.
4. Real-world rollback simulation and milestone restoration.
5. In-card native restore confirmation without browser alert leaks.
6. Real-time active state badge updates.
7. Hover-based in-chat undo action and ghost pruning diff.
8. Light / Dark theme toggles with CSS variable verification.
9. Settings modal rendering, Data Store connection, and `Esc` shortcut.
10. Real-time sidebar search filtering.
11. Fast tail-loading (<0.20s on 18,790-step session) & instant bottom placement.
12. Exact Antigravity thinking block and prompt bar rendering.

---

## 📄 License
MIT License. Free to use, modify, and distribute.
