import os
import json
import sqlite3
import shutil
import re
from datetime import datetime

class RewindBackend:
    def __init__(self, base_path=None):
        if not base_path:
            user_profile = os.environ.get("USERPROFILE", os.path.expanduser("~"))
            self.base_path = os.path.join(user_profile, ".gemini", "antigravity")
        else:
            self.base_path = base_path
        self._title_cache = {}

    def get_kpi_stats(self):
        convs = self.discover_conversations()
        total_sessions = len(convs)
        total_steps = sum(c.get("step_count", 0) for c in convs)
        total_backups = 0
        total_storage_bytes = 0

        for c in convs:
            cid = c["id"]
            brain = c["brain_path"]
            backups_dir = os.path.join(brain, "backups")
            if os.path.exists(backups_dir):
                total_backups += len([d for d in os.listdir(backups_dir) if os.path.isdir(os.path.join(backups_dir, d))])
            if os.path.exists(os.path.join(brain, "backup_before_delete")):
                total_backups += 1
            if os.path.exists(c["db_path"]):
                total_storage_bytes += os.path.getsize(c["db_path"])

        return {
            "total_sessions": total_sessions,
            "active_sessions": total_sessions,
            "total_steps": total_steps,
            "total_steps_formatted": f"{total_steps:,}" if total_steps < 10000 else f"{total_steps/1000:.1f}K",
            "total_backups": total_backups,
            "total_storage_formatted": self.format_bytes(total_storage_bytes),
            "antigravity_path": self.base_path
        }

    def clean_title_text(self, text, max_len=45):
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'^(The following is a|You are the|You are an?|Please|Can you|Could you|I want you to|I want u to)\s+', '', text, flags=re.I)
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            return ""
        first_line = lines[0]
        first_line = re.sub(r'^[#*_\->`\s]+', '', first_line)
        first_line = re.sub(r'[#*_\->`]+', '', first_line)
        first_line = first_line.strip('"\' ')
        if len(first_line) > max_len:
            truncated = first_line[:max_len]
            last_space = truncated.rfind(' ')
            if last_space > 20:
                first_line = truncated[:last_space] + "..."
            else:
                first_line = truncated + "..."
        if first_line:
            first_line = first_line[0].upper() + first_line[1:]
        return first_line

    def _get_summaries_map(self):
        summaries_map = {}
        s_db = os.path.join(self.base_path, "conversation_summaries.db")
        if os.path.exists(s_db):
            try:
                conn = sqlite3.connect(s_db)
                cur = conn.cursor()
                cur.execute("SELECT conversation_id, title, preview, agent_name, parent_conversation_id FROM conversation_summaries;")
                for cid, t, prev, agent, parent in cur.fetchall():
                    summaries_map[cid] = {
                        "title": (t or "").strip(),
                        "preview": (prev or "").strip(),
                        "agent_name": (agent or "").strip(),
                        "parent_id": (parent or "").strip()
                    }
                conn.close()
            except Exception:
                pass
        return summaries_map

    def _resolve_subagent_title(self, cid, s_info):
        parent_id = s_info.get("parent_id")
        agent_name = s_info.get("agent_name")
        brain_dir = os.path.join(self.base_path, "brain")

        # Check subagent's own transcript
        t_file = os.path.join(brain_dir, cid, ".system_generated", "logs", "transcript.jsonl")
        if os.path.exists(t_file):
            try:
                with open(t_file, "r", encoding="utf-8", errors="ignore") as f:
                    for _ in range(5):
                        line = f.readline()
                        if not line: break
                        d = json.loads(line)
                        cnt = d.get("content") or ""
                        m_role = re.search(r"content=(?:You are (?:the|an?) )?([^.\n]+?)(?: for an? (?:exhaustive )?investigation on:?|:|\.)", cnt)
                        if m_role:
                            r_name = self.clean_title_text(m_role.group(1), 32)
                            if r_name and len(r_name) > 3:
                                return f"Subagent: {r_name}"
                        m_build = re.search(r"content=(?:Build the |Reverse-engineering |Investigate )([^.\n`]+)", cnt, re.I)
                        if m_build:
                            b_name = self.clean_title_text(m_build.group(1), 32)
                            if b_name:
                                return f"Subagent: {b_name}"
                        m_cnt = re.search(r"content=([^.\n]+?)(?:\.|\n|$)", cnt)
                        if m_cnt:
                            c_text = self.clean_title_text(m_cnt.group(1), 32)
                            if c_text and len(c_text) > 4:
                                return f"Subagent: {c_text}"
            except Exception:
                pass

        # Check parent transcript
        if parent_id:
            pt_file = os.path.join(brain_dir, parent_id, ".system_generated", "logs", "transcript.jsonl")
            if os.path.exists(pt_file):
                try:
                    with open(pt_file, "r", encoding="utf-8", errors="ignore") as pf:
                        for pline in pf:
                            if cid in pline:
                                m_r = re.search(r'"role":\s*"([^"]+)"', pline) or re.search(r'\\"role\\":\s*\\"([^\\"]+)\\"', pline)
                                if m_r:
                                    return f"Subagent: {m_r.group(1)}"
                except Exception:
                    pass

        if agent_name and agent_name not in ('self', 'MODEL_TIER_INHERIT'):
            return f"Subagent ({agent_name})"
        return "Subagent Task"

    def resolve_conversation_title(self, cid, step_count=0, summaries_map=None, force_refresh=False):
        if not force_refresh and cid in self._title_cache:
            cached = self._title_cache[cid]
            if cached and not cached.startswith("Session ("):
                return cached

        annot_dir = os.path.join(self.base_path, "annotations")
        brain_dir = os.path.join(self.base_path, "brain")

        # 1. Annotations pbtxt
        pb_path = os.path.join(annot_dir, f"{cid}.pbtxt")
        if os.path.exists(pb_path):
            try:
                with open(pb_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    m = re.search(r'title:\s*"([^"]+)"', content)
                    if m:
                        val = m.group(1).strip()
                        if val and val != cid and not val.startswith(cid[:8]):
                            self._title_cache[cid] = val
                            return val
            except Exception:
                pass

        # 2. conversation_summaries.db
        if summaries_map is None:
            summaries_map = self._get_summaries_map()

        s_info = summaries_map.get(cid)
        if s_info:
            s_title = s_info.get("title", "")
            if s_title and s_title != cid and not s_title.startswith(cid[:8]):
                self._title_cache[cid] = s_title
                return s_title

            # Subagent detection via parent_conversation_id
            if s_info.get("parent_id"):
                sub_title = self._resolve_subagent_title(cid, s_info)
                if sub_title:
                    self._title_cache[cid] = sub_title
                    return sub_title

            # Summaries preview
            preview = s_info.get("preview", "")
            if preview and preview != cid and not preview.startswith(cid[:8]):
                cleaned = self.clean_title_text(preview)
                if cleaned:
                    self._title_cache[cid] = cleaned
                    return cleaned

        # 3. Transcript inspection (User requests or Subagent system messages)
        brain_path = os.path.join(brain_dir, cid)
        logs_path = os.path.join(brain_path, ".system_generated", "logs")
        for tf_name in ("transcript.jsonl", "transcript_full.jsonl"):
            t_path = os.path.join(logs_path, tf_name)
            if os.path.exists(t_path):
                try:
                    with open(t_path, "r", encoding="utf-8", errors="ignore") as f:
                        for _ in range(25):
                            line = f.readline()
                            if not line:
                                break
                            d = json.loads(line)
                            cnt = d.get("content") or ""
                            tp = d.get("type") or ""
                            src = d.get("source") or ""

                            # User prompt
                            if tp == "USER_INPUT" or src == "USER_EXPLICIT" or "<USER_REQUEST>" in cnt:
                                req_m = re.search(r'<USER_REQUEST>\s*(.*?)(?:</USER_REQUEST>|$)', cnt, re.DOTALL)
                                prompt_text = req_m.group(1) if req_m else cnt
                                cleaned = self.clean_title_text(prompt_text)
                                if cleaned:
                                    self._title_cache[cid] = cleaned
                                    return cleaned

                            # Subagent content
                            if "content=" in cnt and ("You are" in cnt or "sender=" in cnt):
                                m_sub = re.search(r'content=(?:You are the |Build the |Reverse-engineering )?([^.\n]+)', cnt)
                                if m_sub:
                                    c_name = self.clean_title_text(m_sub.group(1), 35)
                                    if c_name:
                                        res = f"Subagent: {c_name}"
                                        self._title_cache[cid] = res
                                        return res
                except Exception:
                    pass
                break

        if step_count == 0:
            return "New Blank Session"

        fallback = f"Session ({cid[:8]})"
        self._title_cache[cid] = fallback
        return fallback

    def discover_conversations(self):
        convs = []
        conv_dir = os.path.join(self.base_path, "conversations")
        annot_dir = os.path.join(self.base_path, "annotations")
        brain_dir = os.path.join(self.base_path, "brain")

        if not os.path.exists(conv_dir):
            return convs

        summaries_map = self._get_summaries_map()

        for f in os.listdir(conv_dir):
            if f.endswith(".db"):
                cid = f[:-3]
                db_path = os.path.join(conv_dir, f)

                step_count = 0
                try:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute("SELECT MAX(idx) FROM steps;")
                    m = cur.fetchone()[0]
                    if m is not None:
                        step_count = m + 1
                    else:
                        cur.execute("SELECT COUNT(*) FROM steps;")
                        step_count = cur.fetchone()[0]
                    conn.close()
                except:
                    pass

                title = self.resolve_conversation_title(cid, step_count, summaries_map)

                mtime = os.path.getmtime(db_path)
                dt = datetime.fromtimestamp(mtime)
                size_bytes = os.path.getsize(db_path)
                brain_path = os.path.join(brain_dir, cid)

                # Check if backups exist
                backup_count = 0
                b_dir = os.path.join(brain_path, "backups")
                if os.path.exists(b_dir):
                    backup_count += len([d for d in os.listdir(b_dir) if os.path.isdir(os.path.join(b_dir, d))])
                if os.path.exists(os.path.join(brain_path, "backup_before_delete")):
                    backup_count += 1
                has_backup = backup_count > 0

                convs.append({
                    "id": cid,
                    "title": title,
                    "step_count": step_count,
                    "size_bytes": size_bytes,
                    "size_formatted": self.format_bytes(size_bytes),
                    "last_modified": dt.strftime("%Y-%m-%d %H:%M"),
                    "last_modified_timestamp": mtime,
                    "relative_time": self.format_relative_time(mtime),
                    "db_path": db_path,
                    "brain_path": brain_path,
                    "logs_path": os.path.join(brain_path, ".system_generated", "logs"),
                    "has_backup": has_backup,
                    "backup_count": backup_count
                })

        convs.sort(key=lambda x: x["last_modified_timestamp"], reverse=True)
        return convs

    def format_relative_time(self, timestamp):
        import time
        now = time.time()
        diff = max(0, int(now - timestamp))
        if diff < 60:
            return "Just now"
        elif diff < 3600:
            return f"{diff // 60}m"
        elif diff < 86400:
            return f"{diff // 3600}h"
        elif diff < 86400 * 30:
            return f"{diff // 86400}d"
        elif diff < 86400 * 365:
            return f"{diff // (86400 * 30)}mo"
        else:
            return f"{diff // (86400 * 365)}y"

    def get_chat_feed(self, conv_id, limit=0):
        brain_path = os.path.join(self.base_path, "brain", conv_id)
        logs_path = os.path.join(brain_path, ".system_generated", "logs")
        tf_path = os.path.join(logs_path, "transcript_full.jsonl")
        t_path = os.path.join(logs_path, "transcript.jsonl")

        target_path = tf_path if os.path.exists(tf_path) else t_path
        if not os.path.exists(target_path):
            return []

        feed = []
        current_tools = []
        is_truncated = False

        def flush_tools():
            nonlocal current_tools
            if not current_tools:
                return
            exp_files = 0
            exp_searches = 0
            exp_commands = 0
            group_items = []

            for t in current_tools:
                name = t.get('name') or ''
                args = t.get('args', {})
                s_idx = t.get('step_index', 0)
                
                if name in ['write_to_file', 'replace_file_content']:
                    if group_items:
                        start_idx = group_items[0]['step_index']
                        feed.append({
                            'id': f"tg_{group_items[-1]['step_index']}",
                            'type': 'tool_group',
                            'step_index': group_items[-1]['step_index'],
                            'start_step_index': start_idx,
                            'undo_target_step': max(-1, start_idx - 1),
                            'files': exp_files,
                            'searches': exp_searches,
                            'commands': exp_commands,
                            'items': group_items
                        })
                        exp_files = exp_searches = exp_commands = 0
                        group_items = []

                    tf = args.get('TargetFile', '')
                    fn = os.path.basename(tf) or 'file'
                    icon = '</>'
                    if fn.endswith('.py'): icon = '🐍'
                    elif fn.endswith('.cs'): icon = '#'
                    elif fn.endswith('.json'): icon = '{}'
                    elif fn.endswith('.md'): icon = '📝'
                    elif fn.endswith('.bat') or fn.endswith('.sh') or fn.endswith('.ps1'): icon = '⚙️'

                    add_lines = 0
                    del_lines = 0
                    content = args.get('CodeContent') or args.get('ReplacementContent') or ''
                    if content:
                        add_lines = len(content.splitlines())
                    else:
                        add_lines = 1
                    if name == 'replace_file_content':
                        tcontent = args.get('TargetContent', '')
                        if tcontent:
                            del_lines = len(tcontent.splitlines())

                    feed.append({
                        'id': f"edit_{s_idx}",
                        'type': 'file_edit',
                        'step_index': s_idx,
                        'undo_target_step': max(-1, s_idx - 1),
                        'tool_name': name,
                        'filename': fn,
                        'filepath': tf,
                        'icon': icon,
                        'add_lines': add_lines,
                        'del_lines': del_lines,
                        'instruction': args.get('Instruction', '') or args.get('Description', '') or ''
                    })
                else:
                    if name in ['view_file', 'read_url_content']:
                        exp_files += 1
                    elif name in ['search_web']:
                        exp_searches += 1
                    elif name in ['run_command']:
                        exp_commands += 1
                    else:
                        exp_commands += 1
                    group_items.append(t)

            if group_items:
                start_idx = group_items[0]['step_index']
                feed.append({
                    'id': f"tg_{group_items[-1]['step_index']}",
                    'type': 'tool_group',
                    'step_index': group_items[-1]['step_index'],
                    'start_step_index': start_idx,
                    'undo_target_step': max(-1, start_idx - 1),
                    'files': exp_files,
                    'searches': exp_searches,
                    'commands': exp_commands,
                    'items': group_items
                })
            current_tools = []

        with open(target_path, 'r', encoding='utf-8') as f:
            if limit and limit > 0:
                from collections import deque
                file_size = os.path.getsize(target_path)
                if file_size > 2 * 1024 * 1024:
                    raw_lines = list(deque(f, maxlen=limit + 50))
                    is_truncated = True
                else:
                    all_lines = f.readlines()
                    if len(all_lines) > limit + 50:
                        raw_lines = all_lines[-(limit + 50):]
                        is_truncated = True
                    else:
                        raw_lines = all_lines
            else:
                raw_lines = f.readlines()

            for line_idx, line in enumerate(raw_lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    s_idx = obj.get('step_index', line_idx)
                    source = obj.get('source')
                    m_type = obj.get('type')
                    content = obj.get('content', '')
                    thinking = obj.get('thinking', '')
                    t_calls = obj.get('tool_calls', [])

                    if source == 'USER_EXPLICIT' or m_type == 'USER_INPUT':
                        flush_tools()
                        req_text = content
                        m = re.search(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', content, re.DOTALL)
                        if m:
                            req_text = m.group(1).strip()
                        feed.append({
                            'id': f"user_{s_idx}",
                            'type': 'user',
                            'step_index': s_idx,
                            'undo_target_step': max(-1, s_idx - 1),
                            'text': req_text,
                            'timestamp': obj.get('created_at', '')
                        })
                    elif m_type == 'PLANNER_RESPONSE':
                        if thinking and thinking.strip():
                            flush_tools()
                            dur_sec = max(8, min(58, len(thinking) // 25))
                            dur_label = f"Thinking for {dur_sec}s" if len(thinking) < 1600 else f"Worked for {max(1, len(thinking) // 1600)}m"
                            feed.append({
                                'id': f"think_{s_idx}",
                                'type': 'thinking',
                                'step_index': s_idx,
                                'undo_target_step': max(-1, s_idx - 1),
                                'thinking': thinking.strip(),
                                'length': len(thinking),
                                'duration_label': dur_label,
                                'timestamp': obj.get('created_at', '')
                            })

                        if content and content.strip():
                            flush_tools()
                            feed.append({
                                'id': f"asst_{s_idx}",
                                'type': 'assistant',
                                'step_index': s_idx,
                                'undo_target_step': max(-1, s_idx - 1),
                                'keep_target_step': s_idx,
                                'text': content.strip(),
                                'timestamp': obj.get('created_at', '')
                            })

                        if t_calls:
                            for tc in t_calls:
                                current_tools.append({
                                    'step_index': s_idx,
                                    'name': tc.get('name'),
                                    'args': tc.get('args', {})
                                })
                    elif m_type == 'GENERIC':
                        # Tool execution output: attach to the last tool in current_tools
                        if current_tools:
                            current_tools[-1]['output'] = content.strip()
                except:
                    pass

        flush_tools()
        if is_truncated and feed:
            total_steps = len(feed)
            db_path = os.path.join(self.base_path, "brain", f"{conv_id}.db")
            if os.path.exists(db_path):
                try:
                    conn = sqlite3.connect(db_path)
                    cur = conn.cursor()
                    cur.execute("SELECT MAX(idx) FROM steps;")
                    m = cur.fetchone()[0]
                    if m is not None:
                        total_steps = m + 1
                    conn.close()
                except:
                    pass
            feed.insert(0, {
                'id': 'earlier_banner',
                'type': 'earlier_banner',
                'step_index': 0,
                'total_steps': total_steps,
                'loaded_steps': len(feed),
                'message': f'Showing latest {len(feed)} steps. Click to load all {total_steps} steps.'
            })
        return feed

    def get_conversation_prompts(self, conv_id):
        brain_path = os.path.join(self.base_path, "brain", conv_id)
        logs_path = os.path.join(brain_path, ".system_generated", "logs")
        t_path = os.path.join(logs_path, "transcript.jsonl")
        tf_path = os.path.join(logs_path, "transcript_full.jsonl")
        target_path = t_path if os.path.exists(t_path) else tf_path

        prompts = []
        if not os.path.exists(target_path):
            return prompts

        try:
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f):
                    if '"USER_INPUT"' in line or '"USER_EXPLICIT"' in line:
                        try:
                            obj = json.loads(line.strip())
                            tp = obj.get("type")
                            src = obj.get("source")
                            if src == "USER_EXPLICIT" or tp == "USER_INPUT":
                                cnt = obj.get("content", "")
                                m = re.search(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', cnt, re.DOTALL)
                                req_text = m.group(1).strip() if m else cnt
                                prompts.append({
                                    "step_index": obj.get("step_index", line_idx),
                                    "text": req_text,
                                    "timestamp": obj.get("created_at", "")
                                })
                        except Exception:
                            continue
        except Exception as e:
            print(f"[get_conversation_prompts] Error: {e}")

        return prompts

    def get_steps(self, conv_id):
        brain_path = os.path.join(self.base_path, "brain", conv_id)
        logs_path = os.path.join(brain_path, ".system_generated", "logs")
        t_path = os.path.join(logs_path, "transcript.jsonl")

        empty_res = {
            "steps": [],
            "stats": {"total": 0, "user": 0, "assistant": 0, "tool": 0, "output": 0, "system": 0},
            "density": []
        }

        if not os.path.exists(t_path):
            return empty_res

        steps = []
        user_c = assistant_c = tool_c = output_c = system_c = 0

        with open(t_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    s_idx = obj.get("step_index", line_idx)
                    source = obj.get("source", "")
                    m_type = obj.get("type", "")
                    created = obj.get("created_at", "")
                    content = obj.get("content", "")
                    thinking = obj.get("thinking", "")
                    tool_calls = obj.get("tool_calls", [])

                    category = "SYSTEM"
                    badge_color = "slate"
                    title = m_type
                    snippet = ""
                    command = ""
                    tool_summary = ""
                    tool_name = ""

                    if source == "USER_EXPLICIT" or m_type == "USER_INPUT":
                        category = "USER"
                        badge_color = "emerald"
                        title = "User Request"
                        user_c += 1
                        if content:
                            m = re.search(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', content, re.DOTALL)
                            if m:
                                snippet = m.group(1).strip()
                            else:
                                snippet = content.strip()
                    elif source == "MODEL" or m_type == "PLANNER_RESPONSE":
                        if tool_calls:
                            tc0 = tool_calls[0]
                            tool_name = tc0.get("name", "")
                            args = tc0.get("args", {})
                            category = "TOOL"
                            badge_color = "purple"
                            title = f"Tool: {tool_name}"
                            tool_c += 1
                            if "toolSummary" in args:
                                tool_summary = args["toolSummary"]
                                title = tool_summary
                            if "CommandLine" in args:
                                command = args["CommandLine"]
                            elif "AbsolutePath" in args:
                                command = args["AbsolutePath"]
                            elif "Prompt" in args:
                                command = args["Prompt"]
                            elif "TargetFile" in args:
                                command = args["TargetFile"]
                        else:
                            category = "ASSISTANT"
                            badge_color = "blue"
                            title = "Assistant Response"
                            assistant_c += 1
                            snippet = content if content else ""
                    elif m_type == "GENERIC":
                        category = "OUTPUT"
                        badge_color = "amber"
                        title = "Execution Output"
                        output_c += 1
                        snippet = content.strip() if content else ""
                    elif m_type == "SYSTEM_MESSAGE":
                        category = "SYSTEM"
                        badge_color = "slate"
                        title = "System Event"
                        system_c += 1
                        snippet = content.strip() if content else ""
                    else:
                        system_c += 1

                    # Formatted time
                    time_str = ""
                    if created:
                        try:
                            time_str = created.replace("T", " ").replace("Z", "")[:19]
                        except:
                            time_str = created

                    steps.append({
                        "step_index": s_idx,
                        "line_index": line_idx,
                        "source": source,
                        "type": m_type,
                        "category": category,
                        "badge_color": badge_color,
                        "title": title,
                        "tool_name": tool_name,
                        "tool_summary": tool_summary,
                        "command": command[:250] if command else "",
                        "snippet": (snippet[:180] + "...") if len(snippet) > 180 else snippet,
                        "has_thinking": bool(thinking),
                        "timestamp": time_str
                    })
                except:
                    pass

        # Compute Density Histogram (60 bins across steps)
        total_steps = len(steps)
        density_bins = []
        num_bins = 60
        if total_steps > 0:
            bin_size = max(1.0, total_steps / float(num_bins))
            for b in range(num_bins):
                start_i = int(b * bin_size)
                end_i = min(total_steps, int((b + 1) * bin_size))
                if start_i >= total_steps:
                    break
                bin_slice = steps[start_i:end_i]
                u = sum(1 for x in bin_slice if x["category"] == "USER")
                a = sum(1 for x in bin_slice if x["category"] == "ASSISTANT")
                t = sum(1 for x in bin_slice if x["category"] == "TOOL")
                o = sum(1 for x in bin_slice if x["category"] == "OUTPUT")
                s = sum(1 for x in bin_slice if x["category"] == "SYSTEM")
                density_bins.append({
                    "bin_index": b,
                    "start_step": bin_slice[0]["step_index"] if bin_slice else start_i,
                    "end_step": bin_slice[-1]["step_index"] if bin_slice else end_i,
                    "user": u,
                    "assistant": a,
                    "tool": t,
                    "output": o,
                    "system": s,
                    "total": len(bin_slice)
                })

        return {
            "steps": steps,
            "stats": {
                "total": total_steps,
                "user": user_c,
                "assistant": assistant_c,
                "tool": tool_c,
                "output": output_c,
                "system": system_c
            },
            "density": density_bins
        }

    def perform_rollback(self, conv_id, target_step_index, make_backup=True):
        try:
            target_step_index = int(target_step_index)
            brain_path = os.path.join(self.base_path, "brain", conv_id)
            logs_path = os.path.join(brain_path, ".system_generated", "logs")
            conv_db = os.path.join(self.base_path, "conversations", f"{conv_id}.db")

            if make_backup:
                self.create_backup(conv_id)

            # 1. Truncate transcripts
            t_path = os.path.join(logs_path, "transcript.jsonl")
            tf_path = os.path.join(logs_path, "transcript_full.jsonl")

            if os.path.exists(t_path):
                with open(t_path, "r", encoding="utf-8") as f:
                    t_lines = f.readlines()
                kept_t = []
                for line in t_lines:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        if "step_index" in obj:
                            if obj["step_index"] <= target_step_index:
                                kept_t.append(line)
                            else:
                                break
                        else:
                            kept_t.append(line)
                    except:
                        kept_t.append(line)
                with open(t_path, "w", encoding="utf-8") as f:
                    f.writelines(kept_t)

            if os.path.exists(tf_path):
                with open(tf_path, "r", encoding="utf-8") as f:
                    tf_lines = f.readlines()
                kept_tf = []
                for line in tf_lines:
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                        if "step_index" in obj:
                            if obj["step_index"] <= target_step_index:
                                kept_tf.append(line)
                            else:
                                break
                        else:
                            kept_tf.append(line)
                    except:
                        kept_tf.append(line)
                with open(tf_path, "w", encoding="utf-8") as f:
                    f.writelines(kept_tf)

            # 2. Re-slice chunks
            c_t = os.path.join(logs_path, "chunks", "transcript")
            c_tf = os.path.join(logs_path, "chunks", "transcript_full")
            if os.path.exists(c_t):
                self._rechunk(t_path, c_t)
            if os.path.exists(c_tf):
                self._rechunk(tf_path, c_tf)

            # 3. Update SQLite DB (atomic steps, gen_metadata, executor_metadata, wal_checkpoint)
            if os.path.exists(conv_db):
                conn = sqlite3.connect(conv_db)
                cur = conn.cursor()
                try:
                    cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except:
                    pass

                cur.execute(f"DELETE FROM steps WHERE idx > {target_step_index};")

                # Prune gen_metadata associated with rolled-back steps
                try:
                    cur.execute("SELECT idx, data FROM gen_metadata;")
                    g_rows = cur.fetchall()
                    for g_idx, g_data in g_rows:
                        if len(g_data) > 2 and g_data[0] == 0x12:
                            length = g_data[1]
                            g_steps = []
                            off = 2
                            while off < 2 + length and off < len(g_data):
                                s_val = 0
                                shift = 0
                                while off < len(g_data):
                                    b = g_data[off]
                                    off += 1
                                    s_val |= (b & 0x7f) << shift
                                    shift += 7
                                    if not (b & 0x80):
                                        break
                                g_steps.append(s_val)
                            if g_steps and all(s > target_step_index for s in g_steps):
                                cur.execute(f"DELETE FROM gen_metadata WHERE idx = {g_idx};")
                except:
                    pass

                # Update executor_metadata (Field 2: gen_count, Field 3: target_step_index)
                try:
                    cur.execute("SELECT COUNT(*) FROM gen_metadata;")
                    new_gen_cnt = cur.fetchone()[0]
                    cur.execute("SELECT data FROM executor_metadata;")
                    em_row = cur.fetchone()
                    if em_row and em_row[0]:
                        orig_em = em_row[0]
                        def dec_v(buf, offset):
                            r = 0
                            s = 0
                            while offset < len(buf):
                                b = buf[offset]
                                offset += 1
                                r |= (b & 0x7f) << s
                                s += 7
                                if not (b & 0x80):
                                    break
                            return r, offset

                        def enc_v(v):
                            out = bytearray()
                            while v > 0x7f:
                                out.append((v & 0x7f) | 0x80)
                                v >>= 7
                            out.append(v & 0x7f)
                            return out

                        off = 0
                        t1, off = dec_v(orig_em, off)
                        v1, off = dec_v(orig_em, off)
                        t2, off = dec_v(orig_em, off)
                        v2, off = dec_v(orig_em, off)
                        t3, off = dec_v(orig_em, off)
                        v3, off = dec_v(orig_em, off)
                        rest_em = orig_em[off:]

                        new_em = bytearray()
                        new_em.extend(enc_v(t1))
                        new_em.extend(enc_v(v1))
                        new_em.extend(enc_v(t2))
                        new_em.extend(enc_v(new_gen_cnt))
                        new_em.extend(enc_v(t3))
                        new_em.extend(enc_v(target_step_index))
                        new_em.extend(rest_em)

                        cur.execute("UPDATE executor_metadata SET data = ? WHERE idx = 0;", (bytes(new_em),))
                except:
                    pass

                conn.commit()
                try:
                    cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except:
                    pass
                cur.execute("VACUUM;")
                conn.commit()
                conn.close()

                # Clean any lingering WAL / SHM files if present
                for suffix in ["-wal", "-shm"]:
                    extra_f = conv_db.replace(".db", f".db{suffix}")
                    if os.path.exists(extra_f):
                        try:
                            os.remove(extra_f)
                        except:
                            pass

            # 4. Clean step directories
            steps_dir = os.path.join(brain_path, ".system_generated", "steps")
            if os.path.exists(steps_dir):
                for sd in os.listdir(steps_dir):
                    if sd.isdigit() and int(sd) > target_step_index:
                        shutil.rmtree(os.path.join(steps_dir, sd), ignore_errors=True)

            # 5. Clean task logs
            tasks_dir = os.path.join(brain_path, ".system_generated", "tasks")
            if os.path.exists(tasks_dir):
                for lf in os.listdir(tasks_dir):
                    if lf.startswith("task-") and lf.endswith(".log"):
                        num_part = lf.replace("task-", "").replace(".log", "")
                        if num_part.isdigit() and int(num_part) > target_step_index:
                            try:
                                os.remove(os.path.join(tasks_dir, lf))
                            except:
                                pass

            # 6. Clean messages
            msg_dir = os.path.join(brain_path, ".system_generated", "messages")
            if os.path.exists(msg_dir):
                read_json = os.path.join(msg_dir, "read.json")
                read_map = {}
                if os.path.exists(read_json):
                    try:
                        read_map = json.load(open(read_json, "r", encoding="utf-8"))
                    except:
                        pass
                changed = False
                for mf in os.listdir(msg_dir):
                    if mf.endswith(".json") and mf != "read.json":
                        p = os.path.join(msg_dir, mf)
                        try:
                            m_obj = json.load(open(p, "r", encoding="utf-8"))
                            s_idx = m_obj.get("sourceMetadata", {}).get("tool", {}).get("stepIndex")
                            if s_idx and int(s_idx) > target_step_index:
                                os.remove(p)
                                mid = mf.replace(".json", "")
                                if mid in read_map:
                                    del read_map[mid]
                                    changed = True
                        except:
                            pass
                if changed:
                    try:
                        json.dump(read_map, open(read_json, "w", encoding="utf-8"))
                    except:
                        pass

            return {"success": True, "target_step": target_step_index}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_backup(self, conv_id):
        brain_path = os.path.join(self.base_path, "brain", conv_id)
        conv_db = os.path.join(self.base_path, "conversations", f"{conv_id}.db")
        logs_path = os.path.join(brain_path, ".system_generated", "logs")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_dir = os.path.join(brain_path, "backups", f"backup_{timestamp}")
        os.makedirs(dest_dir, exist_ok=True)

        if os.path.exists(conv_db):
            shutil.copy2(conv_db, os.path.join(dest_dir, f"{conv_id}.db"))

        t_path = os.path.join(logs_path, "transcript.jsonl")
        tf_path = os.path.join(logs_path, "transcript_full.jsonl")
        if os.path.exists(t_path):
            shutil.copy2(t_path, os.path.join(dest_dir, "transcript.jsonl"))
        if os.path.exists(tf_path):
            shutil.copy2(tf_path, os.path.join(dest_dir, "transcript_full.jsonl"))

        chunks_dir = os.path.join(logs_path, "chunks")
        if os.path.exists(chunks_dir):
            shutil.copytree(chunks_dir, os.path.join(dest_dir, "chunks"), dirs_exist_ok=True)

        return dest_dir

    def list_backups(self, conv_id):
        backups = []
        brain_path = os.path.join(self.base_path, "brain", conv_id)
        b_base = os.path.join(brain_path, "backups")
        conv_dir = os.path.join(self.base_path, "conversations")
        annot_dir = os.path.join(self.base_path, "annotations")

        # Resolve thread title
        thread_title = self.resolve_conversation_title(conv_id)

        # Live DB state to check is_active
        live_db = os.path.join(conv_dir, f"{conv_id}.db")
        live_max = None
        live_cnt = 0
        if os.path.exists(live_db):
            try:
                conn = sqlite3.connect(live_db)
                c = conn.cursor()
                c.execute("SELECT MAX(idx), COUNT(*) FROM steps;")
                live_max, live_cnt = c.fetchone()
                conn.close()
            except:
                pass

        def parse_snapshot_dir(p, default_name):
            mtime = os.path.getmtime(p)
            size = sum(os.path.getsize(os.path.join(root, f)) for root, dirs, files in os.walk(p) for f in files)
            b_db = os.path.join(p, f"{conv_id}.db")
            b_max = None
            b_cnt = 0
            if os.path.exists(b_db):
                try:
                    conn = sqlite3.connect(b_db)
                    c = conn.cursor()
                    c.execute("SELECT MAX(idx), COUNT(*) FROM steps;")
                    b_max, b_cnt = c.fetchone()
                    conn.close()
                except:
                    pass

            snippet = ""
            t_file = os.path.join(p, "transcript.jsonl")
            if os.path.exists(t_file):
                try:
                    with open(t_file, "r", encoding="utf-8") as f:
                        lines = [l.strip() for l in f if l.strip()]
                        for l in reversed(lines):
                            try:
                                obj = json.loads(l)
                                cnt = obj.get("content", "")
                                if cnt and len(cnt.strip()) > 3:
                                    snippet = re.sub(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', r'\1', cnt, flags=re.DOTALL).strip()
                                    break
                            except:
                                pass
                except:
                    pass

            is_active = (b_max is not None and live_max is not None and b_max == live_max and b_cnt == live_cnt)

            return {
                "name": default_name,
                "path": p.replace("\\", "/"),
                "timestamp": mtime,
                "date_formatted": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "relative_time": self.format_relative_time(mtime),
                "size_formatted": self.format_bytes(size),
                "thread_title": thread_title,
                "step_count": b_cnt,
                "last_step_index": b_max if b_max is not None else 0,
                "preview_snippet": (snippet[:120] + "...") if len(snippet) > 120 else snippet,
                "is_active": is_active
            }

        if os.path.exists(b_base):
            for d in os.listdir(b_base):
                p = os.path.join(b_base, d)
                if os.path.isdir(p):
                    backups.append(parse_snapshot_dir(p, d))

        before_del = os.path.join(brain_path, "backup_before_delete")
        if os.path.exists(before_del):
            backups.append(parse_snapshot_dir(before_del, "backup_before_delete (Initial Snapshot)"))

        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups

    def restore_backup(self, conv_id, backup_identifier):
        try:
            brain_path = os.path.join(self.base_path, "brain", conv_id)
            conv_db = os.path.join(self.base_path, "conversations", f"{conv_id}.db")
            logs_path = os.path.join(brain_path, ".system_generated", "logs")

            # Resolve backup folder path safely
            backup_folder_path = None
            clean_id = (backup_identifier or "").strip().replace("/", "\\")
            
            candidates = [
                clean_id,
                os.path.join(brain_path, "backups", clean_id),
                os.path.join(brain_path, clean_id),
                os.path.join(brain_path, "backups", os.path.basename(clean_id)),
                os.path.join(brain_path, os.path.basename(clean_id))
            ]
            for c in candidates:
                if c and os.path.isdir(c):
                    backup_folder_path = c
                    break

            if not backup_folder_path or not os.path.exists(backup_folder_path):
                return {"success": False, "error": f"Backup directory '{backup_identifier}' not found"}

            backup_db = os.path.join(backup_folder_path, f"{conv_id}.db")
            b_t = os.path.join(backup_folder_path, "transcript.jsonl")
            b_tf = os.path.join(backup_folder_path, "transcript_full.jsonl")

            if not os.path.exists(backup_db) and not os.path.exists(b_t):
                return {"success": False, "error": f"No database or transcript files in {backup_folder_path}"}

            # 1. Restore db
            if os.path.exists(backup_db):
                shutil.copy2(backup_db, conv_db)

            # 2. Restore transcripts
            if os.path.exists(b_t):
                shutil.copy2(b_t, os.path.join(logs_path, "transcript.jsonl"))
            if os.path.exists(b_tf):
                shutil.copy2(b_tf, os.path.join(logs_path, "transcript_full.jsonl"))

            # 3. Restore chunks
            b_chunks = os.path.join(backup_folder_path, "chunks")
            target_chunks = os.path.join(logs_path, "chunks")
            if os.path.exists(b_chunks):
                if os.path.exists(target_chunks):
                    shutil.rmtree(target_chunks, ignore_errors=True)
                shutil.copytree(b_chunks, target_chunks)

            # 4. Clean lingering WAL / SHM files and vacuum restored db
            for suffix in ["-wal", "-shm"]:
                extra_f = conv_db.replace(".db", f".db{suffix}")
                if os.path.exists(extra_f):
                    try:
                        os.remove(extra_f)
                    except:
                        pass

            if os.path.exists(conv_db):
                conn = sqlite3.connect(conv_db)
                try:
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
                except:
                    pass
                conn.execute("VACUUM;")
                conn.close()

            return {"success": True, "restored_path": backup_folder_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_step_detail(self, conv_id, step_index):
        try:
            step_index = int(step_index)
            brain_path = os.path.join(self.base_path, "brain", conv_id)
            logs_path = os.path.join(brain_path, ".system_generated", "logs")
            tf_path = os.path.join(logs_path, "transcript_full.jsonl")
            t_path = os.path.join(logs_path, "transcript.jsonl")

            target_path = tf_path if os.path.exists(tf_path) else t_path
            if not os.path.exists(target_path):
                return {"error": "Transcript file not found"}

            found_obj = None
            with open(target_path, "r", encoding="utf-8") as f:
                for line_idx, line in enumerate(f):
                    line_s = line.strip()
                    if not line_s:
                        continue
                    try:
                        obj = json.loads(line_s)
                        if obj.get("step_index") == step_index:
                            found_obj = obj
                            break
                    except:
                        pass

            if not found_obj:
                return {"error": f"Step {step_index} not found in transcript"}

            content = found_obj.get("content", "")
            clean_user_request = ""
            if content:
                m = re.search(r'<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>', content, re.DOTALL)
                if m:
                    clean_user_request = m.group(1).strip()

            return {
                "step_index": found_obj.get("step_index", step_index),
                "source": found_obj.get("source", ""),
                "type": found_obj.get("type", ""),
                "status": found_obj.get("status", ""),
                "created_at": found_obj.get("created_at", ""),
                "content": content,
                "clean_user_request": clean_user_request,
                "thinking": found_obj.get("thinking", ""),
                "tool_calls": found_obj.get("tool_calls", []),
                "media": found_obj.get("media", []),
                "raw_json": json.dumps(found_obj, indent=2, ensure_ascii=False)
            }
        except Exception as e:
            return {"error": str(e)}

    def create_manual_snapshot(self, conv_id, label="snapshot"):
        try:
            clean_label = re.sub(r'[^a-zA-Z0-9_\-]', '_', (label or "snapshot").strip())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            brain_path = os.path.join(self.base_path, "brain", conv_id)
            conv_db = os.path.join(self.base_path, "conversations", f"{conv_id}.db")
            logs_path = os.path.join(brain_path, ".system_generated", "logs")

            dest_dir = os.path.join(brain_path, "backups", f"snapshot_{timestamp}_{clean_label}")
            os.makedirs(dest_dir, exist_ok=True)

            if os.path.exists(conv_db):
                shutil.copy2(conv_db, os.path.join(dest_dir, f"{conv_id}.db"))

            t_path = os.path.join(logs_path, "transcript.jsonl")
            tf_path = os.path.join(logs_path, "transcript_full.jsonl")
            if os.path.exists(t_path):
                shutil.copy2(t_path, os.path.join(dest_dir, "transcript.jsonl"))
            if os.path.exists(tf_path):
                shutil.copy2(tf_path, os.path.join(dest_dir, "transcript_full.jsonl"))

            chunks_dir = os.path.join(logs_path, "chunks")
            if os.path.exists(chunks_dir):
                shutil.copytree(chunks_dir, os.path.join(dest_dir, "chunks"), dirs_exist_ok=True)

            return {"success": True, "path": dest_dir, "name": os.path.basename(dest_dir)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_backup(self, conv_id, backup_identifier):
        try:
            brain_path = os.path.abspath(os.path.join(self.base_path, "brain", conv_id))
            clean_id = (backup_identifier or "").strip().replace("/", "\\")
            candidates = [
                clean_id,
                os.path.join(brain_path, "backups", clean_id),
                os.path.join(brain_path, clean_id),
                os.path.join(brain_path, "backups", os.path.basename(clean_id)),
                os.path.join(brain_path, os.path.basename(clean_id))
            ]
            target_path = None
            for c in candidates:
                if c and os.path.exists(c):
                    target_path = os.path.abspath(c)
                    break

            if not target_path or not target_path.startswith(brain_path):
                return {"success": False, "error": "Unauthorized or not found backup directory"}
            if os.path.exists(target_path):
                shutil.rmtree(target_path, ignore_errors=True)
                return {"success": True}
            return {"success": False, "error": "Backup path not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _rechunk(self, file_path, chunk_dir, chunk_size=102400):
        if not os.path.exists(file_path) or not os.path.exists(chunk_dir):
            return
        data = open(file_path, "rb").read()
        total = len(data)
        num_chunks = (total + chunk_size - 1) // chunk_size

        for cf in os.listdir(chunk_dir):
            if cf.endswith(".jsonl"):
                fn = cf.replace(".jsonl", "")
                if fn.isdigit() and int(fn) >= num_chunks:
                    try:
                        os.remove(os.path.join(chunk_dir, cf))
                    except:
                        pass

        for i in range(num_chunks):
            c_file = os.path.join(chunk_dir, f"{i:08d}.jsonl")
            offset = i * chunk_size
            length = min(chunk_size, total - offset)
            with open(c_file, "wb") as f:
                f.write(data[offset:offset+length])

    @staticmethod
    def format_bytes(bytes_count):
        suffixes = ["B", "KB", "MB", "GB"]
        d = float(bytes_count)
        i = 0
        while d >= 1024 and i < len(suffixes) - 1:
            d /= 1024
            i += 1
        return f"{d:.1f} {suffixes[i]}"
    
    def open_antigravity_folder(self):
        try:
            if sys.platform == "win32":
                os.startfile(self.base_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.base_path])
            else:
                subprocess.Popen(["xdg-open", self.base_path])
            return {"success": True, "path": self.base_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart_antigravity(self):
        try:
            candidates = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe"),
                r"C:\Users\PC\AppData\Local\Programs\antigravity\Antigravity.exe",
                os.path.expandvars(r"%PROGRAMFILES%\Antigravity\Antigravity.exe")
            ]
            exe_path = next((p for p in candidates if os.path.exists(p)), None)

            # Terminate running Antigravity processes
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/IM", "Antigravity.exe"], capture_output=True)
            else:
                subprocess.run(["pkill", "-f", "Antigravity"], capture_output=True)

            import time
            time.sleep(1.2)

            if exe_path and os.path.exists(exe_path):
                if sys.platform == "win32":
                    os.startfile(exe_path)
                else:
                    subprocess.Popen([exe_path], start_new_session=True)
                return {"success": True, "restarted": True, "path": exe_path}
            else:
                return {"success": True, "restarted": False, "message": "Antigravity terminated. Please launch it from desktop."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def export_conversation_markdown(self, conv_id, include_thinking=True, include_tools=True):
        """
        Exports an Antigravity conversation session as clean, formatted Markdown.
        Supports granular filters:
          - include_thinking (bool): Whether to include model thinking blocks
          - include_tools (bool): Whether to include tool calls, parameters & execution outputs
        """
        try:
            brain_path = os.path.join(self.base_path, "brain", conv_id)
            logs_path = os.path.join(brain_path, ".system_generated", "logs")
            tf_path = os.path.join(logs_path, "transcript_full.jsonl")
            t_path = os.path.join(logs_path, "transcript.jsonl")
            target_path = tf_path if os.path.exists(tf_path) else t_path

            if not os.path.exists(target_path):
                return {
                    "success": False,
                    "error": f"Transcript not found for conversation {conv_id}"
                }

            # Retrieve conversation title
            title = self.resolve_conversation_title(conv_id)

            # Safe filename slug
            clean_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
            if not clean_title:
                clean_title = "session"
            filename = f"{clean_title}_{conv_id[:8]}.md"

            md = []
            md.append(f"# {title}\n")
            md.append(f"**Session ID:** `{conv_id}`  ")
            md.append(f"**Exported:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  ")
            md.append(f"**Include Thinking:** `{'Yes' if include_thinking else 'No'}`  ")
            md.append(f"**Include Tools & Calling:** `{'Yes' if include_tools else 'No'}`  ")
            md.append("\n---\n")

            assistant_buffer = {
                "thinking": [],
                "tools": [],
                "content": []
            }
            pending_tools = []
            user_turns_count = 0
            asst_turns_count = 0
            thinking_blocks_count = 0
            tool_calls_count = 0

            def flush_assistant_turn():
                nonlocal assistant_buffer, asst_turns_count, thinking_blocks_count, tool_calls_count
                has_thinking = bool(assistant_buffer["thinking"]) and include_thinking
                has_tools = bool(assistant_buffer["tools"]) and include_tools
                has_content = bool(assistant_buffer["content"])

                if not (has_thinking or has_tools or has_content):
                    assistant_buffer = {"thinking": [], "tools": [], "content": []}
                    return

                asst_turns_count += 1
                md.append("## Assistant\n")

                if has_thinking:
                    for think_text in assistant_buffer["thinking"]:
                        thinking_blocks_count += 1
                        md.append(f"_Thinking:_\n\n{think_text}\n")

                if has_tools:
                    for tool in assistant_buffer["tools"]:
                        tool_calls_count += 1
                        tname = tool.get("name") or "tool"
                        args = tool.get("args") or {}
                        output = tool.get("output", "")

                        md.append(f"**Tool: `{tname}`**\n")
                        if args:
                            try:
                                args_str = json.dumps(args, indent=2, ensure_ascii=False)
                            except Exception:
                                args_str = str(args)
                            md.append(f"**Input:**\n```json\n{args_str}\n```\n")

                        if output:
                            md.append(f"**Output:**\n```\n{output}\n```\n")

                if has_content:
                    for c in assistant_buffer["content"]:
                        md.append(f"{c}\n")

                md.append("---\n")
                assistant_buffer = {"thinking": [], "tools": [], "content": []}

            with open(target_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except Exception:
                        continue

                    source = obj.get("source")
                    m_type = obj.get("type")
                    content = obj.get("content", "")
                    thinking = obj.get("thinking", "")
                    tool_calls = obj.get("tool_calls", [])

                    if source == "USER_EXPLICIT" or m_type == "USER_INPUT":
                        flush_assistant_turn()
                        user_turns_count += 1
                        req_text = content
                        m = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", content, re.DOTALL)
                        if m:
                            req_text = m.group(1).strip()
                        md.append(f"## User\n\n{req_text}\n\n---\n")

                    elif m_type == "PLANNER_RESPONSE":
                        if thinking and thinking.strip():
                            assistant_buffer["thinking"].append(thinking.strip())

                        if tool_calls:
                            for tc in tool_calls:
                                t_item = {
                                    "name": tc.get("name"),
                                    "args": tc.get("args", {})
                                }
                                pending_tools.append(t_item)
                                assistant_buffer["tools"].append(t_item)

                        if content and content.strip():
                            assistant_buffer["content"].append(content.strip())

                    elif m_type == "GENERIC":
                        if pending_tools:
                            last_tool = pending_tools.pop(0)
                            last_tool["output"] = content.strip()

            flush_assistant_turn()
            final_markdown = "\n".join(md)

            return {
                "success": True,
                "conv_id": conv_id,
                "title": title,
                "filename": filename,
                "markdown": final_markdown,
                "stats": {
                    "user_turns": user_turns_count,
                    "assistant_turns": asst_turns_count,
                    "thinking_blocks": thinking_blocks_count,
                    "tool_calls": tool_calls_count,
                    "characters": len(final_markdown),
                    "lines": len(final_markdown.splitlines())
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_session(self, conv_id, query, case_sensitive=False, limit=200):
        if not query or not query.strip():
            return {
                "success": True,
                "query": "",
                "total_matches": 0,
                "turns_count": 0,
                "matches": []
            }

        brain_path = os.path.join(self.base_path, "brain", conv_id)
        logs_path = os.path.join(brain_path, ".system_generated", "logs")
        tf_path = os.path.join(logs_path, "transcript_full.jsonl")
        t_path = os.path.join(logs_path, "transcript.jsonl")
        target_path = tf_path if os.path.exists(tf_path) else t_path

        if not os.path.exists(target_path):
            return {
                "success": False,
                "error": f"Transcript not found for conversation {conv_id}",
                "matches": []
            }

        flags = 0 if case_sensitive else re.IGNORECASE
        escaped = re.escape(query.strip())
        pattern = re.compile(f"({escaped})", flags)

        matches = []
        total_matches = 0

        try:
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                for line_idx, line in enumerate(f):
                    if not line.strip():
                        continue
                    try:
                        step = json.loads(line)
                    except Exception:
                        continue

                    step_idx = step.get("step_index", line_idx)
                    tp = step.get("type", "")
                    src = step.get("source", "")
                    role = "assistant"
                    if tp == "USER_INPUT" or src == "USER_EXPLICIT":
                        role = "user"
                    elif tp in ["GENERIC", "TOOL"]:
                        role = "tool"

                    cnt = step.get("content") or ""
                    thinking = step.get("thinking") or ""
                    tool_calls = step.get("tool_calls") or []

                    tc_text = ""
                    if tool_calls:
                        tc_text = " ".join([f"{t.get('name', '')} {json.dumps(t.get('args', {}))}" for t in tool_calls])

                    combined_text = f"{cnt} {thinking} {tc_text}"
                    found = list(pattern.finditer(combined_text))
                    if found:
                        count = len(found)
                        total_matches += count
                        m0 = found[0]
                        start = max(0, m0.start() - 40)
                        end = min(len(combined_text), m0.end() + 60)
                        snippet = combined_text[start:end].replace("\n", " ").strip()
                        if start > 0:
                            snippet = "..." + snippet
                        if end < len(combined_text):
                            snippet = snippet + "..."

                        if len(matches) < limit:
                            matches.append({
                                "step_index": step_idx,
                                "role": role,
                                "type": tp,
                                "match_count": count,
                                "snippet": snippet
                            })
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "total_matches": total_matches,
                "matches": matches
            }

        return {
            "success": True,
            "conv_id": conv_id,
            "query": query,
            "total_matches": total_matches,
            "turns_count": len(matches),
            "matches": matches
        }


    
    def open_antigravity_folder(self):
        try:
            if sys.platform == "win32":
                os.startfile(self.base_path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.base_path])
            else:
                subprocess.Popen(["xdg-open", self.base_path])
            return {"success": True, "path": self.base_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart_antigravity(self):
        try:
            candidates = [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\antigravity\Antigravity.exe"),
                r"C:\Users\PC\AppData\Local\Programs\antigravity\Antigravity.exe",
                os.path.expandvars(r"%PROGRAMFILES%\Antigravity\Antigravity.exe")
            ]
            exe_path = next((p for p in candidates if os.path.exists(p)), None)

            # Terminate running Antigravity processes
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/IM", "Antigravity.exe"], capture_output=True)
            else:
                subprocess.run(["pkill", "-f", "Antigravity"], capture_output=True)

            import time
            time.sleep(1.2)

            if exe_path and os.path.exists(exe_path):
                if sys.platform == "win32":
                    os.startfile(exe_path)
                else:
                    subprocess.Popen([exe_path], start_new_session=True)
                return {"success": True, "restarted": True, "path": exe_path}
            else:
                return {"success": True, "restarted": False, "message": "Antigravity terminated. Please launch it from desktop."}
        except Exception as e:
            return {"success": False, "error": str(e)}
