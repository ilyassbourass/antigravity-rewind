import os
import json
import sqlite3

cid = '1de7c250-59af-45c8-93ec-84f468944ff8'
base_p = os.path.expandvars(r'%USERPROFILE%\.gemini\antigravity')

# 1. SQLite DB
db_path = os.path.join(base_p, 'conversations', f'{cid}.db')
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT COUNT(*), MAX(idx) FROM steps;')
count, max_idx = cur.fetchone()
print(f"DB steps count: {count}, MAX(idx): {max_idx}")

# Fetch last 5 rows from DB
cur.execute('SELECT idx, step_type, status FROM steps ORDER BY idx DESC LIMIT 5;')
rows = cur.fetchall()
for r in rows:
    print(f"DB row idx: {r[0]}, type: {r[1]}, status: {r[2]}")
conn.close()

# 2. Transcript files
brain_p = os.path.join(base_p, 'brain', cid, '.system_generated', 'logs')
t_path = os.path.join(brain_p, 'transcript.jsonl')
tf_path = os.path.join(brain_p, 'transcript_full.jsonl')

with open(t_path, 'r', encoding='utf-8') as f:
    t_lines = [json.loads(l) for l in f if l.strip()]
print(f"transcript.jsonl lines: {len(t_lines)}, last step_index: {t_lines[-1].get('step_index') if t_lines else None}")

with open(tf_path, 'r', encoding='utf-8') as f:
    tf_lines = [json.loads(l) for l in f if l.strip()]
print(f"transcript_full.jsonl lines: {len(tf_lines)}, last step_index: {tf_lines[-1].get('step_index') if tf_lines else None}")

# 3. Check chunks
c_dir = os.path.join(brain_p, 'chunks', 'transcript')
if os.path.exists(c_dir):
    chunks = sorted(os.listdir(c_dir))
    print(f"chunks: {len(chunks)} files, last chunk: {chunks[-1] if chunks else None}")

# Check backups
b_dir = os.path.join(base_p, 'brain', cid, 'backups')
if os.path.exists(b_dir):
    print("Backups:")
    for b in sorted(os.listdir(b_dir)):
        print(f"  {b}")
