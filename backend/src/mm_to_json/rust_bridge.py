"""Zero-copy CPython C-API bridge to the Rust `mm_core_rs` acceleration library."""

from __future__ import annotations

import ctypes
import datetime
import logging
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RUST_LIB: ctypes.PyDLL | None = None
_RUST_INIT_ATTEMPTED: bool = False


def _get_lib_filename() -> str:
    """Return platform-specific shared library filename for `mm_core_rs`."""
    sys_name = platform.system().lower()
    if sys_name == "darwin":
        return "libmm_core_rs.dylib"
    if sys_name == "windows":
        return "mm_core_rs.dll"
    return "libmm_core_rs.so"


def _find_or_build_rust_lib() -> Path | None:
    """Locate or build the compiled `mm_core_rs` dynamic library.

    Returns:
        Path to the compiled shared library if available, or None.
    """
    lib_name = _get_lib_filename()
    # backend/src/mm_to_json/rust_bridge.py -> backend/
    import sys

    src_dir = Path(__file__).resolve().parents[1]
    backend_dir = Path(__file__).resolve().parents[2]
    repo_crate_dir = backend_dir / "rust" / "mm_core_rs"
    pkg_crate_dir = src_dir / "jackcess_rs" / "_rust" / "mm_core_rs"
    candidates = [
        repo_crate_dir / "target" / "release" / lib_name,
        pkg_crate_dir / "target" / "release" / lib_name,
        Path(__file__).resolve().parent / "lib" / lib_name,
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "mm_to_json" / "lib" / lib_name)
    env_override = os.environ.get("MM_CORE_RS_LIB")
    if env_override:
        candidates.insert(0, Path(env_override))

    for cand in candidates:
        if cand.is_file():
            return cand

    # Attempt a release build if Cargo.toml exists in repo, packaged wheel, or uv git cache
    crate_dirs = [repo_crate_dir, pkg_crate_dir]
    uv_cache_root = Path(os.environ.get("UV_CACHE_DIR", str(Path.home() / ".cache" / "uv"))) / "git-v0" / "checkouts"
    if uv_cache_root.is_dir():
        uv_crates = sorted(
            uv_cache_root.glob("*/*/backend/rust/mm_core_rs"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0.0,
            reverse=True,
        )
        crate_dirs.extend(uv_crates)

    for crate_dir in crate_dirs:
        if (crate_dir / "Cargo.toml").is_file():
            built = crate_dir / "target" / "release" / lib_name
            if built.is_file():
                return built
            for build_cmd in (
                ["cargo", "build", "--release", "--offline"],
                ["cargo", "build", "--release"],
            ):
                try:
                    subprocess.run(
                        build_cmd,
                        cwd=str(crate_dir),
                        check=True,
                        capture_output=True,
                        timeout=120,
                    )
                    if built.is_file():
                        return built
                except Exception as exc:
                    logger.debug("Could not auto-build mm_core_rs (%s): %s", build_cmd, exc)

    return None


def is_rust_engine_enabled() -> bool:
    """Return True if the Rust engine is enabled via environment configuration.

    Supports `MM_ENGINE=rust|python|java` and `MM_DISABLE_RUST=1|true|yes`.
    Defaults to True (Rust engine enabled).
    """
    if os.environ.get("MM_DISABLE_RUST", "").strip().lower() in ("1", "true", "yes"):
        return False
    engine = os.environ.get("MM_ENGINE", "rust").strip().lower()
    return engine not in ("python", "java", "py", "0", "false", "no", "off")


def _fn_addr(name: str) -> int:
    """Return the raw C address of a symbol in `ctypes.pythonapi`."""
    fn = getattr(ctypes.pythonapi, name)
    addr = ctypes.cast(fn, ctypes.c_void_p).value
    if not addr:
        raise RuntimeError(f"Missing CPython C-API symbol: {name}")
    return int(addr)


def get_rust_lib() -> ctypes.PyDLL | None:
    """Load and initialize the `mm_core_rs` shared library once per process.

    Returns:
        Initialized `ctypes.PyDLL` instance, or None if disabled or unavailable.
    """
    global _RUST_LIB, _RUST_INIT_ATTEMPTED
    if not is_rust_engine_enabled():
        return None
    if _RUST_INIT_ATTEMPTED:
        return _RUST_LIB
    _RUST_INIT_ATTEMPTED = True

    lib_path = _find_or_build_rust_lib()
    if lib_path is None:
        return None

    try:
        lib = ctypes.PyDLL(str(lib_path))
        ptrs_list = [
            id(dict),
            id(list),
            id(tuple),
            id(str),
            id(int),
            id(float),
            id(bool),
            id(None),
            id(True),
            id(False),
            _fn_addr("PyDict_Next"),
            _fn_addr("PyDict_New"),
            _fn_addr("PyDict_SetItem"),
            _fn_addr("PyList_Size"),
            _fn_addr("PyList_GetItem"),
            _fn_addr("PyList_New"),
            _fn_addr("PyList_SetItem"),
            _fn_addr("PyTuple_Size"),
            _fn_addr("PyTuple_GetItem"),
            _fn_addr("PyUnicode_AsUTF8AndSize"),
            _fn_addr("PyUnicode_FromStringAndSize"),
            _fn_addr("PyLong_AsLongLong"),
            _fn_addr("PyLong_FromLongLong"),
            _fn_addr("PyFloat_AsDouble"),
            _fn_addr("PyFloat_FromDouble"),
            _fn_addr("PyObject_Str"),
            _fn_addr("Py_IncRef"),
            _fn_addr("Py_DecRef"),
            _fn_addr("PyErr_Clear"),
        ]
        arr_type = ctypes.c_size_t * len(ptrs_list)
        ptrs_arr = arr_type(*ptrs_list)
        lib.mm_py_init.argtypes = [ctypes.POINTER(ctypes.c_size_t), ctypes.c_size_t]
        lib.mm_py_init.restype = None
        lib.mm_py_init(ptrs_arr, len(ptrs_list))

        lib.mm_py_validate_meet.argtypes = [ctypes.py_object]
        lib.mm_py_validate_meet.restype = ctypes.py_object

        lib.mm_py_convert_meet.argtypes = [ctypes.py_object, ctypes.c_bool]
        lib.mm_py_convert_meet.restype = ctypes.py_object

        lib.mm_py_load_mdb_bundle.argtypes = [ctypes.c_char_p]
        lib.mm_py_load_mdb_bundle.restype = ctypes.py_object

        lib.mm_py_export_mdb_full_schema.argtypes = [ctypes.c_char_p]
        lib.mm_py_export_mdb_full_schema.restype = ctypes.py_object

        lib.mm_py_jackcess_exec.argtypes = [ctypes.py_object]
        lib.mm_py_jackcess_exec.restype = ctypes.py_object

        lib.weasy_rs_render_pdf_buf.argtypes = [
            ctypes.c_char_p,
            ctypes.c_size_t,
            ctypes.c_char_p,
            ctypes.c_size_t,
            ctypes.POINTER(ctypes.c_size_t),
            ctypes.POINTER(ctypes.c_size_t),
        ]
        lib.weasy_rs_render_pdf_buf.restype = ctypes.c_void_p

        lib.weasy_rs_free_buf.argtypes = [
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.c_size_t,
        ]
        lib.weasy_rs_free_buf.restype = None

        lib.weasy_rs_render_pdf_to_file.argtypes = [
            ctypes.c_char_p,
            ctypes.c_size_t,
            ctypes.c_char_p,
            ctypes.c_size_t,
            ctypes.c_char_p,
            ctypes.c_size_t,
        ]
        lib.weasy_rs_render_pdf_to_file.restype = ctypes.c_int

        _RUST_LIB = lib
        return _RUST_LIB
    except Exception as exc:
        logger.warning("Failed to initialize mm_core_rs library: %s", exc)
        return None


def is_jet4_mdb_file(mdb_path: str | os.PathLike[str] | None) -> bool:
    """Check whether `mdb_path` is a real Jet 3.0/4.0 or ACE `.mdb`/`.accdb` binary file on disk.

    Args:
        mdb_path: Path to the candidate `.mdb` file.

    Returns:
        True if the file starts with the Jet or ACE signature header.
    """
    if not mdb_path:
        return False
    try:
        with open(mdb_path, "rb") as f:
            header = f.read(24)
        return len(header) >= 24 and header[:19] in (
            b"\x00\x01\x00\x00Standard Jet DB",
            b"\x00\x01\x00\x00Standard ACE DB",
        )
    except OSError:
        return False


def rust_load_mdb_bundle(mdb_path: str) -> dict[str, Any] | None:
    """Parse a Jet 4.0 `.mdb` file natively in Rust and return normalized tables + converted meet JSON.

    Args:
        mdb_path: Path to the `.mdb` file.

    Returns:
        Bundle dictionary with `schema_type`, `tables`, `date_columns`, and `converted`,
        or None if the Rust library is unavailable or encounters an error.
    """
    lib = get_rust_lib()
    if lib is None or not is_jet4_mdb_file(mdb_path):
        return None

    try:
        path_bytes = os.fsdecode(mdb_path).encode("utf-8")
        bundle: Any = lib.mm_py_load_mdb_bundle(path_bytes)
        if not isinstance(bundle, dict) or "error" in bundle:
            return None

        # Convert ISO datetime strings back to datetime.datetime for date_columns
        date_columns: dict[str, list[str]] = bundle.get("date_columns", {})
        tables: dict[str, list[dict[str, Any]]] = bundle.get("tables", {})
        for logical_name, dcols in date_columns.items():
            if not dcols:
                continue
            rows = tables.get(logical_name)
            if not rows:
                continue
            for row in rows:
                for col in dcols:
                    val = row.get(col)
                    if isinstance(val, str) and val:
                        try:
                            row[col] = datetime.datetime.fromisoformat(val)
                        except ValueError:
                            pass
        return bundle
    except Exception as exc:
        logger.debug("rust_load_mdb_bundle fallback triggered: %s", exc)
        return None


def rust_export_mdb_full_schema(mdb_path: str) -> dict[str, Any] | None:
    """Export all user tables, columns, indexes, and rows from a Jet 4.0 `.mdb` file via Rust.

    Args:
        mdb_path: Path to the `.mdb` file.

    Returns:
        Schema dictionary matching `MmToJsonConverter.export_full_schema()`, or None on fallback.
    """
    lib = get_rust_lib()
    if lib is None or not is_jet4_mdb_file(mdb_path):
        return None

    try:
        path_bytes = os.fsdecode(mdb_path).encode("utf-8")
        result: Any = lib.mm_py_export_mdb_full_schema(path_bytes)
        if not isinstance(result, dict) or "error" in result or "tables" not in result:
            return None

        for t_def in result["tables"].values():
            date_cols = [col["name"] for col in t_def.get("columns", []) if col.get("type") == "SHORT_DATE_TIME"]
            if date_cols:
                for row in t_def.get("rows", []):
                    for cname in date_cols:
                        val = row.get(cname)
                        if isinstance(val, str) and val:
                            try:
                                row[cname] = datetime.datetime.fromisoformat(val)
                            except ValueError:
                                pass
        return result
    except Exception as exc:
        logger.debug("rust_export_mdb_full_schema fallback triggered: %s", exc)
        return None


def rust_convert_meet(table_data: dict[str, Any], from_mdb: bool = False) -> dict[str, Any] | None:
    """Convert raw Meet Manager tables into hierarchical session/event/entry structure in Rust.

    Args:
        table_data: Dictionary of table rows.
        from_mdb: True if tables came from an MDB (keeps first duplicate case column).

    Returns:
        Hierarchical meet dictionary, or None if unavailable.
    """
    lib = get_rust_lib()
    if lib is None or not isinstance(table_data, dict):
        return None

    try:
        res: Any = lib.mm_py_convert_meet(table_data, bool(from_mdb))
        if isinstance(res, dict) and "sessions" in res:
            return res
        return None
    except Exception as exc:
        logger.debug("rust_convert_meet fallback triggered: %s", exc)
        return None


def rust_validate_meet(cache: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Run all TVSL and Meet Manager validation rules in Rust.

    Args:
        cache: Dictionary mapping table names to lists of row dictionaries.

    Returns:
        List of finding dictionaries (`severity`, `category`, `message`, `affected_id`),
        or None if unavailable.
    """
    lib = get_rust_lib()
    if lib is None or not isinstance(cache, dict):
        return None

    try:
        res: Any = lib.mm_py_validate_meet(cache)
        if isinstance(res, list):
            return res
        return None
    except Exception as exc:
        logger.debug("rust_validate_meet fallback triggered: %s", exc)
        return None


def rust_jackcess_exec(req: dict[str, Any]) -> dict[str, Any] | None:
    """Execute a Jackcess database read/write operation natively in Rust.

    Args:
        req: Operation request dictionary containing `op` and parameters.

    Returns:
        Response dictionary with `ok: bool`, or None if the Rust library is unavailable.
    """
    lib = get_rust_lib()
    if lib is None or not isinstance(req, dict):
        return None

    try:
        res: Any = lib.mm_py_jackcess_exec(req)
        if isinstance(res, dict):
            return res
        return None
    except Exception as exc:
        logger.debug("rust_jackcess_exec error: %s", exc)
        return None


def is_rust_pdf_enabled() -> bool:
    """Return True if the Rust `weasy-rs` PDF rendering engine is enabled.

    Supports `MM_PDF_ENGINE=rust|weasyprint`, `MM_ENGINE=rust|python`, and
    `MM_DISABLE_RUST=1|true|yes`. Defaults to True (`rust`).
    """
    if not is_rust_engine_enabled():
        return False
    pdf_engine = os.environ.get("MM_PDF_ENGINE", "rust").strip().lower()
    return pdf_engine not in ("weasyprint", "python", "py", "0", "false", "no", "off")


def rust_render_pdf_to_file(
    html_content: str,
    output_path: str | os.PathLike[str],
    base_url: str | os.PathLike[str] | None = None,
) -> bool:
    """Render HTML + CSS Paged Media directly to a PDF file using native Rust `weasy-rs`.

    Args:
        html_content: Rendered HTML document string.
        output_path: Destination PDF file path.
        base_url: Optional base directory for resolving assets.

    Returns:
        True if the PDF was written by the Rust engine, or False to trigger fallback.
    """
    if not is_rust_pdf_enabled():
        return False
    lib = get_rust_lib()
    if lib is None:
        return False

    try:
        html_bytes = html_content.encode("utf-8")
        base_bytes = os.fsdecode(base_url).encode("utf-8") if base_url else b""
        out_bytes = os.fsdecode(output_path).encode("utf-8")
        rc: int = lib.weasy_rs_render_pdf_to_file(
            html_bytes,
            len(html_bytes),
            base_bytes if base_bytes else None,
            len(base_bytes),
            out_bytes,
            len(out_bytes),
        )
        return rc == 0
    except Exception as exc:
        logger.debug("rust_render_pdf_to_file fallback triggered: %s", exc)
        return False


def rust_render_pdf_bytes(
    html_content: str,
    base_url: str | os.PathLike[str] | None = None,
) -> bytes | None:
    """Render HTML + CSS Paged Media directly to PDF bytes using native Rust `weasy-rs`.

    Args:
        html_content: Rendered HTML document string.
        base_url: Optional base directory for resolving assets.

    Returns:
        PDF bytes if rendered by Rust, or None to trigger fallback.
    """
    if not is_rust_pdf_enabled():
        return None
    lib = get_rust_lib()
    if lib is None:
        return None

    try:
        html_bytes = html_content.encode("utf-8")
        base_bytes = os.fsdecode(base_url).encode("utf-8") if base_url else b""
        out_len = ctypes.c_size_t(0)
        out_cap = ctypes.c_size_t(0)
        ptr = lib.weasy_rs_render_pdf_buf(
            html_bytes,
            len(html_bytes),
            base_bytes if base_bytes else None,
            len(base_bytes),
            ctypes.byref(out_len),
            ctypes.byref(out_cap),
        )
        if not ptr:
            return None
        try:
            return ctypes.string_at(ptr, out_len.value)
        finally:
            lib.weasy_rs_free_buf(ptr, out_len.value, out_cap.value)
    except Exception as exc:
        logger.debug("rust_render_pdf_bytes fallback triggered: %s", exc)
        return None
