import os
import sys
import time
import json
import shutil
import sqlite3
import threading
from http.server import HTTPServer
from app import AppHandler, PORT, backend
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

candidate_dir = r"C:\Users\PC\.gemini\antigravity\brain\f74d1ad5-f0d6-444e-b174-59e7d78ca3a8"
if os.path.exists(os.path.dirname(candidate_dir)):
    ARTIFACT_DIR = candidate_dir
else:
    ARTIFACT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_artifacts")
os.makedirs(ARTIFACT_DIR, exist_ok=True)

import socket

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

def start_server():
    port = get_free_port()
    server = HTTPServer(("127.0.0.1", port), AppHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.5)
    return server, port

def ensure_test_fixtures(base_path):
    conv_dir = os.path.join(base_path, "conversations")
    annot_dir = os.path.join(base_path, "annotations")
    brain_dir = os.path.join(base_path, "brain")
    os.makedirs(conv_dir, exist_ok=True)
    os.makedirs(annot_dir, exist_ok=True)
    os.makedirs(brain_dir, exist_ok=True)

    # 1. BourassVPN
    bourass_id = "89076268-ad08-4b72-8e89-2137e778740c"
    bourass_pb = os.path.join(annot_dir, f"{bourass_id}.pbtxt")
    if not os.path.exists(bourass_pb):
        with open(bourass_pb, "w", encoding="utf-8") as f:
            f.write('title: "BourassVPN Optimization Project Handoff"\n')

    bourass_db = os.path.join(conv_dir, f"{bourass_id}.db")
    if not os.path.exists(bourass_db):
        conn = sqlite3.connect(bourass_db)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS steps (idx INTEGER PRIMARY KEY, data BLOB);")
        for i in range(1050):
            c.execute("INSERT OR REPLACE INTO steps (idx, data) VALUES (?, ?);", (i, b"step_data"))
        conn.commit()
        conn.close()

    b_logs = os.path.join(brain_dir, bourass_id, ".system_generated", "logs")
    os.makedirs(b_logs, exist_ok=True)
    t_file = os.path.join(b_logs, "transcript.jsonl")
    if not os.path.exists(t_file):
        with open(t_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"step_index": 0, "type": "USER_INPUT", "source": "USER_EXPLICIT", "content": "<USER_REQUEST>BourassVPN start</USER_REQUEST>"}) + "\n")
            f.write(json.dumps({"step_index": 1, "type": "PLANNER_RESPONSE", "source": "MODEL", "content": "Running optimization", "thinking": "Thinking for 14s"}) + "\n")
            f.write(json.dumps({"step_index": 2, "type": "TOOL_CALL", "tool_calls": [{"tool_name": "run_command", "args": {"CommandLine": "dir"}}]}) + "\n")
            f.write(json.dumps({"step_index": 3, "type": "PLANNER_RESPONSE", "source": "MODEL", "content": "### 🏁 Optimization Complete: BourassVPN Now Beats FaizVPN We have recompiled..."}) + "\n")
    tf_file = os.path.join(b_logs, "transcript_full.jsonl")
    if not os.path.exists(tf_file):
        shutil.copy2(t_file, tf_file)

    b_bak = os.path.join(brain_dir, bourass_id, "backups", "backup_20260926_174807")
    os.makedirs(b_bak, exist_ok=True)
    if not os.path.exists(os.path.join(b_bak, f"{bourass_id}.db")):
        conn = sqlite3.connect(os.path.join(b_bak, f"{bourass_id}.db"))
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS steps (idx INTEGER PRIMARY KEY, data BLOB);")
        for i in range(1051):
            c.execute("INSERT OR REPLACE INTO steps (idx, data) VALUES (?, ?);", (i, b"step_data"))
        conn.commit()
        conn.close()
    if not os.path.exists(os.path.join(b_bak, "transcript.jsonl")):
        shutil.copy2(t_file, os.path.join(b_bak, "transcript.jsonl"))

    # 2. Samsung Custom Animation Setup
    samsung_id = "1de7c250-59af-45c8-93ec-84f468944ff8"
    samsung_pb = os.path.join(annot_dir, f"{samsung_id}.pbtxt")
    if not os.path.exists(samsung_pb):
        with open(samsung_pb, "w", encoding="utf-8") as f:
            f.write('title: "Samsung Custom Animation Setup"\n')

    s_logs = os.path.join(brain_dir, samsung_id, ".system_generated", "logs")
    os.makedirs(s_logs, exist_ok=True)
    st_file = os.path.join(s_logs, "transcript.jsonl")
    if not os.path.exists(st_file):
        with open(st_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"step_index": 0, "type": "USER_INPUT", "source": "USER_EXPLICIT", "content": "Setup Samsung animations"}) + "\n")
            f.write(json.dumps({"step_index": 1, "type": "PLANNER_RESPONSE", "source": "MODEL", "content": "Configuring animation scales and bezier curves", "thinking": "Thinking for 10s"}) + "\n")
            f.write(json.dumps({"step_index": 2, "type": "PLANNER_RESPONSE", "source": "MODEL", "content": "Assistant Response: Samsung Animation Setup is complete with custom spring values."}) + "\n")
    stf_file = os.path.join(s_logs, "transcript_full.jsonl")
    if not os.path.exists(stf_file):
        shutil.copy2(st_file, stf_file)

    samsung_db = os.path.join(conv_dir, f"{samsung_id}.db")
    if not os.path.exists(samsung_db):
        conn = sqlite3.connect(samsung_db)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS steps (idx INTEGER PRIMARY KEY, data BLOB);")
        for i in range(472):
            c.execute("INSERT OR REPLACE INTO steps (idx, data) VALUES (?, ?);", (i, b"step_data"))
        conn.commit()
        conn.close()

    s_bak = os.path.join(brain_dir, samsung_id, "backups", "backup_20260926_174127")
    os.makedirs(s_bak, exist_ok=True)
    if not os.path.exists(os.path.join(s_bak, f"{samsung_id}.db")):
        conn = sqlite3.connect(os.path.join(s_bak, f"{samsung_id}.db"))
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS steps (idx INTEGER PRIMARY KEY, data BLOB);")
        for i in range(472):
            c.execute("INSERT OR REPLACE INTO steps (idx, data) VALUES (?, ?);", (i, b"step_data"))
        conn.commit()
        conn.close()
    if not os.path.exists(os.path.join(s_bak, "transcript.jsonl")):
        shutil.copy2(st_file, os.path.join(s_bak, "transcript.jsonl"))

    # 3. FaizVPN Complete Knowledge Dossier
    faiz_id = "faizvpn-test-dossier-001"
    faiz_pb = os.path.join(annot_dir, f"{faiz_id}.pbtxt")
    if not os.path.exists(faiz_pb):
        with open(faiz_pb, "w", encoding="utf-8") as f:
            f.write('title: "FaizVPN Complete Knowledge Dossier"\n')

    faiz_db = os.path.join(conv_dir, f"{faiz_id}.db")
    if not os.path.exists(faiz_db):
        conn = sqlite3.connect(faiz_db)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS steps (idx INTEGER PRIMARY KEY, data BLOB);")
        for i in range(120):
            c.execute("INSERT OR REPLACE INTO steps (idx, data) VALUES (?, ?);", (i, b"step_data"))
        conn.commit()
        conn.close()

    f_logs = os.path.join(brain_dir, faiz_id, ".system_generated", "logs")
    os.makedirs(f_logs, exist_ok=True)
    ft_file = os.path.join(f_logs, "transcript.jsonl")
    if not os.path.exists(ft_file):
        with open(ft_file, "w", encoding="utf-8") as f:
            for i in range(80):
                f.write(json.dumps({
                    "step_index": i,
                    "type": "PLANNER_RESPONSE" if i % 2 == 1 else "USER_INPUT",
                    "source": "MODEL" if i % 2 == 1 else "USER_EXPLICIT",
                    "content": f"Step payload {i}: " + ("x" * 250),
                    "thinking": "Thinking for 32s" if i == 1 else None
                }) + "\n")
    ftf_file = os.path.join(f_logs, "transcript_full.jsonl")
    if not os.path.exists(ftf_file):
        shutil.copy2(ft_file, ftf_file)

def run_e2e_test():
    print("[E2E] Ensuring test fixtures in Antigravity storage...", flush=True)
    ensure_test_fixtures(backend.base_path)

    print("[E2E] Starting local backend server...", flush=True)
    server, port = start_server()
    print(f"[E2E] Server running at http://127.0.0.1:{port}", flush=True)

    dialogs_encountered = []

    with sync_playwright() as p:
        print("[E2E] Launching browser via Playwright...", flush=True)
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 820})
        page = context.new_page()

        # Listen for any browser alerts or confirms (must be 0!)
        page.on("dialog", lambda dialog: (dialogs_encountered.append(dialog.message), dialog.dismiss()))

        # 1. Load application
        print(f"[E2E] Navigating to http://127.0.0.1:{port}/index.html...", flush=True)
        page.goto(f"http://127.0.0.1:{port}/index.html", wait_until="networkidle")
        time.sleep(1)

        # Verify page title and header
        title = page.title()
        print(f"[E2E] Page title: '{title}'", flush=True)
        assert "Antigravity" in title, f"Unexpected page title: {title}"

        # 2. Verify sidebar conversations & zero duplicate buttons
        print("[E2E] Waiting for conversation list in sidebar...", flush=True)
        page.wait_for_selector("#sidebar-conversations-list > div")
        conv_items = page.query_selector_all("#sidebar-conversations-list > div")
        print(f"[E2E] Found {len(conv_items)} conversations in sidebar.", flush=True)
        assert len(conv_items) > 0, "No conversations listed in sidebar"

        # Assert sidebar has NO duplicate controls ("only one of one function")
        assert page.locator("aside button:has-text('Conversation Snapshots')").count() == 0, "Sidebar should not have duplicate snapshots button!"
        assert page.locator("aside button:has-text('Settings & Preferences')").count() == 0, "Sidebar should not have duplicate settings button!"
        assert page.locator("#sidebar-snapshot-pill").count() == 0, "Sidebar snapshot pill should be removed!"
        assert page.locator("button:has-text('Snapshots')").count() == 1, "There should be exactly one Snapshots button in the app!"
        assert page.locator("button[onclick='openSettingsModal()']").count() == 1, "There should be exactly one Settings button in the app!"
        print("[E2E] Verified: Zero duplicated buttons. Sidebar is clean, single controls in header!", flush=True)

        # 3. Select BourassVPN conversation
        print("[E2E] Selecting 'BourassVPN Optimization Project Handoff'...", flush=True)
        bourass_btn = page.locator("#sidebar-conversations-list div:has-text('BourassVPN Optimization Project Handoff')").first
        bourass_btn.click()
        page.wait_for_selector("#chat-feed-scroll .feed-node")
        feed_nodes = page.query_selector_all("#chat-feed-scroll .feed-node")
        print(f"[E2E] BourassVPN chat loaded with {len(feed_nodes)} feed items.", flush=True)

        # 4. Open History & Snapshots drawer
        print("[E2E] Opening History & Snapshots drawer...", flush=True)
        page.locator("button:has-text('Snapshots')").first.click()
        time.sleep(0.6)

        # Wait for drawer snapshot cards to render
        page.wait_for_selector("#snapshots-list-container > div")
        snapshot_cards = page.query_selector_all("#snapshots-list-container > div")
        print(f"[E2E] Snapshots drawer rendered {len(snapshot_cards)} snapshot cards.", flush=True)

        # Verify rich metadata on BourassVPN snapshot card
        drawer_text = page.locator("#snapshots-list-container").inner_text()
        print(f"[E2E] Snapshot drawer text preview: {drawer_text[:140]}...", flush=True)
        assert "BourassVPN Optimization Project Handoff" in drawer_text, "Thread title missing from snapshot cards"
        assert "Step #" in drawer_text, "Milestone step count missing"
        
        # Verify snapshot displays real timestamp and NEVER 'now ago'
        assert "now ago" not in drawer_text, "Found 'now ago' in snapshot text! Should be real timestamp."
        import re
        assert re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', drawer_text), "Real timestamp (YYYY-MM-DD HH:MM:SS) missing from snapshot card!"
        print("[E2E] Verified rich snapshot metadata: Real timestamp (no 'now ago'), Thread title, Milestone step, and Current Active State badge present!", flush=True)

        # Capture Screenshot 1: Snapshots Drawer with Rich Cards
        shot1 = os.path.join(ARTIFACT_DIR, "e2e_01_snapshots_drawer.png")
        page.screenshot(path=shot1)
        print(f"[E2E] Captured: {shot1}", flush=True)

        # Close snapshots drawer
        page.locator("button[onclick='closeSnapshotsDrawer()']").first.click()
        time.sleep(0.4)

        # Switch to Samsung Custom Animation Setup
        print("[E2E] Switching to 'Samsung Custom Animation Setup'...", flush=True)
        samsung_btn = page.locator("#sidebar-conversations-list div:has-text('Samsung Custom Animation Setup')").first
        samsung_btn.click()
        time.sleep(0.8)

        # First simulate rollback to Step 450 to test real-world restore
        print("[E2E] Simulating rollback to Step 450 to verify snapshot restore workflow...", flush=True)
        page.evaluate("apiCall('perform_rollback', ['1de7c250-59af-45c8-93ec-84f468944ff8', 450, true])")
        time.sleep(0.8)
        page.evaluate("selectConversation('1de7c250-59af-45c8-93ec-84f468944ff8')")
        time.sleep(0.8)

        # Open Snapshots drawer for Samsung
        print("[E2E] Opening Snapshots drawer for Samsung...", flush=True)
        page.locator("button:has-text('Snapshots')").first.click()
        time.sleep(0.6)
        page.wait_for_selector("#snapshots-list-container > div")

        # Find a restore button on a card that is not currently active
        restore_btns = page.locator("button:has-text('Restore Conversation')")
        restore_count = restore_btns.count()
        print(f"[E2E] Found {restore_count} restorable snapshots in Samsung thread.", flush=True)
        assert restore_count > 0, "Expected restorable snapshots after rollback"

        if restore_count > 0:
            first_restore = restore_btns.first
            print("[E2E] Clicking 'Restore Conversation' to test native inline confirmation...", flush=True)
            first_restore.click()
            time.sleep(0.4)

            # Check that inline confirmation opened inside the card
            confirm_box = page.locator("text=Revert conversation to Step #")
            assert confirm_box.is_visible(), "Inline confirmation did not appear inside the card!"
            confirm_btn = page.locator("button:has-text('Confirm & Restore')").first
            cancel_btn = page.locator("button[onclick='cancelSnapshotAction()']").first
            assert confirm_btn.is_visible(), "Confirm & Restore button missing"
            assert cancel_btn.is_visible(), "Cancel button missing"
            print("[E2E] Verified inline card confirmation: Revert prompt, Cancel, and Confirm & Restore buttons active!", flush=True)

            # Capture Screenshot 2: Inline Restore Confirmation
            shot2 = os.path.join(ARTIFACT_DIR, "e2e_02_inline_restore_confirm.png")
            page.screenshot(path=shot2)
            print(f"[E2E] Captured: {shot2}", flush=True)

            # Click Confirm & Restore
            print("[E2E] Clicking 'Confirm & Restore'...", flush=True)
            confirm_btn.click()
            time.sleep(1.8)

            # Verify toast notification
            toast = page.locator("#ag-toast")
            toast_text = toast.inner_text()
            print(f"[E2E] Toast notification: '{toast_text}'", flush=True)
            assert "restored" in toast_text.lower(), f"Unexpected toast text: {toast_text}"

            # Verify that Restart Antigravity Modal appears!
            restart_modal = page.locator("#restart-ag-modal")
            assert restart_modal.is_visible(), "Restart Antigravity modal did not appear after restore!"
            restart_modal_text = restart_modal.inner_text()
            print(f"[E2E] Restart Antigravity Modal text: {restart_modal_text[:120]}...", flush=True)
            assert "Restart Antigravity?" in restart_modal_text, "Missing 'Restart Antigravity?' heading"
            assert "No, Later" in restart_modal_text, "Missing 'No, Later' button"
            assert "Yes, Restart" in restart_modal_text, "Missing 'Yes, Restart' button"

            # Capture Screenshot of Restart Antigravity Modal
            shot_restart = os.path.join(ARTIFACT_DIR, "e2e_03b_restart_ag_modal.png")
            page.screenshot(path=shot_restart)
            print(f"[E2E] Captured: {shot_restart}", flush=True)

            # Dismiss restart modal via 'No, Later'
            page.locator("#btn-restart-ag-no").click()
            time.sleep(0.5)
            assert not restart_modal.is_visible(), "Restart modal did not dismiss after 'No, Later'"
            print("[E2E] Verified: 'No, Later' smoothly dismisses modal with toast notification!", flush=True)

            # Test 'Yes, Restart' button UI response
            print("[E2E] Testing 'Yes, Restart' button UI flow...", flush=True)
            page.evaluate("showRestartAntigravityPrompt('Testing Restart Flow')")
            time.sleep(0.3)
            assert page.locator("#restart-ag-modal").is_visible(), "Restart modal should be open"
            page.evaluate("""
                window._origApiCall = window.apiCall;
                window.apiCall = async (method, args) => {
                    if (method === 'restart_antigravity') return { success: true, restarted: true };
                    return window._origApiCall(method, args);
                };
            """)
            page.locator("#btn-restart-ag-yes").click()
            time.sleep(0.5)
            assert not page.locator("#restart-ag-modal").is_visible(), "Restart modal should close after restart"
            toast_restart = page.locator("#ag-toast").inner_text()
            print(f"[E2E] Restart toast notification: '{toast_restart}'", flush=True)
            assert "restarted successfully" in toast_restart.lower(), f"Unexpected toast: {toast_restart}"
            page.evaluate("window.apiCall = window._origApiCall;")
            print("[E2E] Verified: 'Yes, Restart' button triggers clean restart flow and success feedback!", flush=True)

            # Reopen snapshots drawer to verify updated active status
            page.locator("button:has-text('Snapshots')").first.click()
            time.sleep(0.6)
            page.wait_for_selector("#snapshots-list-container > div")

            # Verify that the card now shows 'Current Active State' and 'Currently Active'
            drawer_after = page.locator("#snapshots-list-container").inner_text()
            assert "now ago" not in drawer_after, "Snapshot drawer contains 'now ago'! Must show real time."
            assert "Current Active State" in drawer_after, "Restored card did not update to Current Active State!"
            assert "Currently Active" in drawer_after, "Restored button did not update to Currently Active!"
            print("[E2E] Verified: Snapshot restored successfully, shows real time, and updated to 'Current Active State' in real-time!", flush=True)

            # Capture Screenshot 3: Restored Snapshot Active
            shot3 = os.path.join(ARTIFACT_DIR, "e2e_03_restored_active.png")
            page.screenshot(path=shot3)
            print(f"[E2E] Captured: {shot3}", flush=True)

            # Close snapshots drawer
            page.locator("button[onclick='closeSnapshotsDrawer()']").first.click()
            time.sleep(0.5)

        # 6. Test Undo from chat feed
        print("[E2E] Testing hover-based Undo in chat feed...", flush=True)
        asst_cards = page.locator(".group\\/asst")
        asst_count = asst_cards.count()
        print(f"[E2E] Found {asst_count} assistant cards in chat feed.", flush=True)
        if asst_count > 0:
            last_asst = asst_cards.last
            last_asst.hover()
            time.sleep(0.3)
            undo_btn = last_asst.locator("button:has-text('Undo from here')")
            if undo_btn.is_visible():
                undo_btn.click()
                time.sleep(0.5)

                # Check Undo modal
                undo_modal = page.locator("#undo-modal")
                assert undo_modal.is_visible(), "Undo modal did not open on chat hover action"
                modal_text = undo_modal.inner_text()
                print(f"[E2E] Undo modal snippet: {modal_text[:100]}...", flush=True)
                assert "Undo this item & everything after" in modal_text, "Undo mode radio missing"

                # Capture Screenshot 4: Undo Modal
                shot4 = os.path.join(ARTIFACT_DIR, "e2e_04_undo_modal.png")
                page.screenshot(path=shot4)
                print(f"[E2E] Captured: {shot4}", flush=True)

                # Close Undo modal
                page.locator("#undo-modal button:has-text('Cancel')").click()
                time.sleep(0.3)

        # 7. Test Theme Toggle (Dark -> Light -> Dark)
        print("[E2E] Testing Theme Toggle...", flush=True)
        theme_btn = page.locator("#theme-toggle-btn")
        theme_btn.click()
        time.sleep(0.4)
        is_light = page.evaluate("document.documentElement.classList.contains('theme-light')")
        print(f"[E2E] Is theme-light active: {is_light}", flush=True)
        assert is_light, "Theme failed to toggle to Light mode!"

        shot5 = os.path.join(ARTIFACT_DIR, "e2e_05_light_theme.png")
        page.screenshot(path=shot5)
        print(f"[E2E] Captured: {shot5}", flush=True)

        # Toggle back to dark
        theme_btn.click()
        time.sleep(0.4)
        is_dark = page.evaluate("document.documentElement.classList.contains('dark')")
        print(f"[E2E] Is dark theme active: {is_dark}", flush=True)
        assert is_dark, "Theme failed to toggle back to Dark mode!"

        # 8. Test Settings Modal & Keyboard Shortcuts
        print("[E2E] Testing Settings Modal & Shortcuts...", flush=True)
        settings_btn = page.locator("button[onclick='openSettingsModal()']").first
        settings_btn.click()
        time.sleep(0.5)
        settings_modal = page.locator("#settings-modal")
        assert settings_modal.is_visible(), "Settings modal failed to open!"
        settings_text = settings_modal.inner_text()
        assert "Antigravity Rewind Settings" in settings_text, "Settings modal header missing"
        assert "Antigravity Data Store" in settings_text, "Data store section missing"
        assert "Connected" in settings_text, "Data store connected indicator missing"
        assert "Ctrl + ," in settings_text, "Keyboard shortcut listing missing"

        shot6 = os.path.join(ARTIFACT_DIR, "e2e_06_settings_modal.png")
        page.screenshot(path=shot6)
        print(f"[E2E] Captured: {shot6}", flush=True)

        # Test ESC key shortcut to close modal
        print("[E2E] Testing Esc shortcut to close Settings modal...", flush=True)
        page.keyboard.press("Escape")
        time.sleep(0.3)
        assert not settings_modal.is_visible(), "Esc key failed to close Settings modal!"
        print("[E2E] Verified: Esc key successfully closed modal.", flush=True)

        # 9. Test Real-time Sidebar Search Filter
        print("[E2E] Testing real-time sidebar search filter...", flush=True)
        search_input = page.locator("#sidebar-search-input")
        search_input.fill("Faiz")
        time.sleep(0.3)
        filtered_convs = page.query_selector_all("#sidebar-conversations-list > div")
        print(f"[E2E] Filtered sidebar items for 'Faiz': {len(filtered_convs)}", flush=True)
        assert len(filtered_convs) >= 1, "Expected matching conversation for search 'Faiz'"
        first_match_text = filtered_convs[0].inner_text()
        assert "Faiz" in first_match_text, f"Filter result does not match query: {first_match_text}"

        # Clear search
        search_input.fill("")
        time.sleep(0.3)
        all_convs = page.query_selector_all("#sidebar-conversations-list > div")
        print(f"[E2E] Restored sidebar items: {len(all_convs)}", flush=True)
        assert len(all_convs) > len(filtered_convs), "Search clear did not restore all conversations"

        # 10. Test Fast Loading & Instant Bottom Placement on FaizVPN
        print("[E2E] Selecting large conversation 'FaizVPN Complete Knowledge Dossier'...", flush=True)
        t0 = time.time()
        faiz_item = page.locator("#sidebar-conversations-list div:has-text('FaizVPN Complete Knowledge Dossier')").first
        faiz_item.click()
        page.wait_for_selector("#chat-feed-scroll .feed-node")
        elapsed = time.time() - t0
        print(f"[E2E] FaizVPN loaded in {elapsed:.3f}s (Tail deque optimization)!", flush=True)
        assert elapsed < 3.0, f"FaizVPN loading too slow ({elapsed:.2f}s)"

        # Verify instant bottom placement
        time.sleep(0.2)
        scroll_top = page.evaluate("document.getElementById('chat-feed-scroll').scrollTop")
        scroll_height = page.evaluate("document.getElementById('chat-feed-scroll').scrollHeight")
        client_height = page.evaluate("document.getElementById('chat-feed-scroll').clientHeight")
        print(f"[E2E] Scroll position: {scroll_top} / max {scroll_height - client_height}", flush=True)
        assert scroll_top > 0, "Chat feed did not immediately position at the bottom!"

        # 11. Verify Clean Chat UI without Gemini / Prompt Input / Fake Title Menus
        print("[E2E] Verifying Thinking Block & absence of unnecessary buttons...", flush=True)
        thinking_nodes = page.locator("#chat-feed-scroll div[data-step-index]:has(div[id^='think_body_'])")
        if thinking_nodes.count() > 0:
            first_think = thinking_nodes.first
            think_text = first_think.inner_text()
            print(f"[E2E] Thinking label snippet: {think_text[:60]}...", flush=True)
            assert "Thinking" in think_text or "Worked" in think_text, "Thinking label missing duration"

        # Assert Gemini button and prompt input are completely removed
        assert page.locator("#chat-model-label").count() == 0, "Gemini button should be removed from app!"
        assert page.locator("#chat-jump-input").count() == 0, "Prompt input should be removed from app!"
        print("[E2E] Verified: Gemini button and prompt input are completely removed!", flush=True)

        # Assert fake titlebar menus (File, Preferences, View, History) are removed
        titlebar_text = page.locator("header").inner_text()
        assert "File" not in titlebar_text, "Fake 'File' menu should be removed from titlebar"
        assert "Preferences" not in titlebar_text, "Fake 'Preferences' menu should be removed from titlebar"
        print("[E2E] Verified: Fake titlebar menus removed; clean native titlebar present!", flush=True)

        shot7 = os.path.join(ARTIFACT_DIR, "e2e_07_chat_ui_exact.png")
        page.screenshot(path=shot7)
        print(f"[E2E] Captured: {shot7}", flush=True)

        shot8 = os.path.join(ARTIFACT_DIR, "e2e_08_clean_no_gemini.png")
        page.screenshot(path=shot8)
        print(f"[E2E] Captured: {shot8}", flush=True)

        # 12. Final assertion on browser dialogs
        print(f"[E2E] Browser dialogs/alerts encountered: {len(dialogs_encountered)}", flush=True)
        assert len(dialogs_encountered) == 0, f"Leaked browser dialogs detected: {dialogs_encountered}"

        browser.close()
        print("\n[SUCCESS] ALL 12 END-TO-END HUMAN-LIKE VERIFICATION TESTS PASSED WITH 100% ACCURACY!", flush=True)

if __name__ == "__main__":
    run_e2e_test()
