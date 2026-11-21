"""Pure logic extracted verbatim from backend.py (RewindBackend methods -> module functions).

Bodies are copied character-for-character from backend.py so rust-anything records
the original behavior of the real app.
"""
import re


def clean_title_text(text, max_len=45):
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


def format_bytes(bytes_count):
    suffixes = ["B", "KB", "MB", "GB"]
    d = float(bytes_count)
    i = 0
    while d >= 1024 and i < len(suffixes) - 1:
        d /= 1024
        i += 1
    return f"{d:.1f} {suffixes[i]}"


def decode_varint(buf, offset):
    """backend.py dec_v, verbatim."""
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


def encode_varint(v):
    """backend.py enc_v, verbatim."""
    out = bytearray()
    while v > 0x7f:
        out.append((v & 0x7f) | 0x80)
        v >>= 7
    out.append(v & 0x7f)
    return out
