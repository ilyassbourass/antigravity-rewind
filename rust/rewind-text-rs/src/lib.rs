//! Python bindings for `rewind_text.py`: generated from the signatures in `port.rs` by rust-anything.
//! Regenerate with `rust-anything refresh` after changing them.

use pyo3::prelude::*;

pub mod js;
pub mod port;
pub mod pyconv;
pub mod pynum;
mod wire;

#[allow(unused_imports)]
use pynum::Num;

fn error(message: String) -> PyErr {
    use pyo3::exceptions as e;
    let (kind, text) = message.split_once(": ").unwrap_or(("", message.as_str()));
    let text = text.to_string();
    match kind {
        "TypeError" => e::PyTypeError::new_err(text),
        "KeyError" => e::PyKeyError::new_err(text),
        "IndexError" => e::PyIndexError::new_err(text),
        "OverflowError" => e::PyOverflowError::new_err(text),
        "ZeroDivisionError" => e::PyZeroDivisionError::new_err(text),
        "AttributeError" => e::PyAttributeError::new_err(text),
        "RuntimeError" => e::PyRuntimeError::new_err(text),
        "NotImplementedError" => e::PyNotImplementedError::new_err(text),
        "LookupError" => e::PyLookupError::new_err(text),
        "ArithmeticError" => e::PyArithmeticError::new_err(text),
        "UnicodeError" => e::PyUnicodeError::new_err(text),
        "ValueError" => e::PyValueError::new_err(text),
        _ => e::PyValueError::new_err(message),
    }
}

fn clean_title_text_inner(
    text: Bound<'_, PyAny>,
    max_len: i64,
) -> Result<serde_json::Value, String> {
    let text: serde_json::Value = crate::pyconv::FromPy::from_py(&text)?;
    let out = port::clean_title_text(text, max_len)?;
    Ok(out)
}

/// `clean_title_text`.
#[pyfunction]
#[pyo3(name = "clean_title_text", signature = (text, max_len=45))]
fn clean_title_text(py: Python<'_>, text: Bound<'_, PyAny>, max_len: i64) -> PyResult<Py<PyAny>> {
    clean_title_text_inner(text, max_len)
        .map_err(error)
        .and_then(|v| crate::pyconv::ToPy::to_py(&v, py))
}

fn format_bytes_inner(bytes_count: f64) -> Result<serde_json::Value, String> {
    let out = port::format_bytes(bytes_count)?;
    Ok(out)
}

/// `format_bytes`.
#[pyfunction]
#[pyo3(name = "format_bytes", signature = (bytes_count))]
fn format_bytes(py: Python<'_>, bytes_count: f64) -> PyResult<Py<PyAny>> {
    format_bytes_inner(bytes_count)
        .map_err(error)
        .and_then(|v| crate::pyconv::ToPy::to_py(&v, py))
}

fn decode_varint_inner(
    buf: Bound<'_, PyAny>,
    offset: Bound<'_, PyAny>,
) -> Result<serde_json::Value, String> {
    let buf: serde_json::Value = crate::pyconv::FromPy::from_py(&buf)?;
    let offset: serde_json::Value = crate::pyconv::FromPy::from_py(&offset)?;
    let out = port::decode_varint(buf, offset)?;
    Ok(out)
}

/// `decode_varint`.
#[pyfunction]
#[pyo3(name = "decode_varint", signature = (buf, offset))]
fn decode_varint(
    py: Python<'_>,
    buf: Bound<'_, PyAny>,
    offset: Bound<'_, PyAny>,
) -> PyResult<Py<PyAny>> {
    decode_varint_inner(buf, offset)
        .map_err(error)
        .and_then(|v| crate::pyconv::ToPy::to_py(&v, py))
}

fn encode_varint_inner(v: Bound<'_, PyAny>) -> Result<serde_json::Value, String> {
    let v: serde_json::Value = crate::pyconv::FromPy::from_py(&v)?;
    let out = port::encode_varint(v)?;
    Ok(out)
}

/// `encode_varint`.
#[pyfunction]
#[pyo3(name = "encode_varint", signature = (v))]
fn encode_varint(py: Python<'_>, v: Bound<'_, PyAny>) -> PyResult<Py<PyAny>> {
    encode_varint_inner(v)
        .map_err(error)
        .and_then(|v| crate::pyconv::ToPy::to_py(&v, py))
}

#[pymodule]
#[pyo3(name = "_native")]
fn native_module(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(clean_title_text, m)?)?;
    m.add_function(wrap_pyfunction!(format_bytes, m)?)?;
    m.add_function(wrap_pyfunction!(decode_varint, m)?)?;
    m.add_function(wrap_pyfunction!(encode_varint, m)?)?;
    Ok(())
}
