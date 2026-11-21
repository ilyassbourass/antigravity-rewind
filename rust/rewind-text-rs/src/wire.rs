//! Python value semantics on the JSON wire (the same layer the generated `pyconv.rs` /
//! `wire.rs` scaffolding covers): truthiness, `len()`, `int` operands (bools count, huge
//! ints arrive as `$int`), and `buf[offset]` indexing for list/str/dict.

#![forbid(unsafe_code)]
use serde_json::{Value, json};

pub fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Number(n) => n.as_f64().map(|f| f != 0.0).unwrap_or(true),
        Value::String(s) => !s.is_empty(),
        Value::Array(a) => !a.is_empty(),
        Value::Object(o) => !o.is_empty(),
    }
}

pub fn type_name(v: &Value) -> &'static str {
    match v {
        Value::Null => "NoneType",
        Value::Bool(_) => "bool",
        Value::Number(n) if n.is_i64() || n.is_u64() => "int",
        Value::Number(_) => "float",
        Value::String(_) => "str",
        Value::Array(_) => "list",
        Value::Object(o) if o.len() == 1 && o.contains_key("$int") => "int",
        Value::Object(_) => "dict",
    }
}

/// Python `len()`; Err is the original's `TypeError: object of type 'X' has no len()`.
pub fn py_len(v: &Value) -> Result<i128, String> {
    match v {
        Value::String(s) => Ok(s.chars().count() as i128),
        Value::Array(a) => Ok(a.len() as i128),
        Value::Object(o) if o.contains_key("$int") => {
            Err("TypeError: object of type 'int' has no len()".into())
        }
        Value::Object(o) => Ok(o.len() as i128),
        other => Err(format!(
            "TypeError: object of type '{}' has no len()",
            type_name(other)
        )),
    }
}

/// An integer operand as Python sees it: bool is an int, huge ints arrive as `$int`.
pub fn as_int(v: &Value) -> Option<i128> {
    match v {
        Value::Bool(b) => Some(*b as i128),
        Value::Number(n) => n
            .as_i64()
            .map(|i| i as i128)
            .or_else(|| n.as_u64().map(|u| u as i128)),
        Value::Object(o) if o.len() == 1 => o
            .get("$int")
            .and_then(|x| x.as_str())
            .and_then(|s| s.parse().ok()),
        _ => None,
    }
}

/// Python `buf[offset]` for list/str/dict: negative indices wrap, wrong types raise.
pub fn py_index(
    buf: &Value,
    cur: i128,
    offset: &Value,
    offset_is_bool: bool,
) -> Result<Value, String> {
    match buf {
        Value::Array(a) => {
            let i = if cur < 0 { a.len() as i128 + cur } else { cur };
            a.get(i as usize)
                .cloned()
                .filter(|_| (0..a.len() as i128).contains(&i))
                .ok_or_else(|| "IndexError: list index out of range".to_string())
        }
        Value::String(st) => {
            let cs: Vec<char> = st.chars().collect();
            let i = if cur < 0 { cs.len() as i128 + cur } else { cur };
            cs.get(i as usize)
                .map(|c| json!(c.to_string()))
                .filter(|_| (0..cs.len() as i128).contains(&i))
                .ok_or_else(|| "IndexError: string index out of range".to_string())
        }
        Value::Object(o) => {
            let key = if offset_is_bool {
                if offset.as_bool().is_some_and(|b| b) {
                    "True"
                } else {
                    "False"
                }
                .to_string()
            } else {
                offset.to_string()
            };
            o.get(&key)
                .cloned()
                .ok_or_else(|| format!("KeyError: {key}"))
        }
        _ => Err("TypeError: not indexable".to_string()),
    }
}
