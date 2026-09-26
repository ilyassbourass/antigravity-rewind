# 🚀 Antigravity Rewind — Promotion & Launch Kit

Use this launch kit to share **Antigravity Rewind** across developer communities, Reddit, Hacker News, X (Twitter), and Discord to maximize reach and help other developers solve their Antigravity headaches.

---

## 📌 1. Reddit Post (for r/GoogleGeminiAI, r/LocalLLaMA, r/ChatGPTCoding, r/programming)

**Title:**
> I built Antigravity Rewind: A 1-click surgical undo & conversation time-machine for Google Antigravity (Fix stuck thinking, runaway tool loops, and "I cannot assist with that" filter blocks)

**Body:**
```markdown
Hey everyone!

If you've been using **Google Antigravity** for agentic coding, you've probably encountered these frustrating moments:
1. **The Context-Polluting Refusal**: Gemini outputs *"I cannot assist with that"*, and from that moment on, that refusal turn stays in your context window, causing the model to get stuck refusing subsequent prompts.
2. **Runaway Thinking / Tool Loops**: The agent gets stuck in a 3-minute thinking loop or runs recursive web searches you didn't ask for.
3. **Disappearing Conversation Bug**: You try using the built-in undo/restore in Antigravity, and your thread mysteriously vanishes from the sidebar, or asks to delete files in your workspace!

To solve this once and for all, I built **Antigravity Rewind** — a standalone desktop time machine and conversation manager built specifically for Google Antigravity.

### ✨ What It Does:
- **Injected In-Chat Undo**: Hover over any user message, thinking block, command group, or assistant response to see an instant `Undo from here` button.
- **Ghost Pruning Diff**: Dims future messages in crimson in real-time so you know exactly what turns will be purged before confirming.
- **6-Layer Atomic SQLite Rollback Engine**: Safely synchronizes `.db` steps, `transcript.jsonl`, `transcript_full.jsonl`, virtual 100 KB scroll chunks, and WAL checkpoints with 100% byte parity. Zero risk to your workspace source files.
- **1-Click "Restart Antigravity"**: Safely terminates `Antigravity.exe`, releases database locks, and relaunches it so your rewound session loads immediately in your editor.
- **Time Machine Snapshots**: Reversible snapshots with real timestamps (`YYYY-MM-DD HH:MM:SS`) so you can jump between milestones anytime.
- **Ultra Fast**: Tested on 18,700+ step enterprise sessions — loads in 0.15s with tail-streaming.
- **Zero-Install Binary**: Available as a ready-to-run `.exe` with Dark and Light themes.

GitHub Repo: https://github.com/ilyassbourass/antigravity-rewind  
Releases (Download EXE): https://github.com/ilyassbourass/antigravity-rewind/releases/latest

It's completely free and open-source (MIT License). Let me know what you think or if you have any feature requests!
```

---

## 📌 2. Hacker News (Show HN)

**Title:**
> Show HN: Antigravity Rewind – Surgical undo and time machine for Google Antigravity

**URL:** `https://github.com/ilyassbourass/antigravity-rewind`

**First Comment:**
```markdown
Hi HN!

Google Antigravity is a fantastic agentic coding environment, but managing long conversations has several known edge cases:
- When a safety refusal ("I cannot assist with that") gets appended to SQLite, the context window retains the refusal turn and degrades subsequent outputs.
- Antigravity's native undo can cause sessions to disappear from the UI due to desynchronized JSONL chunk indexes.
- Destructive restores sometimes trigger file deletion prompts.

I built Antigravity Rewind to solve this. It's a lightweight desktop tool that performs an atomic 6-layer rollback:
1. Prunes the SQLite `steps` table and executes `PRAGMA wal_checkpoint(TRUNCATE)`.
2. Truncates both `transcript.jsonl` and `transcript_full.jsonl`.
3. Re-slices 100 KB virtual scroll chunks so the Antigravity frontend never crashes on scroll.
4. Cleans orphaned task logs and step output folders.
5. Offers an automated prompt to restart `Antigravity.exe` so the rollback is immediately visible.

It also features in-chat hover undo, ghost pruning diffs, and reversible milestone snapshots.

Code & pre-built binary: https://github.com/ilyassbourass/antigravity-rewind
Feedback and questions are very welcome!
```

---

## 📌 3. X (Twitter) Thread

**Tweet 1:**
> 🚨 Just open-sourced Antigravity Rewind: A 1-click surgical undo & conversation time-machine for Google Antigravity!
> 
> Ever had Gemini get stuck in a thinking loop or output "I cannot assist with that" and ruin your 500-step conversation? 
> 
> Here's how to fix it in 1 second 👇🧵

**Tweet 2:**
> 1️⃣ Injected In-Chat Undo:
> Hover over any message, tool group, or thinking block and click "Undo from here". Ghost pruning previews what gets cut before you confirm.
> 
> [Attach screenshot: docs/images/e2e_04_undo_modal.png]

**Tweet 3:**
> 2️⃣ 6-Layer Atomic SQLite Rollback:
> Unlike Antigravity's buggy native restore that can hide sessions or prompt file deletions, Rewind maintains 100% byte parity across SQLite, JSONL streams, and 100 KB virtual chunks.

**Tweet 4:**
> 3️⃣ 1-Click Antigravity Restart:
> When you rewind or restore, Rewind automatically terminates Antigravity.exe, clears DB locks, and relaunches the editor with your restored session.

**Tweet 5:**
> Download the pre-built Windows .exe or clone the repo (Free & MIT):
> 🔗 https://github.com/ilyassbourass/antigravity-rewind
> 
> RT & Star ⭐ if you use Google Antigravity!

---

## 📌 4. Discord Message (Gemini & AI Dev Servers)

```markdown
**Antigravity Rewind — Time Machine & Undo Tool for Google Antigravity**

If you're using Google Antigravity and tired of:
- Sessions getting poisoned by "I cannot assist with that" or safety blocks
- Threads disappearing when you click undo
- Runaway thinking or tool loops

Check out **Antigravity Rewind**: https://github.com/ilyassbourass/antigravity-rewind
It provides in-chat hover undo, atomic SQLite rollback, milestone snapshots, and 1-click Antigravity restart. Free, open source, and available as a standalone `.exe`.
```
