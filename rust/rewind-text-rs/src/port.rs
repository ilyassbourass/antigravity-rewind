//! The Rust port of `rewind_text.py`.
//!
//! The Python value-semantics layer (truthiness, `len()`, int operands, indexing) lives in
//! `wire.rs` alongside the generated conversion scaffolding; this file holds the ported
//! functions themselves. Regex-shaped logic uses the `regex` crate, per the gate's advice.

#![forbid(unsafe_code)]
use crate::wire::{as_int, py_index, py_len, truthy, type_name};
use regex::Regex;
use serde_json::{Value, json};

fn re(pattern: &str) -> Result<Regex, String> {
    Regex::new(pattern).map_err(|e| format!("RuntimeError: {e}"))
}

/// Port of `clean_title_text` (`rewind_text.py:9`).
pub fn clean_title_text(text: Value, max_len: i64) -> Result<Value, String> {
    if !truthy(&text) {
        return Ok(json!(""));
    }
    let s = match &text {
        Value::String(s) => s.clone(),
        other => {
            return Err(format!(
                "TypeError: expected string or bytes-like object, got '{}'",
                type_name(other)
            ));
        }
    };
    // text = re.sub(r'<[^>]+>', ' ', text)
    let text = re(r"<[^>]+>")?.replace_all(&s, " ").into_owned();
    // text = re.sub(prefix words + \s+, '', text, flags=re.I) — regex is leftmost-first, like Python
    let text = re(r"(?i)^(The following is a|You are the|You are an?|Please|Can you|Could you|I want you to|I want u to)\s+")?
        .replace(&text, "")
        .into_owned();
    // lines = [l.strip() for l in text.split('\n') if l.strip()]
    let first_line = match text.split('\n').map(str::trim).find(|l| !l.is_empty()) {
        Some(l) => l.to_string(),
        None => return Ok(json!("")),
    };
    // first_line = re.sub(r'^[#*_\->`\s]+', '', first_line); first_line = re.sub(r'[#*_\->`]+', '', first_line)
    let first_line = re(r"^[#*_\\>`\s-]+")?.replace(&first_line, "").into_owned();
    let first_line = re(r"[#*_\\>`-]+")?
        .replace_all(&first_line, "")
        .into_owned();
    // first_line = first_line.strip('"\' ')
    let first_line = first_line
        .trim_matches(|c| c == '"' || c == '\'' || c == ' ')
        .to_string();
    // len()/slicing in code points, like Python str: s[:n] keeps all but the last |n| when n < 0
    let chars: Vec<char> = first_line.chars().collect();
    let keep = if max_len >= 0 {
        max_len as usize
    } else {
        chars.len().saturating_sub((-max_len) as usize)
    };
    let truncated = if (chars.len() as i64) > max_len {
        Some(chars.into_iter().take(keep).collect::<String>())
    } else {
        None
    };
    let mut first_line = match truncated {
        Some(t) => match t.rfind(' ') {
            Some(ls) if ls > 20 => format!("{}...", t.chars().take(ls).collect::<String>()),
            _ => format!("{t}..."),
        },
        None => first_line,
    };
    // first_line = first_line[0].upper() + first_line[1:]
    if let Some(c0) = first_line.chars().next() {
        first_line = c0.to_uppercase().collect::<String>() + &first_line[c0.len_utf8()..];
    }
    Ok(json!(first_line))
}

/// Port of `format_bytes` (`rewind_text.py:33`).
pub fn format_bytes(bytes_count: f64) -> Result<Value, String> {
    let suffixes = ["B", "KB", "MB", "GB"];
    let mut d = bytes_count;
    let mut i = 0usize;
    while d >= 1024.0 && i < suffixes.len() - 1 {
        d /= 1024.0;
        i += 1;
    }
    // f"{d:.1f}" — Python spells it 'nan'/'inf'/'-inf', Rust says 'NaN'
    let body = if d.is_nan() {
        "nan".to_string()
    } else if d.is_infinite() {
        if d > 0.0 { "inf" } else { "-inf" }.to_string()
    } else {
        format!("{d:.1}")
    };
    Ok(json!(format!("{body} {}", suffixes[i])))
}

/// Port of `decode_varint` (`rewind_text.py:43`) — backend.py `dec_v`, verbatim semantics.
pub fn decode_varint(buf: Value, offset: Value) -> Result<Value, String> {
    let len = py_len(&buf)?;
    let offset_is_bool = offset.is_boolean();
    let off0: i128 = match &offset {
        Value::Bool(_) | Value::Number(_) => match as_int(&offset) {
            Some(i) => i,
            // float: `0.5 < len` compares fine in Python, then buf[0.5] raises or misses
            None => {
                if offset.as_f64().unwrap_or(f64::NAN) >= len as f64 {
                    return Ok(json!({"$tuple": [0, offset]}));
                }
                return match &buf {
                    Value::Object(_) => Err(format!("KeyError: {offset}")),
                    _ => Err("TypeError: index is not an integer".into()),
                };
            }
        },
        other => {
            return Err(format!(
                "TypeError: '<' not supported between instances of '{}' and 'int'",
                type_name(other)
            ));
        }
    };
    let mut r: i128 = 0;
    let mut s: i32 = 0;
    let (mut off, mut cur) = (off0, off0);
    while cur < len {
        let item = py_index(&buf, cur, &offset, offset_is_bool)?;
        let b = match as_int(&item) {
            Some(b) => b,
            None => {
                return Err(format!(
                    "TypeError: unsupported operand type(s) for &: '{}' and 'int'",
                    type_name(&item)
                ));
            }
        };
        r |= (b & 0x7f) << s.min(121); // clamp guards i128; the recordings stay far below
        s += 7;
        off = cur + 1;
        cur += 1;
        if b & 0x80 == 0 {
            break;
        }
    }
    let r_val = i64::try_from(r)
        .map(Value::from)
        .unwrap_or_else(|_| json!({"$int": r.to_string()}));
    // bool offsets the loop never touched stay bool (True + 0 is still True in Python)
    let off_val = if offset_is_bool && off == off0 {
        offset.clone()
    } else {
        json!(off)
    };
    Ok(json!({"$tuple": [r_val, off_val]}))
}

/// Port of `encode_varint` (`rewind_text.py:57`) — backend.py `enc_v`, verbatim semantics.
pub fn encode_varint(v: Value) -> Result<Value, String> {
    let mut val: i128 = match &v {
        Value::Bool(_) | Value::Number(_) => match as_int(&v) {
            Some(i) => i,
            None => {
                return Err(
                    "TypeError: unsupported operand type(s) for &: 'float' and 'int'".into(),
                );
            }
        },
        other => {
            return Err(format!(
                "TypeError: unsupported operand type(s) for &: '{}' and 'int'",
                type_name(other)
            ));
        }
    };
    let mut out: Vec<u8> = Vec::new();
    while val > 0x7f {
        out.push(((val & 0x7f) | 0x80) as u8);
        val >>= 7;
    }
    // Python's `&` on a negative int is two's complement with infinite sign bits
    out.push((val & 0x7f) as u8);
    Ok(json!({"$bytes": out}))
}
