#![allow(non_snake_case)]

use crate::validator::FindingDto;
use serde_json::{Map, Number, Value};
use std::os::raw::{c_char, c_double, c_int, c_longlong, c_void};
use std::slice;
use std::sync::atomic::{AtomicUsize, Ordering};

#[repr(C)]
struct PyObjectHeader {
    ob_refcnt: isize,
    ob_type: usize,
}

type FnPyDictNext = unsafe extern "C" fn(
    mp: *mut c_void,
    ppos: *mut isize,
    pkey: *mut *mut c_void,
    pvalue: *mut *mut c_void,
) -> c_int;
type FnPyDictNew = unsafe extern "C" fn() -> *mut c_void;
type FnPyDictSetItem =
    unsafe extern "C" fn(mp: *mut c_void, key: *mut c_void, item: *mut c_void) -> c_int;
type FnPyListSize = unsafe extern "C" fn(list: *mut c_void) -> isize;
type FnPyListGetItem = unsafe extern "C" fn(list: *mut c_void, index: isize) -> *mut c_void;
type FnPyListNew = unsafe extern "C" fn(size: isize) -> *mut c_void;
type FnPyListSetItem =
    unsafe extern "C" fn(list: *mut c_void, index: isize, item: *mut c_void) -> c_int;
type FnPyTupleSize = unsafe extern "C" fn(tuple: *mut c_void) -> isize;
type FnPyTupleGetItem = unsafe extern "C" fn(tuple: *mut c_void, index: isize) -> *mut c_void;
type FnPyUnicodeAsUTF8AndSize =
    unsafe extern "C" fn(unicode: *mut c_void, size: *mut isize) -> *const c_char;
type FnPyUnicodeFromStringAndSize =
    unsafe extern "C" fn(u: *const c_char, size: isize) -> *mut c_void;
type FnPyLongAsLongLong = unsafe extern "C" fn(v: *mut c_void) -> c_longlong;
type FnPyLongFromLongLong = unsafe extern "C" fn(v: c_longlong) -> *mut c_void;
type FnPyFloatAsDouble = unsafe extern "C" fn(v: *mut c_void) -> c_double;
type FnPyFloatFromDouble = unsafe extern "C" fn(v: c_double) -> *mut c_void;
type FnPyObjectStr = unsafe extern "C" fn(v: *mut c_void) -> *mut c_void;
type FnPyIncRef = unsafe extern "C" fn(o: *mut c_void);
type FnPyDecRef = unsafe extern "C" fn(o: *mut c_void);
type FnPyErrClear = unsafe extern "C" fn();

static DICT_TYPE: AtomicUsize = AtomicUsize::new(0);
static LIST_TYPE: AtomicUsize = AtomicUsize::new(0);
static TUPLE_TYPE: AtomicUsize = AtomicUsize::new(0);
static STR_TYPE: AtomicUsize = AtomicUsize::new(0);
static INT_TYPE: AtomicUsize = AtomicUsize::new(0);
static FLOAT_TYPE: AtomicUsize = AtomicUsize::new(0);
static BOOL_TYPE: AtomicUsize = AtomicUsize::new(0);
static NONE_OBJ: AtomicUsize = AtomicUsize::new(0);
static TRUE_OBJ: AtomicUsize = AtomicUsize::new(0);
static FALSE_OBJ: AtomicUsize = AtomicUsize::new(0);

static FN_PY_DICT_NEXT: AtomicUsize = AtomicUsize::new(0);
static FN_PY_DICT_NEW: AtomicUsize = AtomicUsize::new(0);
static FN_PY_DICT_SET_ITEM: AtomicUsize = AtomicUsize::new(0);
static FN_PY_LIST_SIZE: AtomicUsize = AtomicUsize::new(0);
static FN_PY_LIST_GET_ITEM: AtomicUsize = AtomicUsize::new(0);
static FN_PY_LIST_NEW: AtomicUsize = AtomicUsize::new(0);
static FN_PY_LIST_SET_ITEM: AtomicUsize = AtomicUsize::new(0);
static FN_PY_TUPLE_SIZE: AtomicUsize = AtomicUsize::new(0);
static FN_PY_TUPLE_GET_ITEM: AtomicUsize = AtomicUsize::new(0);
static FN_PY_UNICODE_AS_UTF8_AND_SIZE: AtomicUsize = AtomicUsize::new(0);
static FN_PY_UNICODE_FROM_STRING_AND_SIZE: AtomicUsize = AtomicUsize::new(0);
static FN_PY_LONG_AS_LONGLONG: AtomicUsize = AtomicUsize::new(0);
static FN_PY_LONG_FROM_LONGLONG: AtomicUsize = AtomicUsize::new(0);
static FN_PY_FLOAT_AS_DOUBLE: AtomicUsize = AtomicUsize::new(0);
static FN_PY_FLOAT_FROM_DOUBLE: AtomicUsize = AtomicUsize::new(0);
static FN_PY_OBJECT_STR: AtomicUsize = AtomicUsize::new(0);
static FN_PY_INCREF: AtomicUsize = AtomicUsize::new(0);
static FN_PY_DECREF: AtomicUsize = AtomicUsize::new(0);
static FN_PY_ERR_CLEAR: AtomicUsize = AtomicUsize::new(0);

#[inline(always)]
unsafe fn PyDict_Next(
    mp: *mut c_void,
    ppos: *mut isize,
    pkey: *mut *mut c_void,
    pvalue: *mut *mut c_void,
) -> c_int {
    let f: FnPyDictNext = std::mem::transmute(FN_PY_DICT_NEXT.load(Ordering::Relaxed));
    f(mp, ppos, pkey, pvalue)
}

#[inline(always)]
unsafe fn PyDict_New() -> *mut c_void {
    let f: FnPyDictNew = std::mem::transmute(FN_PY_DICT_NEW.load(Ordering::Relaxed));
    f()
}

#[inline(always)]
unsafe fn PyDict_SetItem(mp: *mut c_void, key: *mut c_void, item: *mut c_void) -> c_int {
    let f: FnPyDictSetItem = std::mem::transmute(FN_PY_DICT_SET_ITEM.load(Ordering::Relaxed));
    f(mp, key, item)
}

#[inline(always)]
unsafe fn PyList_Size(list: *mut c_void) -> isize {
    let f: FnPyListSize = std::mem::transmute(FN_PY_LIST_SIZE.load(Ordering::Relaxed));
    f(list)
}

#[inline(always)]
unsafe fn PyList_GetItem(list: *mut c_void, index: isize) -> *mut c_void {
    let f: FnPyListGetItem = std::mem::transmute(FN_PY_LIST_GET_ITEM.load(Ordering::Relaxed));
    f(list, index)
}

#[inline(always)]
unsafe fn PyList_New(size: isize) -> *mut c_void {
    let f: FnPyListNew = std::mem::transmute(FN_PY_LIST_NEW.load(Ordering::Relaxed));
    f(size)
}

#[inline(always)]
unsafe fn PyList_SetItem(list: *mut c_void, index: isize, item: *mut c_void) -> c_int {
    let f: FnPyListSetItem = std::mem::transmute(FN_PY_LIST_SET_ITEM.load(Ordering::Relaxed));
    f(list, index, item)
}

#[inline(always)]
unsafe fn PyTuple_Size(tuple: *mut c_void) -> isize {
    let f: FnPyTupleSize = std::mem::transmute(FN_PY_TUPLE_SIZE.load(Ordering::Relaxed));
    f(tuple)
}

#[inline(always)]
unsafe fn PyTuple_GetItem(tuple: *mut c_void, index: isize) -> *mut c_void {
    let f: FnPyTupleGetItem = std::mem::transmute(FN_PY_TUPLE_GET_ITEM.load(Ordering::Relaxed));
    f(tuple, index)
}

#[inline(always)]
unsafe fn PyUnicode_AsUTF8AndSize(unicode: *mut c_void, size: *mut isize) -> *const c_char {
    let f: FnPyUnicodeAsUTF8AndSize =
        std::mem::transmute(FN_PY_UNICODE_AS_UTF8_AND_SIZE.load(Ordering::Relaxed));
    f(unicode, size)
}

#[inline(always)]
unsafe fn PyUnicode_FromStringAndSize(u: *const c_char, size: isize) -> *mut c_void {
    let f: FnPyUnicodeFromStringAndSize =
        std::mem::transmute(FN_PY_UNICODE_FROM_STRING_AND_SIZE.load(Ordering::Relaxed));
    f(u, size)
}

#[inline(always)]
unsafe fn PyLong_AsLongLong(v: *mut c_void) -> c_longlong {
    let f: FnPyLongAsLongLong =
        std::mem::transmute(FN_PY_LONG_AS_LONGLONG.load(Ordering::Relaxed));
    f(v)
}

#[inline(always)]
unsafe fn PyLong_FromLongLong(v: c_longlong) -> *mut c_void {
    let f: FnPyLongFromLongLong =
        std::mem::transmute(FN_PY_LONG_FROM_LONGLONG.load(Ordering::Relaxed));
    f(v)
}

#[inline(always)]
unsafe fn PyFloat_AsDouble(v: *mut c_void) -> c_double {
    let f: FnPyFloatAsDouble = std::mem::transmute(FN_PY_FLOAT_AS_DOUBLE.load(Ordering::Relaxed));
    f(v)
}

#[inline(always)]
unsafe fn PyFloat_FromDouble(v: c_double) -> *mut c_void {
    let f: FnPyFloatFromDouble =
        std::mem::transmute(FN_PY_FLOAT_FROM_DOUBLE.load(Ordering::Relaxed));
    f(v)
}

#[inline(always)]
unsafe fn PyObject_Str(v: *mut c_void) -> *mut c_void {
    let f: FnPyObjectStr = std::mem::transmute(FN_PY_OBJECT_STR.load(Ordering::Relaxed));
    f(v)
}

#[inline(always)]
unsafe fn Py_IncRef(o: *mut c_void) {
    let f: FnPyIncRef = std::mem::transmute(FN_PY_INCREF.load(Ordering::Relaxed));
    f(o)
}

#[inline(always)]
unsafe fn Py_DecRef(o: *mut c_void) {
    let f: FnPyDecRef = std::mem::transmute(FN_PY_DECREF.load(Ordering::Relaxed));
    f(o)
}

#[inline(always)]
unsafe fn PyErr_Clear() {
    let f: FnPyErrClear = std::mem::transmute(FN_PY_ERR_CLEAR.load(Ordering::Relaxed));
    f()
}

pub unsafe fn init_py_api(ptrs: *const usize, count: usize) {
    if ptrs.is_null() || count < 29 {
        return;
    }
    let s = slice::from_raw_parts(ptrs, count);
    DICT_TYPE.store(s[0], Ordering::SeqCst);
    LIST_TYPE.store(s[1], Ordering::SeqCst);
    TUPLE_TYPE.store(s[2], Ordering::SeqCst);
    STR_TYPE.store(s[3], Ordering::SeqCst);
    INT_TYPE.store(s[4], Ordering::SeqCst);
    FLOAT_TYPE.store(s[5], Ordering::SeqCst);
    BOOL_TYPE.store(s[6], Ordering::SeqCst);
    NONE_OBJ.store(s[7], Ordering::SeqCst);
    TRUE_OBJ.store(s[8], Ordering::SeqCst);
    FALSE_OBJ.store(s[9], Ordering::SeqCst);
    FN_PY_DICT_NEXT.store(s[10], Ordering::SeqCst);
    FN_PY_DICT_NEW.store(s[11], Ordering::SeqCst);
    FN_PY_DICT_SET_ITEM.store(s[12], Ordering::SeqCst);
    FN_PY_LIST_SIZE.store(s[13], Ordering::SeqCst);
    FN_PY_LIST_GET_ITEM.store(s[14], Ordering::SeqCst);
    FN_PY_LIST_NEW.store(s[15], Ordering::SeqCst);
    FN_PY_LIST_SET_ITEM.store(s[16], Ordering::SeqCst);
    FN_PY_TUPLE_SIZE.store(s[17], Ordering::SeqCst);
    FN_PY_TUPLE_GET_ITEM.store(s[18], Ordering::SeqCst);
    FN_PY_UNICODE_AS_UTF8_AND_SIZE.store(s[19], Ordering::SeqCst);
    FN_PY_UNICODE_FROM_STRING_AND_SIZE.store(s[20], Ordering::SeqCst);
    FN_PY_LONG_AS_LONGLONG.store(s[21], Ordering::SeqCst);
    FN_PY_LONG_FROM_LONGLONG.store(s[22], Ordering::SeqCst);
    FN_PY_FLOAT_AS_DOUBLE.store(s[23], Ordering::SeqCst);
    FN_PY_FLOAT_FROM_DOUBLE.store(s[24], Ordering::SeqCst);
    FN_PY_OBJECT_STR.store(s[25], Ordering::SeqCst);
    FN_PY_INCREF.store(s[26], Ordering::SeqCst);
    FN_PY_DECREF.store(s[27], Ordering::SeqCst);
    FN_PY_ERR_CLEAR.store(s[28], Ordering::SeqCst);
}

unsafe fn py_str_to_string(obj: *mut c_void) -> Option<String> {
    let mut size: isize = 0;
    let ptr = PyUnicode_AsUTF8AndSize(obj, &mut size);
    if ptr.is_null() || size < 0 {
        PyErr_Clear();
        return None;
    }
    let bytes = slice::from_raw_parts(ptr as *const u8, size as usize);
    Some(String::from_utf8_lossy(bytes).into_owned())
}

fn is_relevant_table_key(k: &str) -> bool {
    let t = k.trim();
    const TABLES: &[&str] = &[
        "data",
        "meet",
        "meets",
        "session",
        "sessions",
        "sessitem",
        "sessitems",
        "event",
        "events",
        "mtevent",
        "mtevents",
        "divisions",
        "division",
        "team",
        "teams",
        "athlete",
        "athletes",
        "entry",
        "entries",
        "relay",
        "relays",
        "relaynames",
        "relayname",
        "scoring",
        "stdlanes",
    ];
    TABLES.iter().any(|&cand| t.eq_ignore_ascii_case(cand))
}

unsafe fn py_row_dict_to_value(obj: *mut c_void, skip_nulls: bool, depth: usize) -> Value {
    let none_addr = NONE_OBJ.load(Ordering::Relaxed);
    let str_ty = STR_TYPE.load(Ordering::Relaxed);
    let mut map = Map::new();
    let mut pos: isize = 0;
    let mut k_ptr: *mut c_void = std::ptr::null_mut();
    let mut v_ptr: *mut c_void = std::ptr::null_mut();
    while PyDict_Next(obj, &mut pos, &mut k_ptr, &mut v_ptr) != 0 {
        let is_py_none = v_ptr.is_null() || (v_ptr as usize) == none_addr;
        if skip_nulls && is_py_none && map.is_empty() {
            continue;
        }
        if !k_ptr.is_null() {
            let k_hdr = &*(k_ptr as *const PyObjectHeader);
            if k_hdr.ob_type == str_ty {
                if let Some(k_str) = py_str_to_string(k_ptr) {
                    if is_py_none {
                        if !skip_nulls
                            || map.keys().any(|existing| existing.eq_ignore_ascii_case(&k_str))
                        {
                            map.insert(k_str, Value::Null);
                        }
                        continue;
                    }
                    let v_val = py_obj_to_value(v_ptr, depth + 1);
                    if !skip_nulls
                        || !v_val.is_null()
                        || map.keys().any(|existing| existing.eq_ignore_ascii_case(&k_str))
                    {
                        map.insert(k_str, v_val);
                    }
                }
            }
        }
    }
    Value::Object(map)
}

pub unsafe fn py_obj_to_value(obj: *mut c_void, depth: usize) -> Value {
    py_obj_to_value_inner(obj, depth, true)
}

pub unsafe fn py_obj_to_value_full(obj: *mut c_void, depth: usize) -> Value {
    py_obj_to_value_inner(obj, depth, false)
}

unsafe fn py_obj_to_value_inner(obj: *mut c_void, depth: usize, filter_meet_tables: bool) -> Value {
    if obj.is_null() || depth > 16 {
        return Value::Null;
    }
    let addr = obj as usize;
    let none_addr = NONE_OBJ.load(Ordering::Relaxed);
    if addr == none_addr {
        return Value::Null;
    }
    let true_addr = TRUE_OBJ.load(Ordering::Relaxed);
    if addr == true_addr {
        return Value::Bool(true);
    }
    if addr == FALSE_OBJ.load(Ordering::Relaxed) {
        return Value::Bool(false);
    }
    let hdr = &*(obj as *const PyObjectHeader);
    let ty = hdr.ob_type;
    if ty == BOOL_TYPE.load(Ordering::Relaxed) {
        return Value::Bool(addr == true_addr);
    }
    if ty == STR_TYPE.load(Ordering::Relaxed) {
        return match py_str_to_string(obj) {
            Some(s) => Value::String(s),
            None => Value::Null,
        };
    }
    if ty == INT_TYPE.load(Ordering::Relaxed) {
        let v = PyLong_AsLongLong(obj);
        if v == -1 {
            PyErr_Clear();
        }
        return Value::Number(Number::from(v));
    }
    if ty == FLOAT_TYPE.load(Ordering::Relaxed) {
        let f = PyFloat_AsDouble(obj);
        if f == -1.0 {
            PyErr_Clear();
        }
        if f.is_nan() || f.is_infinite() {
            return Value::Null;
        }
        return match Number::from_f64(f) {
            Some(n) => Value::Number(n),
            None => Value::Null,
        };
    }
    let dict_ty = DICT_TYPE.load(Ordering::Relaxed);
    if ty == LIST_TYPE.load(Ordering::Relaxed) {
        let len = PyList_Size(obj);
        if len <= 0 {
            return Value::Array(Vec::new());
        }
        let mut arr = Vec::with_capacity(len as usize);
        for i in 0..len {
            let item = PyList_GetItem(obj, i);
            if filter_meet_tables
                && !item.is_null()
                && (&*(item as *const PyObjectHeader)).ob_type == dict_ty
            {
                arr.push(py_row_dict_to_value(item, i > 0, depth + 1));
            } else {
                arr.push(py_obj_to_value_inner(item, depth + 1, filter_meet_tables));
            }
        }
        return Value::Array(arr);
    }
    if ty == TUPLE_TYPE.load(Ordering::Relaxed) {
        let len = PyTuple_Size(obj);
        if len <= 0 {
            return Value::Array(Vec::new());
        }
        let mut arr = Vec::with_capacity(len as usize);
        for i in 0..len {
            let item = PyTuple_GetItem(obj, i);
            arr.push(py_obj_to_value_inner(item, depth + 1, filter_meet_tables));
        }
        return Value::Array(arr);
    }
    if ty == dict_ty {
        let mut map = Map::new();
        let mut pos: isize = 0;
        let mut k_ptr: *mut c_void = std::ptr::null_mut();
        let mut v_ptr: *mut c_void = std::ptr::null_mut();
        let str_ty = STR_TYPE.load(Ordering::Relaxed);
        while PyDict_Next(obj, &mut pos, &mut k_ptr, &mut v_ptr) != 0 {
            if !k_ptr.is_null() {
                let k_hdr = &*(k_ptr as *const PyObjectHeader);
                if k_hdr.ob_type == str_ty {
                    if let Some(k_str) = py_str_to_string(k_ptr) {
                        if filter_meet_tables && depth <= 1 && !is_relevant_table_key(&k_str) {
                            continue;
                        }
                        let v_val = py_obj_to_value_inner(v_ptr, depth + 1, filter_meet_tables);
                        map.insert(k_str, v_val);
                    }
                }
            }
        }
        return Value::Object(map);
    }
    let s_obj = PyObject_Str(obj);
    if !s_obj.is_null() {
        let res = match py_str_to_string(s_obj) {
            Some(s) if s == "nan" || s == "NaT" || s == "<NA>" || s == "None" => Value::Null,
            Some(s) => Value::String(s),
            None => Value::Null,
        };
        Py_DecRef(s_obj);
        return res;
    }
    PyErr_Clear();
    Value::Null
}

unsafe fn str_to_py(s: &str) -> *mut c_void {
    PyUnicode_FromStringAndSize(s.as_ptr() as *const c_char, s.len() as isize)
}

pub unsafe fn value_to_py_obj(val: &Value) -> *mut c_void {
    match val {
        Value::Null => {
            let p = NONE_OBJ.load(Ordering::Relaxed) as *mut c_void;
            Py_IncRef(p);
            p
        }
        Value::Bool(b) => {
            let p = if *b {
                TRUE_OBJ.load(Ordering::Relaxed)
            } else {
                FALSE_OBJ.load(Ordering::Relaxed)
            } as *mut c_void;
            Py_IncRef(p);
            p
        }
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                PyLong_FromLongLong(i)
            } else if let Some(f) = n.as_f64() {
                PyFloat_FromDouble(f)
            } else {
                let p = NONE_OBJ.load(Ordering::Relaxed) as *mut c_void;
                Py_IncRef(p);
                p
            }
        }
        Value::String(s) => str_to_py(s),
        Value::Array(arr) => {
            let list = PyList_New(arr.len() as isize);
            for (i, item) in arr.iter().enumerate() {
                let py_item = value_to_py_obj(item);
                PyList_SetItem(list, i as isize, py_item);
            }
            list
        }
        Value::Object(map) => {
            let dict = PyDict_New();
            for (k, v) in map.iter() {
                let py_k = str_to_py(k);
                let py_v = value_to_py_obj(v);
                PyDict_SetItem(dict, py_k, py_v);
                Py_DecRef(py_k);
                Py_DecRef(py_v);
            }
            dict
        }
    }
}

pub unsafe fn findings_to_py_list(findings: &[FindingDto]) -> *mut c_void {
    let list = PyList_New(findings.len() as isize);
    let k_sev = str_to_py("severity");
    let k_cat = str_to_py("category");
    let k_msg = str_to_py("message");
    let k_aff = str_to_py("affected_id");

    for (i, f) in findings.iter().enumerate() {
        let dict = PyDict_New();
        let v_sev = PyLong_FromLongLong(f.severity as c_longlong);
        let v_cat = str_to_py(&f.category);
        let v_msg = str_to_py(&f.message);
        let v_aff = str_to_py(&f.affected_id);

        PyDict_SetItem(dict, k_sev, v_sev);
        PyDict_SetItem(dict, k_cat, v_cat);
        PyDict_SetItem(dict, k_msg, v_msg);
        PyDict_SetItem(dict, k_aff, v_aff);

        Py_DecRef(v_sev);
        Py_DecRef(v_cat);
        Py_DecRef(v_msg);
        Py_DecRef(v_aff);

        PyList_SetItem(list, i as isize, dict);
    }

    Py_DecRef(k_sev);
    Py_DecRef(k_cat);
    Py_DecRef(k_msg);
    Py_DecRef(k_aff);
    list
}
