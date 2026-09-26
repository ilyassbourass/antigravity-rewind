import os
import json
import sqlite3
from backend import RewindBackend

backend = RewindBackend()
cid = '1de7c250-59af-45c8-93ec-84f468944ff8'

print(f"=== Starting End-to-End Verification on {cid} ===")
# 1. Initial State
init_steps = backend.get_steps(cid)
init_count = len(init_steps['steps'])
print(f"[STEP 1] Initial step count: {init_count}")
assert init_count == 472, f"Expected 472 steps, got {init_count}"

# 2. Perform Rollback to Step 467
target_step = 467
print(f"[STEP 2] Performing rollback to step {target_step}...")
rb_res = backend.perform_rollback(cid, target_step, make_backup=True)
print(f"Rollback result: {rb_res}")
assert rb_res.get('success') is True, f"Rollback failed: {rb_res}"

# Verify rolled back state
rb_steps = backend.get_steps(cid)
rb_count = len(rb_steps['steps'])
print(f"Post-rollback step count: {rb_count}")
assert rb_count == target_step + 1, f"Expected {target_step + 1} steps, got {rb_count}"
assert rb_steps['steps'][-1]['step_index'] == target_step, "Last step index mismatch"

# Verify SQLite DB
db_path = os.path.join(backend.base_path, 'conversations', f'{cid}.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT MAX(idx), COUNT(*) FROM steps;')
max_idx, total_db_steps = cur.fetchone()
cur.execute('PRAGMA integrity_check;')
db_integrity = cur.fetchone()[0]
conn.close()
print(f"SQLite DB MAX(idx): {max_idx}, total count: {total_db_steps}, integrity: {db_integrity}")
assert max_idx == target_step, f"DB max idx {max_idx} != target {target_step}"
assert db_integrity == 'ok', "DB integrity failed"

# Verify chunks byte parity
brain = os.path.join(backend.base_path, 'brain', cid)
logs = os.path.join(brain, '.system_generated', 'logs')
t_path = os.path.join(logs, 'transcript.jsonl')
t_size = os.path.getsize(t_path)
c_dir = os.path.join(logs, 'chunks', 'transcript')
c_size = sum(os.path.getsize(os.path.join(c_dir, f)) for f in os.listdir(c_dir) if f.endswith('.jsonl'))
print(f"transcript.jsonl size: {t_size} bytes, total chunk bytes: {c_size} bytes")
assert t_size == c_size, f"Chunk byte mismatch: {t_size} != {c_size}"

# 3. Test Restore from Snapshot
backups = backend.list_backups(cid)
print(f"[STEP 3] Backups available: {len(backups)}")
latest_backup = backups[0]
print(f"Restoring from latest backup: {latest_backup['name']}...")
res_res = backend.restore_backup(cid, latest_backup['path'])
print(f"Restore result: {res_res}")
assert res_res.get('success') is True, f"Restore failed: {res_res}"

# Verify restored state
restored_steps = backend.get_steps(cid)
restored_count = len(restored_steps['steps'])
print(f"[STEP 4] Restored step count: {restored_count}")
assert restored_count == init_count, f"Expected {init_count} steps after restore, got {restored_count}"

# Verify restored SQLite DB integrity
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT MAX(idx), COUNT(*) FROM steps;')
max_idx_r, total_db_steps_r = cur.fetchone()
cur.execute('PRAGMA integrity_check;')
db_integrity_r = cur.fetchone()[0]
conn.close()
print(f"Restored SQLite MAX(idx): {max_idx_r}, integrity: {db_integrity_r}")
assert max_idx_r == init_count - 1, "Restored DB max idx mismatch"
assert db_integrity_r == 'ok', "Restored DB integrity failed"

print("\n>>> END-TO-END VERIFICATION PASSED PERFECTLY WITH ZERO DEFECTS! <<<")
