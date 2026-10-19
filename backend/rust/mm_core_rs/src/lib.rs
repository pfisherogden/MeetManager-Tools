pub mod converter;
pub use jackcess_rs::{empty_mdb, jackcess, mdb};
pub mod py_bridge;
pub mod validator;
pub use weasy_rs;
pub use weasy_rs::py_bridge::{
    weasy_rs_free_buf, weasy_rs_render_pdf_buf, weasy_rs_render_pdf_to_file,
};

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

pub fn load_mdb_meet_bundle(mdb_path: &str) -> Result<Value, String> {
    let data = std::fs::read(mdb_path).map_err(|e| format!("Failed to read MDB {}: {}", mdb_path, e))?;
    let ver = mdb::JetVersion::from_data(&data)?;
    let user_tables = mdb::discover_user_tables(&data)?;
    let mut catalog_map: std::collections::HashMap<String, (String, usize)> =
        std::collections::HashMap::with_capacity(user_tables.len());
    for (tname, tpage) in &user_tables {
        catalog_map.insert(tname.to_lowercase(), (tname.clone(), *tpage));
    }

    let aliases: &[(&str, &[&str])] = &[
        ("meet", &["Meet", "MEET"]),
        ("session", &["Session", "SESSIONS"]),
        ("sessitem", &["Sessitem", "SESSITEM"]),
        ("event", &["Event", "MTEVENT"]),
        ("entry", &["Entry", "ENTRY"]),
        ("relay", &["Relay", "RELAY"]),
        ("relaynames", &["RelayNames", "RELAYNAMES"]),
        ("athlete", &["athlete", "ATHLETE", "Athlete"]),
        ("team", &["Team", "TEAM"]),
        ("divisions", &["Divisions", "DIVISIONS"]),
        ("scoring", &["Scoring", "SCORING"]),
        ("stdlanes", &["StdLanes", "STDLANES"]),
    ];

    let mut schema_type = "A";
    let mut lower_tables_map = Map::new();
    let mut raw_input_for_convert = Map::new();
    let mut date_columns_map = Map::new();
    let mut missing_warnings = Vec::new();

    for &(logical, candidates) in aliases {
        let mut found: Option<(String, usize)> = None;
        for &cand in candidates {
            if let Some(entry) = catalog_map.get(&cand.to_lowercase()) {
                found = Some(entry.clone());
                break;
            }
        }
        if let Some((phys_name, tpage)) = found {
            if logical == "event" && phys_name.eq_ignore_ascii_case("MTEVENT") {
                schema_type = "B";
            }
            if let Ok(tdef) = mdb::parse_table_ver(&data, tpage, ver) {
                let mut date_cols = Vec::new();
                for c in &tdef.columns {
                    if c.col_type == 8 {
                        date_cols.push(Value::String(c.name.to_lowercase()));
                    }
                }
                if !date_cols.is_empty() {
                    date_columns_map.insert(logical.to_string(), Value::Array(date_cols));
                }

                let mut lower_rows = Vec::with_capacity(tdef.rows.len());
                for r in tdef.rows {
                    let mut lr = Map::with_capacity(r.len());
                    for (k, v) in r {
                        let lk = k.to_lowercase();
                        if !lr.contains_key(&lk) {
                            lr.insert(lk, v);
                        }
                    }
                    lower_rows.push(Value::Object(lr));
                }
                let arr_val = Value::Array(lower_rows);
                if logical == "event" && schema_type == "B" {
                    raw_input_for_convert.insert("MTEVENT".to_string(), arr_val.clone());
                } else {
                    raw_input_for_convert.insert(logical.to_string(), arr_val.clone());
                }
                lower_tables_map.insert(logical.to_string(), arr_val);
            } else {
                lower_tables_map.insert(logical.to_string(), Value::Array(Vec::new()));
            }
        } else {
            if !matches!(logical, "sessitem" | "relaynames" | "divisions") {
                missing_warnings.push(Value::String(logical.to_string()));
            }
            lower_tables_map.insert(logical.to_string(), Value::Array(Vec::new()));
        }
    }

    let converted = converter::convert_meet_data_rs(&raw_input_for_convert, true);
    Ok(serde_json::json!({
        "schema_type": schema_type,
        "tables": Value::Object(lower_tables_map),
        "date_columns": Value::Object(date_columns_map),
        "missing_warnings": Value::Array(missing_warnings),
        "converted": converted,
    }))
}

#[no_mangle]
pub extern "C" fn mm_py_load_mdb_bundle(mdb_path_ptr: *const c_char) -> *mut c_void {
    unsafe {
        match c_str_to_str(mdb_path_ptr).and_then(load_mdb_meet_bundle) {
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
