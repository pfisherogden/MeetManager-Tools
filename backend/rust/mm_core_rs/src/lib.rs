pub mod converter;
pub mod empty_mdb;
pub mod jackcess;
pub mod mdb;
pub mod py_bridge;
pub mod validator;

use serde_json::{Map, Value};
use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_void};

fn c_str_to_str<'a>(input_ptr: *const c_char) -> Result<&'a str, String> {
    if input_ptr.is_null() {
        return Err("Null input pointer".to_string());
    }
    let c_str = unsafe { CStr::from_ptr(input_ptr) };
    c_str.to_str().map_err(|e| format!("Invalid UTF-8: {}", e))
}

fn json_str_to_map(input_ptr: *const c_char) -> Result<Map<String, Value>, String> {
    let s = c_str_to_str(input_ptr)?;
    let val: Value = serde_json::from_str(s).map_err(|e| format!("Invalid JSON: {}", e))?;
    match val {
        Value::Object(m) => Ok(m),
        _ => Err("Expected JSON object at root".to_string()),
    }
}

fn string_to_c_char(s: String) -> *mut c_char {
    match CString::new(s) {
        Ok(c) => c.into_raw(),
        Err(_) => CString::new("{}").unwrap().into_raw(),
    }
}

#[no_mangle]
pub extern "C" fn mm_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            let _ = CString::from_raw(ptr);
        }
    }
}

#[no_mangle]
pub extern "C" fn mm_py_init(ptrs: *const usize, count: usize) {
    unsafe {
        py_bridge::init_py_api(ptrs, count);
    }
}

#[no_mangle]
pub extern "C" fn mm_py_validate_meet(dict_obj: *mut c_void) -> *mut c_void {
    unsafe {
        let val = py_bridge::py_obj_to_value(dict_obj, 0);
        let findings = match val {
            Value::Object(map) => validator::validate_meet_data_rs(&map),
            _ => Vec::new(),
        };
        py_bridge::findings_to_py_list(&findings)
    }
}

#[no_mangle]
pub extern "C" fn mm_py_convert_meet(dict_obj: *mut c_void, from_mdb: bool) -> *mut c_void {
    unsafe {
        let val = py_bridge::py_obj_to_value(dict_obj, 0);
        let res = match val {
            Value::Object(map) => converter::convert_meet_data_rs(&map, from_mdb),
            _ => Value::Object(Map::new()),
        };
        py_bridge::value_to_py_obj(&res)
    }
}

#[no_mangle]
pub extern "C" fn mm_py_load_mdb_bundle(mdb_path_ptr: *const c_char) -> *mut c_void {
    unsafe {
        match c_str_to_str(mdb_path_ptr).and_then(mdb::load_mdb_meet_bundle) {
            Ok(val) => py_bridge::value_to_py_obj(&val),
            Err(err) => {
                let err_val = serde_json::json!({ "error": err });
                py_bridge::value_to_py_obj(&err_val)
            }
        }
    }
}

#[no_mangle]
pub extern "C" fn mm_py_export_mdb_full_schema(mdb_path_ptr: *const c_char) -> *mut c_void {
    unsafe {
        match c_str_to_str(mdb_path_ptr).and_then(mdb::export_full_schema_from_file) {
            Ok(val) => py_bridge::value_to_py_obj(&val),
            Err(err) => {
                let err_val = serde_json::json!({ "error": err });
                py_bridge::value_to_py_obj(&err_val)
            }
        }
    }
}

#[no_mangle]
pub extern "C" fn mm_py_jackcess_exec(req_obj: *mut c_void) -> *mut c_void {
    unsafe {
        let req = py_bridge::py_obj_to_value_full(req_obj, 0);
        let res = jackcess::execute_jackcess_op(&req);
        py_bridge::value_to_py_obj(&res)
    }
}

#[no_mangle]
pub extern "C" fn mm_validate_meet_json(input_ptr: *const c_char) -> *mut c_char {
    match json_str_to_map(input_ptr) {
        Ok(map) => {
            let findings = validator::validate_meet_data_rs(&map);
            let out = serde_json::to_string(&findings).unwrap_or_else(|_| "[]".to_string());
            string_to_c_char(out)
        }
        Err(_) => string_to_c_char("[]".to_string()),
    }
}

#[no_mangle]
pub extern "C" fn mm_convert_meet_json(input_ptr: *const c_char, from_mdb: bool) -> *mut c_char {
    match json_str_to_map(input_ptr) {
        Ok(map) => {
            let res = converter::convert_meet_data_rs(&map, from_mdb);
            let out = serde_json::to_string(&res).unwrap_or_else(|_| "{}".to_string());
            string_to_c_char(out)
        }
        Err(_) => string_to_c_char("{}".to_string()),
    }
}

#[no_mangle]
pub extern "C" fn mm_export_mdb_full_schema_json(mdb_path_ptr: *const c_char) -> *mut c_char {
    match c_str_to_str(mdb_path_ptr).and_then(mdb::export_full_schema_from_file) {
        Ok(val) => {
            let out = serde_json::to_string(&val).unwrap_or_else(|_| "{}".to_string());
            string_to_c_char(out)
        }
        Err(err) => {
            let out = serde_json::to_string(&serde_json::json!({ "error": err }))
                .unwrap_or_else(|_| "{}".to_string());
            string_to_c_char(out)
        }
    }
}
