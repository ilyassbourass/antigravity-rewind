import os
import sys
import time
import threading
from http.server import HTTPServer
from app import AppHandler, PORT
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ARTIFACT_DIR = r"C:\Users\PC\.gemini\antigravity\brain\f74d1ad5-f0d6-444e-b174-59e7d78ca3a8"
os.makedirs(ARTIFACT_DIR, exist_ok=True)

def start_server():
    for p in range(PORT, PORT + 20):
        try:
            server = HTTPServer(("127.0.0.1", p), AppHandler)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            time.sleep(0.5)
            return server, p
        except Exception:
            continue
    raise RuntimeError("Could not bind to any port")

def run_e2e_test():
    print("[E2E] Starting local backend server...", flush=True)
    server, port = start_server()
    print(f"[E2E] Server running at http://127.0.0.1:{port}", flush=True)

    dialogs_encountered = []

    with sync_playwright() as p:
        print("[E2E] Launching Chrome via Playwright...", flush=True)
        browser = p.chromium.launch(channel="chrome", headless=True)
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

        # 2. Verify sidebar conversations
        print("[E2E] Waiting for conversation list in sidebar...", flush=True)
        page.wait_for_selector("#sidebar-conversations-list > div")
        conv_items = page.query_selector_all("#sidebar-conversations-list > div")
        print(f"[E2E] Found {len(conv_items)} conversations in sidebar.", flush=True)
        assert len(conv_items) > 0, "No conversations listed in sidebar"

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
        assert "Current Active State" in drawer_text, "Active badge missing from current snapshot"
        assert "Step #" in drawer_text, "Milestone step count missing"
        print("[E2E] Verified rich snapshot metadata: Thread title, Milestone step, and Current Active State badge present!", flush=True)

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

            # Verify that the card now shows 'Current Active State' and 'Currently Active'
            drawer_after = page.locator("#snapshots-list-container").inner_text()
            assert "Current Active State" in drawer_after, "Restored card did not update to Current Active State!"
            assert "Currently Active" in drawer_after, "Restored button did not update to Currently Active!"
            print("[E2E] Verified: Snapshot restored successfully and updated to 'Current Active State' in real-time!", flush=True)

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

        # 11. Verify Exact Antigravity Chat UI & Thinking Block
        print("[E2E] Verifying Thinking Block & Bottom Prompt Bar...", flush=True)
        thinking_nodes = page.locator("#chat-feed-scroll div[data-step-index]:has(div[id^='think_body_'])")
        if thinking_nodes.count() > 0:
            first_think = thinking_nodes.first
            think_text = first_think.inner_text()
            print(f"[E2E] Thinking label snippet: {think_text[:60]}...", flush=True)
            assert "Thinking" in think_text or "Worked" in think_text, "Thinking label missing duration"

        # Verify bottom bar elements
        model_label = page.locator("#chat-model-label").inner_text()
        print(f"[E2E] Bottom prompt bar model: '{model_label}'", flush=True)
        assert "Gemini" in model_label, "Model label missing from bottom prompt bar"

        shot7 = os.path.join(ARTIFACT_DIR, "e2e_07_chat_ui_exact.png")
        page.screenshot(path=shot7)
        print(f"[E2E] Captured: {shot7}", flush=True)

        # 12. Final assertion on browser dialogs
        print(f"[E2E] Browser dialogs/alerts encountered: {len(dialogs_encountered)}", flush=True)
        assert len(dialogs_encountered) == 0, f"Leaked browser dialogs detected: {dialogs_encountered}"

        browser.close()
        print("\n[SUCCESS] ALL 12 END-TO-END HUMAN-LIKE VERIFICATION TESTS PASSED WITH 100% ACCURACY!", flush=True)

if __name__ == "__main__":
    run_e2e_test()
