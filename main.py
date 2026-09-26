import os
import sys
import argparse
import webview
from backend import RewindBackend

class Api:
    def __init__(self, backend):
        self.backend = backend

    def get_kpi_stats(self):
        return self.backend.get_kpi_stats()

    def discover_conversations(self):
        return self.backend.discover_conversations()

    def get_steps(self, conv_id):
        return self.backend.get_steps(conv_id)

    def perform_rollback(self, conv_id, target_step_index, make_backup=True):
        return self.backend.perform_rollback(conv_id, target_step_index, make_backup)

    def list_backups(self, conv_id):
        return self.backend.list_backups(conv_id)

    def restore_backup(self, conv_id, backup_folder_path):
        return self.backend.restore_backup(conv_id, backup_folder_path)


def start_desktop_gui(backend):
    api = Api(backend)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS

    html_path = os.path.join(base_dir, "index.html")

    window = webview.create_window(
        title="Antigravity Rewind",
        url=html_path,
        js_api=api,
        width=1280,
        height=820,
        min_size=(1000, 650),
        background_color="#0c0e14"
    )

    webview.start(debug=False)


def run_cli(backend, args):
    if args.list:
        convs = backend.discover_conversations()
        print(f"\nDiscovered {len(convs)} Antigravity conversations:")
        print("-" * 75)
        for c in convs:
            print(f"[{c['id']}]  {c['title']:<40}  ({c['step_count']} steps, {c['size_formatted']})")
        print("-" * 75)
    elif args.rollback:
        cid, step = args.rollback
        print(f"Executing rollback on {cid} to step {step}...")
        res = backend.perform_rollback(cid, int(step), make_backup=True)
        if res.get("success"):
            print(f"[SUCCESS] Conversation {cid} rolled back to step {step}. Backup created.")
        else:
            print(f"[FAILED] Error: {res.get('error')}")
    elif args.restore:
        cid = args.restore
        backups = backend.list_backups(cid)
        if not backups:
            print(f"No backups found for {cid}")
            return
        latest = backups[0]
        print(f"Restoring {cid} from {latest['name']}...")
        res = backend.restore_backup(cid, latest['path'])
        if res.get("success"):
            print(f"[SUCCESS] Conversation {cid} restored from {latest['name']}.")
        else:
            print(f"[FAILED] Error: {res.get('error')}")


def main():
    parser = argparse.ArgumentParser(description="Antigravity Thread Rewind Tool")
    parser.add_argument("--list", "-l", action="store_true", help="List all conversations")
    parser.add_argument("--rollback", "-r", nargs=2, metavar=("CONV_ID", "STEP_INDEX"), help="Rollback conversation to step")
    parser.add_argument("--restore", metavar="CONV_ID", help="Restore conversation from latest backup")
    parser.add_argument("--path", help="Custom path to Antigravity directory")

    args = parser.parse_args()
    backend = RewindBackend(args.path)

    if args.list or args.rollback or args.restore:
        run_cli(backend, args)
    else:
        start_desktop_gui(backend)


if __name__ == "__main__":
    main()
