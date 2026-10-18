use crate::empty_mdb::get_empty_v2000_mdb;
use crate::mdb::{
    discover_tables, find_row_end, name_to_col_type, parse_table_ver, read_u16_le, read_u32_le,
    ColumnDef, IndexDef, JetVersion, TableDef,
};
use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};
use chrono::{NaiveDate, NaiveDateTime};
use serde_json::{Map, Value};
use std::collections::HashMap;
use std::fs;

const PAGE_SIZE: usize = 4096;
const LVAL_MAGIC_TDEF: u32 = 0x4C41_564C; // "LVAL"

fn write_u16_le(buf: &mut [u8], off: usize, val: u16) {
    let b = val.to_le_bytes();
    buf[off] = b[0];
    buf[off + 1] = b[1];
}

fn write_i16_le(buf: &mut [u8], off: usize, val: i16) {
    let b = val.to_le_bytes();
    buf[off] = b[0];
    buf[off + 1] = b[1];
}

fn write_u32_le(buf: &mut [u8], off: usize, val: u32) {
    let b = val.to_le_bytes();
    buf[off..off + 4].copy_from_slice(&b);
}

fn write_i32_le(buf: &mut [u8], off: usize, val: i32) {
    let b = val.to_le_bytes();
    buf[off..off + 4].copy_from_slice(&b);
}

fn write_i64_le(buf: &mut [u8], off: usize, val: i64) {
    let b = val.to_le_bytes();
    buf[off..off + 8].copy_from_slice(&b);
}

fn write_f32_le(buf: &mut [u8], off: usize, val: f32) {
    let b = val.to_le_bytes();
    buf[off..off + 4].copy_from_slice(&b);
}

fn write_f64_le(buf: &mut [u8], off: usize, val: f64) {
    let b = val.to_le_bytes();
    buf[off..off + 8].copy_from_slice(&b);
}

fn encode_utf16le(s: &str) -> Vec<u8> {
    let mut out = Vec::with_capacity(s.len() * 2);
    for u in s.encode_utf16() {
        out.extend_from_slice(&u.to_le_bytes());
    }
    out
}

pub fn encode_jet4_text(s: &str, compressed_unicode: bool) -> Vec<u8> {
    if s.is_empty() {
        return Vec::new();
    }
    let chars: Vec<u16> = s.encode_utf16().collect();
    if compressed_unicode
        && chars.len() >= 2
        && chars.len() <= 1024
        && chars[0] != 0xFEFF
        && chars[0] != 0xFFFE
        && chars.iter().all(|&c| (1..=0xFF).contains(&c))
    {
        let mut out = Vec::with_capacity(2 + chars.len());
        out.push(0xFF);
        out.push(0xFE);
        for c in chars {
            out.push(c as u8);
        }
        out
    } else {
        encode_utf16le(s)
    }
}

pub fn allocate_page(data: &mut Vec<u8>) -> usize {
    if data.len() % PAGE_SIZE != 0 {
        let rem = PAGE_SIZE - (data.len() % PAGE_SIZE);
        data.resize(data.len() + rem, 0);
    }
    let page_num = data.len() / PAGE_SIZE;
    data.resize(data.len() + PAGE_SIZE, 0);
    mark_global_page_allocated(data, page_num);
    page_num
}

fn mark_global_page_allocated(data: &mut Vec<u8>, page_num: usize) {
    // Global usage map is on Page 1, Row 0 (where bit 0 = allocated, bit 1 = free)
    let p1_off = PAGE_SIZE;
    let r0_off = (read_u16_le(data, p1_off + 14) & 0x1FFF) as usize;
    if r0_off + 5 > PAGE_SIZE {
        return;
    }
    let map_type = data[p1_off + r0_off];
    if map_type == 0 {
        let start_page = read_u32_le(data, p1_off + r0_off + 1) as usize;
        let max_inline_pages = (PAGE_SIZE - r0_off - 5) * 8;
        if page_num >= start_page && page_num < start_page + max_inline_pages {
            let rel = page_num - start_page;
            let byte_idx = p1_off + r0_off + 5 + (rel / 8);
            data[byte_idx] &= !(1 << (rel % 8));
        } else {
            // Promote global usage map on Page 1 Row 0 from Inline (0x00) to Reference (0x01)
            let old_bitmap = data[p1_off + r0_off + 5..p1_off + PAGE_SIZE].to_vec();
            data[p1_off + r0_off] = 1;
            for b in &mut data[p1_off + r0_off + 1..p1_off + PAGE_SIZE] {
                *b = 0;
            }
            // Allocate reference usage map page (type 0x05)
            let ref_page = data.len() / PAGE_SIZE;
            data.resize(data.len() + PAGE_SIZE, 0xFF);
            let rp_off = ref_page * PAGE_SIZE;
            data[rp_off] = 0x05;
            data[rp_off + 1] = 0x01;
            data[rp_off + 2] = 0x00;
            data[rp_off + 3] = 0x00;
            // Copy old inline bitmap into the beginning of ref_page
            let copy_len = old_bitmap.len().min(PAGE_SIZE - 4);
            data[rp_off + 4..rp_off + 4 + copy_len].copy_from_slice(&old_bitmap[..copy_len]);
            write_u32_le(data, p1_off + r0_off + 1, ref_page as u32);
            // Clear bits for both page_num and ref_page
            mark_global_page_allocated(data, page_num);
            mark_global_page_allocated(data, ref_page);
        }
    } else if map_type == 1 {
        let pages_per_ref = (PAGE_SIZE - 4) * 8;
        let slot = page_num / pages_per_ref;
        let rem = page_num % pages_per_ref;
        let slot_off = p1_off + r0_off + 1 + slot * 4;
        if slot_off + 4 > p1_off + PAGE_SIZE {
            return;
        }
        let mut rpage = read_u32_le(data, slot_off) as usize;
        if rpage == 0 {
            rpage = data.len() / PAGE_SIZE;
            data.resize(data.len() + PAGE_SIZE, 0xFF);
            let rp_off = rpage * PAGE_SIZE;
            data[rp_off] = 0x05;
            data[rp_off + 1] = 0x01;
            data[rp_off + 2] = 0x00;
            data[rp_off + 3] = 0x00;
            write_u32_le(data, slot_off, rpage as u32);
            mark_global_page_allocated(data, rpage);
        }
        let rp_off = rpage * PAGE_SIZE;
        data[rp_off + 4 + (rem / 8)] &= !(1 << (rem % 8));
    }
}

pub fn set_usage_map_bit(data: &mut Vec<u8>, usage_ptr: u32, target_page: usize, set_bit: bool) {
    let mpage = (usage_ptr >> 8) as usize;
    let mrow = (usage_ptr & 0xFF) as usize;
    if mpage == 0 || (mpage + 1) * PAGE_SIZE > data.len() {
        return;
    }
    let mp_off = mpage * PAGE_SIZE;
    let r_off = (read_u16_le(data, mp_off + 14 + mrow * 2) & 0x1FFF) as usize;
    let r_end = find_row_end(&data[mp_off..mp_off + PAGE_SIZE], mrow, 14, PAGE_SIZE);
    if r_off + 5 > r_end || r_end > PAGE_SIZE {
        return;
    }
    let mtype = data[mp_off + r_off];
    if mtype == 0 {
        let mut start_page = read_u32_le(data, mp_off + r_off + 1) as usize;
        let bitmap_len = r_end - (r_off + 5);
        let max_pages = bitmap_len * 8;
        let all_zero = data[mp_off + r_off + 5..mp_off + r_end]
            .iter()
            .all(|&b| b == 0);
        if all_zero && set_bit {
            start_page = (target_page / 8) * 8;
            write_u32_le(data, mp_off + r_off + 1, start_page as u32);
        }
        if target_page >= start_page && target_page < start_page + max_pages {
            let rel = target_page - start_page;
            let b_idx = mp_off + r_off + 5 + (rel / 8);
            if set_bit {
                data[b_idx] |= 1 << (rel % 8);
            } else {
                data[b_idx] &= !(1 << (rel % 8));
            }
        } else if set_bit {
            // Promote inline usage map row to reference (0x01)
            let existing = crate::mdb::read_usage_map_ver(data, usage_ptr, JetVersion::Jet4);
            data[mp_off + r_off] = 1;
            for b in &mut data[mp_off + r_off + 1..mp_off + r_end] {
                *b = 0;
            }
            for p in existing {
                set_usage_map_bit(data, usage_ptr, p, true);
            }
            set_usage_map_bit(data, usage_ptr, target_page, true);
        }
    } else if mtype == 1 {
        let pages_per_ref = (PAGE_SIZE - 4) * 8;
        let slot = target_page / pages_per_ref;
        let rem = target_page % pages_per_ref;
        let slot_off = mp_off + r_off + 1 + slot * 4;
        if slot_off + 4 > mp_off + r_end {
            return;
        }
        let mut rpage = read_u32_le(data, slot_off) as usize;
        if rpage == 0 {
            if !set_bit {
                return;
            }
            rpage = allocate_page(data);
            let rp_off = rpage * PAGE_SIZE;
            data[rp_off] = 0x05;
            data[rp_off + 1] = 0x01;
            write_u32_le(data, slot_off, rpage as u32);
        }
        let rp_off = rpage * PAGE_SIZE;
        let b_idx = rp_off + 4 + (rem / 8);
        if set_bit {
            data[b_idx] |= 1 << (rem % 8);
        } else {
            data[b_idx] &= !(1 << (rem % 8));
        }
    }
}

fn allocate_new_data_page(data: &mut Vec<u8>, tdef_page: usize, owned_ptr: u32, free_ptr: u32) -> usize {
    let dpage = allocate_page(data);
    let dp_off = dpage * PAGE_SIZE;
    data[dp_off] = 0x01;
    data[dp_off + 1] = 0x01;
    write_u16_le(data, dp_off + 2, 4082); // PAGE_SIZE - 14
    write_u32_le(data, dp_off + 4, tdef_page as u32);
    write_u32_le(data, dp_off + 8, 0);
    write_u16_le(data, dp_off + 12, 0);
    if owned_ptr != 0 {
        set_usage_map_bit(data, owned_ptr, dpage, true);
    }
    if free_ptr != 0 {
        set_usage_map_bit(data, free_ptr, dpage, true);
    }
    dpage
}

fn append_row_to_data_page(data: &mut [u8], dpage: usize, row_bytes: &[u8], mark_deleted: bool) -> usize {
    let dp_off = dpage * PAGE_SIZE;
    let free_space = read_u16_le(data, dp_off + 2) as usize;
    let num_rows = read_u16_le(data, dp_off + 12) as usize;
    let last_row_pos = find_row_end(&data[dp_off..dp_off + PAGE_SIZE], num_rows, 14, PAGE_SIZE);
    let new_row_pos = last_row_pos - row_bytes.len();
    data[dp_off + new_row_pos..dp_off + last_row_pos].copy_from_slice(row_bytes);
    let mut off_entry = new_row_pos as u16;
    if mark_deleted {
        off_entry |= 0x8000;
    }
    write_u16_le(data, dp_off + 14 + num_rows * 2, off_entry);
    let new_free = free_space.saturating_sub(row_bytes.len() + 2);
    write_u16_le(data, dp_off + 2, new_free as u16);
    write_u16_le(data, dp_off + 12, (num_rows + 1) as u16);
    num_rows
}

fn find_or_alloc_data_page_for_row(
    data: &mut Vec<u8>,
    tdef_page: usize,
    owned_ptr: u32,
    free_ptr: u32,
    row_len: usize,
    exclude_page: Option<usize>,
) -> usize {
    let needed = row_len + 2;
    let candidate_pages = crate::mdb::read_usage_map_ver(data, owned_ptr, JetVersion::Jet4);
    for &p in candidate_pages.iter().rev() {
        if Some(p) == exclude_page || (p + 1) * PAGE_SIZE > data.len() {
            continue;
        }
        let dp_off = p * PAGE_SIZE;
        if data[dp_off] != 0x01 || (read_u32_le(data, dp_off + 4) as usize) != tdef_page {
            continue;
        }
        let free_space = read_u16_le(data, dp_off + 2) as usize;
        let num_rows = read_u16_le(data, dp_off + 12) as usize;
        let last_row_pos = find_row_end(&data[dp_off..dp_off + PAGE_SIZE], num_rows, 14, PAGE_SIZE);
        let hdr_end = 14 + (num_rows + 1) * 2;
        if free_space >= needed && last_row_pos >= hdr_end + row_len {
            return p;
        }
    }
    allocate_new_data_page(data, tdef_page, owned_ptr, free_ptr)
}

fn write_lval_bytes(data: &mut Vec<u8>, payload: &[u8]) -> Vec<u8> {
    let len = payload.len();
    if len <= 64 {
        let mut out = Vec::with_capacity(12 + len);
        let hdr = (len as u32) | 0x8000_0000;
        out.extend_from_slice(&hdr.to_le_bytes());
        out.extend_from_slice(&[0u8; 8]);
        out.extend_from_slice(payload);
        return out;
    }
    if len <= 4076 {
        let (pnum, rnum) = write_lval_chunk(data, payload, 0, 0, false);
        let mut out = vec![0u8; 12];
        let hdr = (len as u32) | 0x4000_0000;
        write_u32_le(&mut out, 0, hdr);
        out[4] = rnum as u8;
        let pb = (pnum as u32).to_le_bytes();
        out[5] = pb[0];
        out[6] = pb[1];
        out[7] = pb[2];
        return out;
    }
    // Multi-page LVAL (type 0): write chunks in reverse so each points to next!
    let chunks: Vec<&[u8]> = payload.chunks(4072).collect();
    let mut next_page = 0usize;
    let mut next_row = 0usize;
    for chunk in chunks.into_iter().rev() {
        let (p, r) = write_lval_chunk(data, chunk, next_page, next_row, true);
        next_page = p;
        next_row = r;
    }
    let mut out = vec![0u8; 12];
    let hdr = (len as u32) & 0x3FFF_FFFF;
    write_u32_le(&mut out, 0, hdr);
    out[4] = next_row as u8;
    let pb = (next_page as u32).to_le_bytes();
    out[5] = pb[0];
    out[6] = pb[1];
    out[7] = pb[2];
    out
}

fn write_lval_chunk(
    data: &mut Vec<u8>,
    chunk: &[u8],
    next_page: usize,
    next_row: usize,
    with_chain_prefix: bool,
) -> (usize, usize) {
    let row_len = if with_chain_prefix {
        4 + chunk.len()
    } else {
        chunk.len()
    };
    let mut row_buf = Vec::with_capacity(row_len);
    if with_chain_prefix {
        row_buf.push(next_row as u8);
        let pb = (next_page as u32).to_le_bytes();
        row_buf.push(pb[0]);
        row_buf.push(pb[1]);
        row_buf.push(pb[2]);
    }
    row_buf.extend_from_slice(chunk);

    // Find an existing LVAL page (`tdef == LVAL_MAGIC_TDEF`) with enough space, or allocate one
    let num_pages = data.len() / PAGE_SIZE;
    let mut target_page = None;
    for p in (22..num_pages).rev() {
        let dp_off = p * PAGE_SIZE;
        if data[dp_off] == 0x01 && read_u32_le(data, dp_off + 4) == LVAL_MAGIC_TDEF {
            let free_space = read_u16_le(data, dp_off + 2) as usize;
            let num_rows = read_u16_le(data, dp_off + 12) as usize;
            let last_pos = find_row_end(&data[dp_off..dp_off + PAGE_SIZE], num_rows, 14, PAGE_SIZE);
            if free_space >= row_len + 2 && last_pos >= 14 + (num_rows + 1) * 2 + row_len {
                target_page = Some(p);
                break;
            }
        }
    }
    let lpage = target_page.unwrap_or_else(|| {
        let np = allocate_page(data);
        let dp_off = np * PAGE_SIZE;
        data[dp_off] = 0x01;
        data[dp_off + 1] = 0x01;
        write_u16_le(data, dp_off + 2, 4082);
        write_u32_le(data, dp_off + 4, LVAL_MAGIC_TDEF);
        write_u16_le(data, dp_off + 12, 0);
        np
    });
    let rnum = append_row_to_data_page(data, lpage, &row_buf, false);
    (lpage, rnum)
}

fn value_to_bool(v: &Value) -> bool {
    match v {
        Value::Bool(b) => *b,
        Value::Number(n) => n.as_f64().unwrap_or(0.0) != 0.0,
        Value::String(s) => {
            let t = s.trim().to_lowercase();
            t == "true" || t == "1" || t == "-1" || t == "yes"
        }
        _ => false,
    }
}

fn value_to_i64(v: &Value) -> Option<i64> {
    match v {
        Value::Number(n) => n.as_i64().or_else(|| n.as_f64().map(|f| f as i64)),
        Value::Bool(b) => Some(if *b { -1 } else { 0 }),
        Value::String(s) => s
            .trim()
            .parse::<i64>()
            .ok()
            .or_else(|| s.trim().parse::<f64>().ok().map(|f| f as i64)),
        _ => None,
    }
}

fn value_to_f64(v: &Value) -> Option<f64> {
    match v {
        Value::Number(n) => n.as_f64(),
        Value::String(s) => s.trim().parse::<f64>().ok(),
        Value::Bool(b) => Some(if *b { -1.0 } else { 0.0 }),
        _ => None,
    }
}

fn value_to_access_date_f64(v: &Value) -> Option<f64> {
    let base = NaiveDate::from_ymd_opt(1899, 12, 30)?.and_hms_opt(0, 0, 0)?;
    match v {
        Value::Number(n) => {
            let ms = n.as_f64()?;
            // Millisecond timestamp (e.g. 1780099200000) -> convert via chrono Local or UTC
            // Note: in Python `datetime.fromtimestamp(ts_ms / 1000.0)` uses local time!
            let secs = (ms / 1000.0).floor() as i64;
            let nsecs = (((ms % 1000.0) + 1000.0) % 1000.0 * 1_000_000.0) as u32;
            if let Some(utc_dt) = chrono::DateTime::from_timestamp(secs, nsecs) {
                use chrono::TimeZone;
                let local_dt = chrono::Local.from_utc_datetime(&utc_dt.naive_utc()).naive_local();
                let diff = local_dt.signed_duration_since(base);
                let days = diff.num_days() as f64;
                let rem_ms = (diff.num_milliseconds() - diff.num_days() * 86_400_000) as f64;
                let frac = (rem_ms / 86_400_000.0).abs();
                return Some(if days < 0.0 { days - frac } else { days + frac });
            }
            None
        }
        Value::String(s) => {
            let clean = s.trim().trim_end_matches('Z');
            let dt = NaiveDateTime::parse_from_str(clean, "%Y-%m-%dT%H:%M:%S")
                .or_else(|_| NaiveDateTime::parse_from_str(clean, "%Y-%m-%d %H:%M:%S"))
                .or_else(|_| {
                    NaiveDate::parse_from_str(clean, "%Y-%m-%d")
                        .map(|d| d.and_hms_opt(0, 0, 0).unwrap())
                })
                .ok()?;
            let diff = dt.signed_duration_since(base);
            let days = diff.num_days() as f64;
            let rem_ms = (diff.num_milliseconds() - diff.num_days() * 86_400_000) as f64;
            let frac = (rem_ms / 86_400_000.0).abs();
            Some(if days < 0.0 { days - frac } else { days + frac })
        }
        _ => None,
    }
}

fn encode_money_i64(v: &Value) -> i64 {
    if let Some(s) = v.as_str() {
        if let Ok(f) = s.trim().parse::<f64>() {
            return (f * 10_000.0).round() as i64;
        }
    }
    if let Some(f) = value_to_f64(v) {
        return (f * 10_000.0).round() as i64;
    }
    0
}

fn encode_numeric_17(v: &Value, scale: u8) -> [u8; 17] {
    let mut out = [0u8; 17];
    let s = match v {
        Value::String(st) => st.trim().to_string(),
        Value::Number(n) => n.to_string(),
        _ => "0".to_string(),
    };
    let neg = s.starts_with('-');
    let clean = s.trim_start_matches('-').trim_start_matches('+');
    let parts: Vec<&str> = clean.split('.').collect();
    let int_part = parts.first().copied().unwrap_or("0");
    let frac_part = parts.get(1).copied().unwrap_or("");
    let sc = scale as usize;
    let mut combined = String::from(int_part);
    if sc > 0 {
        if frac_part.len() >= sc {
            combined.push_str(&frac_part[..sc]);
        } else {
            combined.push_str(frac_part);
            combined.push_str(&"0".repeat(sc - frac_part.len()));
        }
    }
    let unscaled = combined.parse::<u128>().unwrap_or(0);
    out[0] = if neg && unscaled > 0 { 0x01 } else { 0x00 };
    let be = unscaled.to_be_bytes();
    for seg in 0..4 {
        let off = 1 + seg * 4;
        out[off] = be[seg * 4 + 3];
        out[off + 1] = be[seg * 4 + 2];
        out[off + 2] = be[seg * 4 + 1];
        out[off + 3] = be[seg * 4];
    }
    out
}

fn encode_guid_16(v: &Value) -> [u8; 16] {
    let mut out = [0u8; 16];
    let s = v.as_str().unwrap_or("").trim().trim_matches(|c| c == '{' || c == '}');
    let hex: String = s.chars().filter(|c| c.is_ascii_hexdigit()).collect();
    if hex.len() == 32 {
        for i in 0..16 {
            out[i] = u8::from_str_radix(&hex[i * 2..i * 2 + 2], 16).unwrap_or(0);
        }
        out[0..4].reverse();
        out[4..6].reverse();
        out[6..8].reverse();
    }
    out
}

pub fn encode_row_jet4(data: &mut Vec<u8>, tdef: &TableDef, row_map: &Map<String, Value>) -> Vec<u8> {
    let mut lower_lookup: HashMap<String, &Value> = HashMap::with_capacity(row_map.len());
    for (k, v) in row_map {
        lower_lookup.insert(k.to_lowercase(), v);
    }

    let max_cols = (tdef.max_cols as usize).max(tdef.columns.len());
    let var_cols = tdef.var_cols as usize;
    let mut fixed_data_len = 0usize;
    for c in &tdef.columns {
        if c.is_fixed && c.col_type != 1 {
            let end = c.fixed_off + (c.length as usize);
            if end > fixed_data_len {
                fixed_data_len = end;
            }
        }
    }

    let null_mask_len = (max_cols + 7) / 8;
    let mut null_mask = vec![0u8; null_mask_len];
    let mut fixed_buf = vec![0u8; fixed_data_len];

    // Sort variable columns by var_col_num
    let mut var_col_payloads: Vec<Option<Vec<u8>>> = vec![None; var_cols];

    for c in &tdef.columns {
        let val_opt = row_map
            .get(&c.name)
            .or_else(|| lower_lookup.get(&c.name.to_lowercase()).copied());
        let cid = c.col_id;

        if c.col_type == 1 {
            // BOOLEAN: stored in null_mask
            let b = val_opt.map(value_to_bool).unwrap_or(false);
            if b && cid < max_cols {
                null_mask[cid / 8] |= 1 << (cid % 8);
            }
            continue;
        }

        let val = match val_opt {
            Some(v) if !v.is_null() => v,
            _ => continue,
        };

        if c.is_fixed {
            let foff = c.fixed_off;
            let mut wrote = true;
            match c.col_type {
                2 => {
                    if let Some(i) = value_to_i64(val) {
                        if foff < fixed_buf.len() {
                            fixed_buf[foff] = i as u8;
                        }
                    } else {
                        wrote = false;
                    }
                }
                3 => {
                    if let Some(i) = value_to_i64(val) {
                        if foff + 2 <= fixed_buf.len() {
                            write_i16_le(&mut fixed_buf, foff, i as i16);
                        }
                    } else {
                        wrote = false;
                    }
                }
                4 | 18 => {
                    if let Some(i) = value_to_i64(val) {
                        if foff + 4 <= fixed_buf.len() {
                            write_i32_le(&mut fixed_buf, foff, i as i32);
                        }
                    } else {
                        wrote = false;
                    }
                }
                5 => {
                    if foff + 8 <= fixed_buf.len() {
                        write_i64_le(&mut fixed_buf, foff, encode_money_i64(val));
                    }
                }
                6 => {
                    if let Some(f) = value_to_f64(val) {
                        if foff + 4 <= fixed_buf.len() {
                            write_f32_le(&mut fixed_buf, foff, f as f32);
                        }
                    } else {
                        wrote = false;
                    }
                }
                7 => {
                    if let Some(f) = value_to_f64(val) {
                        if foff + 8 <= fixed_buf.len() {
                            write_f64_le(&mut fixed_buf, foff, f);
                        }
                    } else {
                        wrote = false;
                    }
                }
                8 => {
                    if let Some(d) = value_to_access_date_f64(val) {
                        if foff + 8 <= fixed_buf.len() {
                            write_f64_le(&mut fixed_buf, foff, d);
                        }
                    } else {
                        wrote = false;
                    }
                }
                15 => {
                    if foff + 16 <= fixed_buf.len() {
                        fixed_buf[foff..foff + 16].copy_from_slice(&encode_guid_16(val));
                    }
                }
                16 => {
                    if foff + 17 <= fixed_buf.len() {
                        fixed_buf[foff..foff + 17]
                            .copy_from_slice(&encode_numeric_17(val, c.scale));
                    }
                }
                19 => {
                    if let Some(i) = value_to_i64(val) {
                        if foff + 8 <= fixed_buf.len() {
                            write_i64_le(&mut fixed_buf, foff, i);
                        }
                    } else {
                        wrote = false;
                    }
                }
                _ => {
                    wrote = false;
                }
            }
            if wrote && cid < max_cols {
                null_mask[cid / 8] |= 1 << (cid % 8);
            }
        } else {
            let vnum = c.var_col_num;
            if vnum >= var_cols {
                continue;
            }
            let encoded_opt: Option<Vec<u8>> = match c.col_type {
                10 => {
                    let s_cow = match val {
                        Value::String(s) => s.clone(),
                        Value::Number(n) => n.to_string(),
                        Value::Bool(b) => b.to_string(),
                        _ => String::new(),
                    };
                    let max_units = if c.length >= 2 {
                        (c.length / 2) as usize
                    } else {
                        255
                    };
                    let truncated: String = s_cow.chars().take(max_units).collect();
                    Some(encode_jet4_text(&truncated, true))
                }
                12 => {
                    let s_cow = match val {
                        Value::String(s) => s.clone(),
                        Value::Number(n) => n.to_string(),
                        _ => String::new(),
                    };
                    let text_bytes = encode_jet4_text(&s_cow, true);
                    Some(write_lval_bytes(data, &text_bytes))
                }
                9 => {
                    if let Some(s) = val.as_str() {
                        BASE64.decode(s).ok()
                    } else {
                        None
                    }
                }
                11 => {
                    if let Some(s) = val.as_str() {
                        BASE64
                            .decode(s)
                            .ok()
                            .map(|raw| write_lval_bytes(data, &raw))
                    } else {
                        None
                    }
                }
                16 => Some(encode_numeric_17(val, c.scale).to_vec()),
                _ => None,
            };
            if let Some(enc) = encoded_opt {
                if cid < max_cols {
                    null_mask[cid / 8] |= 1 << (cid % 8);
                }
                var_col_payloads[vnum] = Some(enc);
            }
        }
    }

    let mut out = Vec::with_capacity(2 + fixed_data_len + var_cols * 16 + null_mask_len);
    out.extend_from_slice(&(max_cols as u16).to_le_bytes());
    out.extend_from_slice(&fixed_buf);

    let mut var_offsets = Vec::with_capacity(var_cols);
    for v_item in &var_col_payloads {
        var_offsets.push(out.len() as u16);
        if let Some(bytes) = v_item {
            out.extend_from_slice(bytes);
        }
    }
    let eod = out.len() as u16;
    if var_cols > 0 {
        out.extend_from_slice(&eod.to_le_bytes());
        for &off in var_offsets.iter().rev() {
            out.extend_from_slice(&off.to_le_bytes());
        }
        out.extend_from_slice(&(var_cols as u16).to_le_bytes());
    }
    out.extend_from_slice(&null_mask);
    out
}

fn genleg_ascii_sort_bytes(name: &str) -> Vec<u8> {
    let mut out = Vec::with_capacity(name.len() + 3);
    out.push(0x7F);
    for ch in name.chars() {
        let code = ch as u32;
        match code {
            0x20 => out.push(0x07),
            0x21 => out.push(0x09),
            0x22 => out.push(0x0A),
            0x23 => out.push(0x0C),
            0x24 => out.push(0x0E),
            0x25 => out.push(0x10),
            0x26 => out.push(0x12),
            0x28 => out.push(0x14),
            0x29 => out.push(0x16),
            0x2A => out.push(0x18),
            0x2B => out.push(0x2C),
            0x2C => out.push(0x1A),
            0x2E => out.push(0x1C),
            0x2F => out.push(0x1E),
            0x30..=0x39 => out.push(0x36 + ((code - 0x30) as u8) * 2),
            0x3A => out.push(0x20),
            0x3B => out.push(0x22),
            0x3C => out.push(0x2E),
            0x3D => out.push(0x30),
            0x3E => out.push(0x32),
            0x3F => out.push(0x24),
            0x40 => out.push(0x26),
            0x41..=0x5A | 0x61..=0x7A => {
                const LETTER_WEIGHTS: [u8; 26] = [
                    0x4A, 0x4C, 0x4D, 0x4F, 0x51, 0x53, 0x55, 0x57, 0x59, 0x5B, 0x5C, 0x5E, 0x60,
                    0x62, 0x64, 0x66, 0x68, 0x69, 0x6B, 0x6D, 0x6F, 0x71, 0x73, 0x75, 0x76, 0x78,
                ];
                let idx = (ch.to_ascii_uppercase() as u8 - b'A') as usize;
                out.push(LETTER_WEIGHTS[idx]);
            }
            0x5B => out.push(0x27),
            0x5C => out.push(0x29),
            0x5D => out.push(0x2A),
            0x5E => out.extend_from_slice(&[0x2B, 0x02]),
            0x5F => out.extend_from_slice(&[0x2B, 0x03]),
            0x60 => out.extend_from_slice(&[0x2B, 0x07]),
            0x7B => out.extend_from_slice(&[0x2B, 0x09]),
            0x7C => out.extend_from_slice(&[0x2B, 0x0B]),
            0x7D => out.extend_from_slice(&[0x2B, 0x0D]),
            0x7E => out.extend_from_slice(&[0x2B, 0x0F]),
            _ => out.push(0x4A),
        }
    }
    out.push(0x01);
    out.push(0x00);
    out
}

fn insert_uncompressed_index_leaf_entry(
    data: &mut [u8],
    idx_page: usize,
    entry_bytes: &[u8],
) -> bool {
    let ip_off = idx_page * PAGE_SIZE;
    if data[ip_off] != 0x04 {
        return false;
    }
    let free_space = read_u16_le(data, ip_off + 2) as usize;
    let comp_cnt = read_u16_le(data, ip_off + 24) as usize;
    if comp_cnt != 0 || free_space < entry_bytes.len() {
        return false;
    }
    let mask = &data[ip_off + 27..ip_off + 480];
    let mut ends = Vec::new();
    for bit_idx in 0..(453 * 8) {
        if (mask[bit_idx / 8] & (1 << (bit_idx % 8))) != 0 {
            ends.push(bit_idx);
        }
    }
    let mut entries: Vec<Vec<u8>> = Vec::with_capacity(ends.len() + 1);
    let mut prev = 0usize;
    for end in ends {
        if 480 + end <= PAGE_SIZE {
            entries.push(data[ip_off + 480 + prev..ip_off + 480 + end].to_vec());
        }
        prev = end;
    }
    entries.push(entry_bytes.to_vec());
    entries.sort();

    let total_bytes: usize = entries.iter().map(|e| e.len()).sum();
    if 480 + total_bytes > PAGE_SIZE || total_bytes >= 453 * 8 {
        return false;
    }
    for b in &mut data[ip_off + 27..ip_off + PAGE_SIZE] {
        *b = 0;
    }
    let mut pos = 0usize;
    for e in &entries {
        data[ip_off + 480 + pos..ip_off + 480 + pos + e.len()].copy_from_slice(e);
        pos += e.len();
        let bit_idx = pos;
        data[ip_off + 27 + (bit_idx / 8)] |= 1 << (bit_idx % 8);
    }
    write_u16_le(data, ip_off + 2, (free_space - entry_bytes.len()) as u16);
    true
}

pub fn create_table_in_data(
    data: &mut Vec<u8>,
    table_name: &str,
    columns: &[ColumnDef],
    indexes: &[IndexDef],
) -> Result<usize, String> {
    let existing = discover_tables(data, true)?;
    if existing
        .keys()
        .any(|k| k.eq_ignore_ascii_case(table_name))
    {
        return Err(format!("Table '{}' already exists", table_name));
    }

    let col_count = columns.len();
    let mut cols: Vec<ColumnDef> = Vec::with_capacity(col_count);
    let mut non_lval_var_count = 0usize;
    let mut lval_col_ids = Vec::new();

    for (idx, c) in columns.iter().enumerate() {
        let mut cd = c.clone();
        cd.col_type = if cd.col_type != 0 {
            cd.col_type
        } else {
            name_to_col_type(&cd.col_type_name)
        };
        cd.col_type_name = crate::mdb::col_type_to_name(cd.col_type).to_string();
        cd.col_id = idx;
        cd.col_index = idx as u16;
        cd.is_fixed = !matches!(cd.col_type, 9 | 10 | 11 | 12 | 16);
        if matches!(cd.col_type, 9 | 10 | 16) {
            non_lval_var_count += 1;
        } else if matches!(cd.col_type, 11 | 12) {
            lval_col_ids.push(idx as u16);
        }
        cols.push(cd);
    }

    let mut var_off = 0usize;
    let mut lval_off = non_lval_var_count;
    let mut fixed_off = 0usize;
    for c in &mut cols {
        if c.is_fixed {
            c.var_col_num = var_off;
            if c.col_type == 1 {
                c.fixed_off = 0;
                c.length = 1;
            } else {
                c.fixed_off = fixed_off;
                let fsize: u16 = match c.col_type {
                    2 => 1,
                    3 => 2,
                    4 | 6 | 18 => 4,
                    5 | 7 | 8 | 19 => 8,
                    15 => 16,
                    16 => 17,
                    _ => c.length.max(1),
                };
                c.length = fsize;
                fixed_off += fsize as usize;
            }
        } else if matches!(c.col_type, 11 | 12) {
            c.var_col_num = lval_off;
            lval_off += 1;
            c.fixed_off = 0;
            c.length = 0;
        } else {
            c.var_col_num = var_off;
            var_off += 1;
            c.fixed_off = 0;
            if c.col_type == 10 {
                if c.length == 0 {
                    c.length = 510;
                } else if c.length <= 255 && c.length % 2 == 1 {
                    c.length *= 2;
                }
            } else if c.col_type == 16 {
                c.length = 17;
                if c.precision == 0 {
                    c.precision = 18;
                }
            } else if c.length == 0 {
                c.length = 255;
            }
        }
    }
    let total_var_cols = lval_off;

    let valid_indexes: Vec<&IndexDef> = indexes
        .iter()
        .filter(|ix| !ix.name.starts_with('.'))
        .collect();
    let idx_count = valid_indexes.len();

    let tdef_page = allocate_page(data);
    let umap_page = allocate_page(data);

    let mut idx_root_pages = Vec::with_capacity(idx_count);
    for _ in 0..idx_count {
        let ipage = allocate_page(data);
        let ip_off = ipage * PAGE_SIZE;
        data[ip_off] = 0x04;
        data[ip_off + 1] = 0x01;
        write_u16_le(data, ip_off + 2, (PAGE_SIZE - 480) as u16);
        write_u32_le(data, ip_off + 4, tdef_page as u32);
        idx_root_pages.push(ipage);
    }

    // Initialize umap_page rows (Row 0 = owned pages, Row 1 = free space, Rows 2.. = index + LVAL umaps)
    let total_umap_rows = 2 + idx_count + lval_col_ids.len() * 2;
    {
        let up_off = umap_page * PAGE_SIZE;
        data[up_off] = 0x01;
        data[up_off + 1] = 0x01;
        write_u16_le(data, up_off + 2, 4082);
        write_u32_le(data, up_off + 4, 0);
        write_u16_le(data, up_off + 12, 0);
        let empty_inline_umap = [0u8; 69]; // byte 0 = 0x00 (Inline), bytes 1..5 = start_page 0, 64B bitmap
        for r in 0..total_umap_rows {
            append_row_to_data_page(data, umap_page, &empty_inline_umap, false);
            if r >= 2 && r < 2 + idx_count {
                let ipage = idx_root_pages[r - 2];
                let uptr = ((umap_page as u32) << 8) | (r as u32);
                set_usage_map_bit(data, uptr, ipage, true);
            }
        }
    }

    let col_id_by_lower_name: HashMap<String, u16> = cols
        .iter()
        .map(|c| (c.name.to_lowercase(), c.col_id as u16))
        .collect();

    // Build TDEF byte buffer
    let mut tdef_buf = vec![0u8; 63];
    tdef_buf[0] = 0x02;
    tdef_buf[1] = 0x01;
    write_u32_le(&mut tdef_buf, 12, 1625);
    write_u32_le(&mut tdef_buf, 16, 0); // rowCount
    write_u32_le(&mut tdef_buf, 20, 0); // nextAutoNumber
    tdef_buf[24] = 1;
    tdef_buf[40] = 0x4E; // 'N' user table
    write_u16_le(&mut tdef_buf, 41, col_count as u16);
    write_u16_le(&mut tdef_buf, 43, total_var_cols as u16);
    write_u16_le(&mut tdef_buf, 45, col_count as u16);
    write_u32_le(&mut tdef_buf, 47, idx_count as u32);
    write_u32_le(&mut tdef_buf, 51, idx_count as u32);
    let owned_ptr = ((umap_page as u32) << 8) | 0;
    let free_ptr = ((umap_page as u32) << 8) | 1;
    write_u32_le(&mut tdef_buf, 55, owned_ptr);
    write_u32_le(&mut tdef_buf, 59, free_ptr);

    // 1. Index row-count definitions (12 bytes * idx_count)
    tdef_buf.resize(tdef_buf.len() + idx_count * 12, 0);

    // 2. Column definitions (25 bytes * col_count)
    for c in &cols {
        let mut cb = [0u8; 25];
        cb[0] = c.col_type;
        write_u32_le(&mut cb, 1, 1625);
        write_u16_le(&mut cb, 5, c.col_id as u16);
        write_u16_le(&mut cb, 7, c.var_col_num as u16);
        write_u16_le(&mut cb, 9, c.col_index);
        if matches!(c.col_type, 10 | 12) {
            cb[11] = 0x09;
            cb[12] = 0x04;
            cb[13] = 0x00;
            cb[14] = 0x00;
        } else if c.col_type == 16 {
            cb[11] = if c.precision > 0 { c.precision } else { 18 };
            cb[12] = c.scale;
        }
        let mut flags = 0x02u8; // updatable
        if c.is_fixed {
            flags |= 0x01;
        }
        if c.auto_number {
            flags |= 0x04;
        }
        cb[15] = flags;
        cb[16] = if matches!(c.col_type, 10 | 12) {
            0x01
        } else {
            0x00
        };
        write_u16_le(&mut cb, 21, if c.is_fixed { c.fixed_off as u16 } else { 0 });
        write_u16_le(&mut cb, 23, c.length);
        tdef_buf.extend_from_slice(&cb);
    }

    // 3. Column names (UTF-16LE)
    for c in &cols {
        let nb = encode_utf16le(&c.name);
        tdef_buf.extend_from_slice(&(nb.len() as u16).to_le_bytes());
        tdef_buf.extend_from_slice(&nb);
    }

    // 4. Physical index column blocks (52 bytes * idx_count)
    for (i, ix) in valid_indexes.iter().enumerate() {
        let mut ib = [0u8; 52];
        write_u32_le(&mut ib, 0, 1923);
        for s in 0..10 {
            let off = 4 + s * 3;
            if let Some(cname) = ix.columns.get(s) {
                let cid = col_id_by_lower_name
                    .get(&cname.to_lowercase())
                    .copied()
                    .unwrap_or(0xFFFF);
                write_u16_le(&mut ib, off, cid);
                ib[off + 2] = 0x01; // ASC
            } else {
                write_u16_le(&mut ib, off, 0xFFFF);
                ib[off + 2] = 0x01;
            }
        }
        let idx_umap_row = (2 + i) as u8;
        let idx_uptr = ((umap_page as u32) << 8) | (idx_umap_row as u32);
        write_u32_le(&mut ib, 34, idx_uptr);
        write_u32_le(&mut ib, 38, idx_root_pages[i] as u32);
        let uflag = if ix.unique { 0x01u8 } else { 0x00u8 };
        ib[42] = uflag;
        ib[46] = uflag;
        tdef_buf.extend_from_slice(&ib);
    }

    // 5. Logical index info blocks (28 bytes * idx_count)
    for (i, ix) in valid_indexes.iter().enumerate() {
        let mut lb = [0u8; 28];
        write_u32_le(&mut lb, 0, 1923);
        write_u32_le(&mut lb, 4, i as u32);
        write_u32_le(&mut lb, 8, i as u32);
        lb[23] = if ix.name.eq_ignore_ascii_case("PrimaryKey") {
            1
        } else {
            0
        };
        tdef_buf.extend_from_slice(&lb);
    }

    // 6. Logical index names (UTF-16LE)
    for ix in &valid_indexes {
        let nb = encode_utf16le(&ix.name);
        tdef_buf.extend_from_slice(&(nb.len() as u16).to_le_bytes());
        tdef_buf.extend_from_slice(&nb);
    }

    // 7. LVAL column usage map pointers (10 bytes * lval_col_count)
    for (li, &cid) in lval_col_ids.iter().enumerate() {
        let mut lblk = [0u8; 10];
        write_u16_le(&mut lblk, 0, cid);
        let r_owned = (2 + idx_count + li * 2) as u32;
        let r_free = r_owned + 1;
        write_u32_le(&mut lblk, 2, ((umap_page as u32) << 8) | r_owned);
        write_u32_le(&mut lblk, 6, ((umap_page as u32) << 8) | r_free);
        tdef_buf.extend_from_slice(&lblk);
    }

    // 8. Trailer (0xFFFF)
    tdef_buf.extend_from_slice(&[0xFF, 0xFF]);

    let total_tdef_len = tdef_buf.len();
    write_u32_le(&mut tdef_buf, 8, total_tdef_len as u32);

    // Write TDEF into tdef_page (and continuation pages if > 4096 bytes)
    if total_tdef_len <= PAGE_SIZE {
        let free_tdef = PAGE_SIZE - total_tdef_len;
        write_u16_le(&mut tdef_buf, 2, free_tdef as u16);
        write_u32_le(&mut tdef_buf, 4, 0);
        let tp_off = tdef_page * PAGE_SIZE;
        data[tp_off..tp_off + total_tdef_len].copy_from_slice(&tdef_buf);
    } else {
        let rem_len = total_tdef_len - PAGE_SIZE;
        let num_cont = (rem_len + (PAGE_SIZE - 8) - 1) / (PAGE_SIZE - 8);
        let mut cont_pages = Vec::with_capacity(num_cont);
        for _ in 0..num_cont {
            cont_pages.push(allocate_page(data));
        }
        write_u16_le(&mut tdef_buf, 2, 0);
        write_u32_le(&mut tdef_buf, 4, cont_pages[0] as u32);
        let tp_off = tdef_page * PAGE_SIZE;
        data[tp_off..tp_off + PAGE_SIZE].copy_from_slice(&tdef_buf[..PAGE_SIZE]);
        for (ci, chunk) in tdef_buf[PAGE_SIZE..].chunks(PAGE_SIZE - 8).enumerate() {
            let cp = cont_pages[ci];
            let next_p = cont_pages.get(ci + 1).copied().unwrap_or(0);
            let cp_off = cp * PAGE_SIZE;
            data[cp_off] = 0x02;
            data[cp_off + 1] = 0x01;
            write_u16_le(data, cp_off + 2, (PAGE_SIZE - 8 - chunk.len()) as u16);
            write_u32_le(data, cp_off + 4, next_p as u32);
            data[cp_off + 8..cp_off + 8 + chunk.len()].copy_from_slice(chunk);
        }
    }

    // Register in MSysObjects (Page 2)
    register_table_in_msys_objects(data, table_name, tdef_page)?;
    Ok(tdef_page)
}

fn register_table_in_msys_objects(
    data: &mut Vec<u8>,
    table_name: &str,
    tdef_page: usize,
) -> Result<(), String> {
    let msys_tdef = parse_table_ver(data, 2, JetVersion::Jet4)?;
    let mut row_map = Map::new();
    row_map.insert("Id".to_string(), Value::Number((tdef_page as i64).into()));
    row_map.insert(
        "ParentId".to_string(),
        Value::Number((0x0F00_0001i64).into()),
    );
    row_map.insert("Name".to_string(), Value::String(table_name.to_string()));
    row_map.insert("Type".to_string(), Value::Number(1.into()));
    row_map.insert(
        "DateCreate".to_string(),
        Value::String("2026-01-01T00:00:00".to_string()),
    );
    row_map.insert(
        "DateUpdate".to_string(),
        Value::String("2026-01-01T00:00:00".to_string()),
    );
    row_map.insert(
        "Owner".to_string(),
        Value::String(BASE64.encode([0xA6u8, 0x33u8])),
    );
    row_map.insert("Flags".to_string(), Value::Number(0.into()));

    let row_bytes = encode_row_jet4(data, &msys_tdef, &row_map);
    let dpage = find_or_alloc_data_page_for_row(
        data,
        2,
        msys_tdef.owned_pages_ptr,
        msys_tdef.free_space_ptr,
        row_bytes.len(),
        None,
    );
    let rnum = append_row_to_data_page(data, dpage, &row_bytes, false);

    // Increment MSysObjects row count on Page 2 (+16)
    let p2_off = 2 * PAGE_SIZE;
    let old_cnt = read_u32_le(data, p2_off + 16);
    write_u32_le(data, p2_off + 16, old_cnt + 1);

    // Update MSysObjects Index 0 (ParentIdName on Page 7) and Index 1 (Id on Page 8)
    let mut p7_entry = vec![0x7F, 0x8F, 0x00, 0x00, 0x01];
    p7_entry.extend_from_slice(&genleg_ascii_sort_bytes(table_name));
    let dp_be = (dpage as u32).to_be_bytes();
    p7_entry.push(dp_be[1]);
    p7_entry.push(dp_be[2]);
    p7_entry.push(dp_be[3]);
    p7_entry.push(rnum as u8);

    let mut p8_entry = vec![0x7F];
    let id_be = ((tdef_page as u32) ^ 0x8000_0000).to_be_bytes();
    p8_entry.extend_from_slice(&id_be);
    p8_entry.push(dp_be[1]);
    p8_entry.push(dp_be[2]);
    p8_entry.push(dp_be[3]);
    p8_entry.push(rnum as u8);

    let ok7 = insert_uncompressed_index_leaf_entry(data, 7, &p7_entry);
    let ok8 = insert_uncompressed_index_leaf_entry(data, 8, &p8_entry);
    if ok7 && ok8 {
        let u0 = read_u32_le(data, p2_off + 67);
        write_u32_le(data, p2_off + 67, u0 + 1);
        let u1 = read_u32_le(data, p2_off + 79);
        write_u32_le(data, p2_off + 79, u1 + 1);
    } else {
        // If Page 7 or Page 8 leaf is full (e.g. > 150 tables), mark MSysObjects index slots = 0
        // so Jackcess DefaultTableFinder gracefully falls back to FallbackTableFinder table scan!
        write_u32_le(data, p2_off + 47, 0);
        write_u32_le(data, p2_off + 51, 0);
    }
    Ok(())
}

pub fn find_table_page(data: &[u8], table_name: &str) -> Result<usize, String> {
    let tables = discover_tables(data, true)?;
    for (k, p) in tables {
        if k.eq_ignore_ascii_case(table_name) {
            return Ok(p);
        }
    }
    Err(format!("Table '{}' not found", table_name))
}

pub fn add_rows_to_table(
    data: &mut Vec<u8>,
    table_name: &str,
    rows: &[Map<String, Value>],
    allow_autonum: bool,
) -> Result<Vec<i64>, String> {
    let tdef_page = find_table_page(data, table_name)?;
    let tdef = parse_table_ver(data, tdef_page, JetVersion::Jet4)?;
    let auto_col = tdef.columns.iter().find(|c| c.auto_number).cloned();
    let mut cur_auto = tdef.next_auto_number as i64;
    let mut cur_row_count = tdef.tdef_row_count;
    let mut assigned_ids = Vec::with_capacity(rows.len());

    for r in rows {
        let mut row_copy = r.clone();
        let mut assigned = 0i64;
        if let Some(ref acol) = auto_col {
            let existing_val = row_copy
                .iter()
                .find(|(k, _)| k.eq_ignore_ascii_case(&acol.name))
                .and_then(|(_, v)| value_to_i64(v));
            if allow_autonum {
                if let Some(ev) = existing_val {
                    assigned = ev;
                    if ev > cur_auto {
                        cur_auto = ev;
                    }
                } else {
                    cur_auto += 1;
                    assigned = cur_auto;
                    row_copy.insert(acol.name.clone(), Value::Number(assigned.into()));
                }
            } else {
                cur_auto += 1;
                assigned = cur_auto;
                row_copy.retain(|k, _| !k.eq_ignore_ascii_case(&acol.name));
                row_copy.insert(acol.name.clone(), Value::Number(assigned.into()));
            }
        }
        let row_bytes = encode_row_jet4(data, &tdef, &row_copy);
        let dpage = find_or_alloc_data_page_for_row(
            data,
            tdef_page,
            tdef.owned_pages_ptr,
            tdef.free_space_ptr,
            row_bytes.len(),
            None,
        );
        append_row_to_data_page(data, dpage, &row_bytes, false);
        cur_row_count += 1;
        assigned_ids.push(assigned);
    }

    let tp_off = tdef_page * PAGE_SIZE;
    write_u32_le(data, tp_off + 16, cur_row_count);
    if auto_col.is_some() {
        write_i32_le(data, tp_off + 20, cur_auto as i32);
    }
    Ok(assigned_ids)
}

pub fn update_row_in_table(
    data: &mut Vec<u8>,
    table_name: &str,
    page_num: usize,
    row_num: usize,
    updated_row: &Map<String, Value>,
) -> Result<(), String> {
    let tdef_page = find_table_page(data, table_name)?;
    let tdef = parse_table_ver(data, tdef_page, JetVersion::Jet4)?;
    let new_row_bytes = encode_row_jet4(data, &tdef, updated_row);
    replace_or_overflow_row_on_page(
        data,
        tdef_page,
        tdef.owned_pages_ptr,
        tdef.free_space_ptr,
        page_num,
        row_num,
        &new_row_bytes,
    )
}

fn replace_or_overflow_row_on_page(
    data: &mut Vec<u8>,
    tdef_page: usize,
    owned_ptr: u32,
    free_ptr: u32,
    page_num: usize,
    row_num: usize,
    new_row_bytes: &[u8],
) -> Result<(), String> {
    if (page_num + 1) * PAGE_SIZE > data.len() {
        return Err("Data page out of bounds".to_string());
    }
    let dp_off = page_num * PAGE_SIZE;
    let num_rows = read_u16_le(data, dp_off + 12) as usize;
    if row_num >= num_rows {
        return Err("Row number out of bounds".to_string());
    }
    let raw_off = read_u16_le(data, dp_off + 14 + row_num * 2);
    if (raw_off & 0x8000) != 0 {
        return Err("Cannot update a deleted row".to_string());
    }
    // If the row was already an overflow pointer, delete the old overflow target row first
    if (raw_off & 0x4000) != 0 {
        let p_start = (raw_off & 0x1FFF) as usize;
        if p_start + 4 <= PAGE_SIZE {
            let ovf_row = data[dp_off + p_start] as usize;
            let ovf_page = u32::from_le_bytes([
                data[dp_off + p_start + 1],
                data[dp_off + p_start + 2],
                data[dp_off + p_start + 3],
                0,
            ]) as usize;
            let _ = delete_physical_row_on_page(data, ovf_page, ovf_row);
        }
    }

    let old_start = (raw_off & 0x1FFF) as usize;
    let old_end = find_row_end(&data[dp_off..dp_off + PAGE_SIZE], row_num, 14, PAGE_SIZE);
    let old_size = old_end.saturating_sub(old_start);
    let free_space = read_u16_le(data, dp_off + 2) as usize;
    let lowest_start = find_row_end(&data[dp_off..dp_off + PAGE_SIZE], num_rows, 14, PAGE_SIZE);
    let hdr_end = 14 + num_rows * 2;
    let new_size = new_row_bytes.len();

    if new_size <= old_size + free_space && lowest_start + old_size >= hdr_end + new_size {
        // In-place replacement on the same page
        let size_diff = (new_size as isize) - (old_size as isize);
        let tail_bytes = data[dp_off + lowest_start..dp_off + old_start].to_vec();
        let new_lowest = ((lowest_start as isize) - size_diff) as usize;
        let new_start = old_end - new_size;
        data[dp_off + new_lowest..dp_off + new_start].copy_from_slice(&tail_bytes);
        data[dp_off + new_start..dp_off + old_end].copy_from_slice(new_row_bytes);

        write_u16_le(data, dp_off + 14 + row_num * 2, new_start as u16);
        for j in (row_num + 1)..num_rows {
            let j_raw = read_u16_le(data, dp_off + 14 + j * 2);
            let j_off = j_raw & 0x1FFF;
            if j_off != 0 {
                let new_j_off = ((j_off as isize) - size_diff) as u16;
                write_u16_le(
                    data,
                    dp_off + 14 + j * 2,
                    (j_raw & 0xE000) | (new_j_off & 0x1FFF),
                );
            }
        }
        let new_free = ((free_space as isize) - size_diff) as u16;
        write_u16_le(data, dp_off + 2, new_free);
    } else {
        // Overflow to another data page
        let target_page = find_or_alloc_data_page_for_row(
            data,
            tdef_page,
            owned_ptr,
            free_ptr,
            new_size,
            Some(page_num),
        );
        // Mark target row with 0x8000 so table scans don't visit it twice
        let target_row = append_row_to_data_page(data, target_page, new_row_bytes, true);
        let mut ptr_bytes = [0u8; 4];
        ptr_bytes[0] = target_row as u8;
        let tp_b = (target_page as u32).to_le_bytes();
        ptr_bytes[1] = tp_b[0];
        ptr_bytes[2] = tp_b[1];
        ptr_bytes[3] = tp_b[2];

        let dp_off = page_num * PAGE_SIZE;
        let size_diff = 4isize - (old_size as isize);
        let tail_bytes = data[dp_off + lowest_start..dp_off + old_start].to_vec();
        let new_lowest = ((lowest_start as isize) - size_diff) as usize;
        let new_start = old_end - 4;
        data[dp_off + new_lowest..dp_off + new_start].copy_from_slice(&tail_bytes);
        data[dp_off + new_start..dp_off + old_end].copy_from_slice(&ptr_bytes);

        write_u16_le(
            data,
            dp_off + 14 + row_num * 2,
            (new_start as u16) | 0x4000,
        );
        for j in (row_num + 1)..num_rows {
            let j_raw = read_u16_le(data, dp_off + 14 + j * 2);
            let j_off = j_raw & 0x1FFF;
            if j_off != 0 {
                let new_j_off = ((j_off as isize) - size_diff) as u16;
                write_u16_le(
                    data,
                    dp_off + 14 + j * 2,
                    (j_raw & 0xE000) | (new_j_off & 0x1FFF),
                );
            }
        }
        let new_free = ((free_space as isize) - size_diff) as u16;
        write_u16_le(data, dp_off + 2, new_free);
    }
    Ok(())
}

fn delete_physical_row_on_page(
    data: &mut [u8],
    page_num: usize,
    row_num: usize,
) -> Result<usize, String> {
    if (page_num + 1) * PAGE_SIZE > data.len() {
        return Err("Data page out of bounds".to_string());
    }
    let dp_off = page_num * PAGE_SIZE;
    let num_rows = read_u16_le(data, dp_off + 12) as usize;
    if row_num >= num_rows {
        return Err("Row number out of bounds".to_string());
    }
    let raw_off = read_u16_le(data, dp_off + 14 + row_num * 2);
    let old_start = (raw_off & 0x1FFF) as usize;
    if old_start == 0 {
        return Ok(0);
    }
    let old_end = find_row_end(&data[dp_off..dp_off + PAGE_SIZE], row_num, 14, PAGE_SIZE);
    let old_size = old_end.saturating_sub(old_start);
    let lowest_start = find_row_end(&data[dp_off..dp_off + PAGE_SIZE], num_rows, 14, PAGE_SIZE);

    let tail_bytes = data[dp_off + lowest_start..dp_off + old_start].to_vec();
    data[dp_off + lowest_start + old_size..dp_off + old_end].copy_from_slice(&tail_bytes);
    write_u16_le(data, dp_off + 14 + row_num * 2, 0x8000);
    for j in (row_num + 1)..num_rows {
        let j_raw = read_u16_le(data, dp_off + 14 + j * 2);
        let j_off = j_raw & 0x1FFF;
        if j_off != 0 {
            let new_j_off = j_off + (old_size as u16);
            write_u16_le(
                data,
                dp_off + 14 + j * 2,
                (j_raw & 0xE000) | (new_j_off & 0x1FFF),
            );
        }
    }
    let free_space = read_u16_le(data, dp_off + 2) as usize;
    write_u16_le(data, dp_off + 2, (free_space + old_size) as u16);
    Ok(old_size)
}

pub fn delete_row_in_table(
    data: &mut Vec<u8>,
    table_name: &str,
    page_num: usize,
    row_num: usize,
) -> Result<(), String> {
    let tdef_page = find_table_page(data, table_name)?;
    let dp_off = page_num * PAGE_SIZE;
    let raw_off = read_u16_le(data, dp_off + 14 + row_num * 2);
    if (raw_off & 0x8000) != 0 {
        return Ok(());
    }
    if (raw_off & 0x4000) != 0 {
        let p_start = (raw_off & 0x1FFF) as usize;
        if p_start + 4 <= PAGE_SIZE {
            let ovf_row = data[dp_off + p_start] as usize;
            let ovf_page = u32::from_le_bytes([
                data[dp_off + p_start + 1],
                data[dp_off + p_start + 2],
                data[dp_off + p_start + 3],
                0,
            ]) as usize;
            let _ = delete_physical_row_on_page(data, ovf_page, ovf_row);
        }
    }
    delete_physical_row_on_page(data, page_num, row_num)?;
    let tp_off = tdef_page * PAGE_SIZE;
    let old_cnt = read_u32_le(data, tp_off + 16);
    write_u32_le(data, tp_off + 16, old_cnt.saturating_sub(1));
    Ok(())
}

pub fn restore_mdb_from_schema_value(schema: &Value, target_mdb: &str) -> Result<(), String> {
    let tables_obj = schema
        .get("tables")
        .and_then(|v| v.as_object())
        .ok_or_else(|| "Missing 'tables' object in schema".to_string())?;

    let mut data = get_empty_v2000_mdb();

    for (table_name, table_val) in tables_obj {
        let cols_val = table_val
            .get("columns")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();
        let idxs_val = table_val
            .get("indexes")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();
        let rows_val = table_val
            .get("rows")
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();

        let mut cols = Vec::with_capacity(cols_val.len());
        for cv in cols_val {
            if let Ok(cd) = serde_json::from_value::<ColumnDef>(cv) {
                cols.push(cd);
            }
        }
        let mut idxs = Vec::with_capacity(idxs_val.len());
        for iv in idxs_val {
            if let Ok(id) = serde_json::from_value::<IndexDef>(iv) {
                idxs.push(id);
            }
        }

        let has_auto = cols.iter().any(|c| c.auto_number);
        create_table_in_data(&mut data, table_name, &cols, &idxs)?;

        if !rows_val.is_empty() {
            let mut row_maps = Vec::with_capacity(rows_val.len());
            for rv in rows_val {
                if let Value::Object(mut m) = rv {
                    if table_name.eq_ignore_ascii_case("SESSIONS") {
                        if let Some(day_v) = m.get_mut("DAY") {
                            if day_v.is_null() {
                                *day_v = Value::Number(1.into());
                            }
                        }
                    }
                    row_maps.push(m);
                }
            }
            add_rows_to_table(&mut data, table_name, &row_maps, has_auto)?;
        }
    }

    fs::write(target_mdb, &data)
        .map_err(|e| format!("Failed to write target MDB {}: {}", target_mdb, e))?;
    Ok(())
}

pub fn create_empty_mdb_file(target_mdb: &str) -> Result<(), String> {
    let data = get_empty_v2000_mdb();
    fs::write(target_mdb, &data)
        .map_err(|e| format!("Failed to write empty MDB {}: {}", target_mdb, e))
}

fn execute_jackcess_op_inner(req: &Value) -> Result<Value, String> {
    let op = req.get("op").and_then(|v| v.as_str()).unwrap_or("");
    match op {
        "create_db" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            create_empty_mdb_file(mdb_path)?;
            Ok(serde_json::json!({ "ok": true }))
        }
        "get_table_names" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            let include_sys = req
                .get("include_system")
                .and_then(|v| v.as_bool())
                .unwrap_or(false);
            let data = fs::read(mdb_path).map_err(|e| e.to_string())?;
            let tables = discover_tables(&data, include_sys)?;
            let names: Vec<String> = tables.keys().cloned().collect();
            Ok(serde_json::json!({ "ok": true, "table_names": names }))
        }
        "read_table" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            let table_name = req
                .get("table_name")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing table_name".to_string())?;
            let data = fs::read(mdb_path).map_err(|e| e.to_string())?;
            let ver = JetVersion::from_data(&data)?;
            let tables = discover_tables(&data, true)?;
            let mut found: Option<(String, usize)> = None;
            for (k, p) in tables {
                if k.eq_ignore_ascii_case(table_name) {
                    found = Some((k, p));
                    break;
                }
            }
            match found {
                Some((phys_name, tpage)) => {
                    let tdef = parse_table_ver(&data, tpage, ver)?;
                    let rids: Vec<Value> = tdef
                        .row_ids
                        .iter()
                        .map(|&(p, r)| serde_json::json!([p, r]))
                        .collect();
                    Ok(serde_json::json!({
                        "ok": true,
                        "found": true,
                        "name": phys_name,
                        "columns": tdef.columns,
                        "indexes": tdef.indexes,
                        "rows": tdef.rows,
                        "row_ids": rids,
                    }))
                }
                None => Ok(serde_json::json!({ "ok": true, "found": false })),
            }
        }
        "create_table" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            let table_name = req
                .get("table_name")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing table_name".to_string())?;
            let cols_val = req
                .get("columns")
                .and_then(|v| v.as_array())
                .cloned()
                .unwrap_or_default();
            let idxs_val = req
                .get("indexes")
                .and_then(|v| v.as_array())
                .cloned()
                .unwrap_or_default();
            let mut cols = Vec::with_capacity(cols_val.len());
            for cv in cols_val {
                let cd: ColumnDef = serde_json::from_value(cv).map_err(|e| e.to_string())?;
                cols.push(cd);
            }
            let mut idxs = Vec::with_capacity(idxs_val.len());
            for iv in idxs_val {
                let id: IndexDef = serde_json::from_value(iv).map_err(|e| e.to_string())?;
                idxs.push(id);
            }
            let mut data = fs::read(mdb_path).map_err(|e| e.to_string())?;
            let tpage = create_table_in_data(&mut data, table_name, &cols, &idxs)?;
            fs::write(mdb_path, &data).map_err(|e| e.to_string())?;
            Ok(serde_json::json!({ "ok": true, "tdef_page": tpage }))
        }
        "add_rows" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            let table_name = req
                .get("table_name")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing table_name".to_string())?;
            let allow_auto = req
                .get("allow_autonum")
                .and_then(|v| v.as_bool())
                .unwrap_or(true);
            let rows_arr = req
                .get("rows")
                .and_then(|v| v.as_array())
                .ok_or_else(|| "Missing rows array".to_string())?;
            let mut row_maps = Vec::with_capacity(rows_arr.len());
            for rv in rows_arr {
                if let Some(m) = rv.as_object() {
                    row_maps.push(m.clone());
                }
            }
            let mut data = fs::read(mdb_path).map_err(|e| e.to_string())?;
            let ids = add_rows_to_table(&mut data, table_name, &row_maps, allow_auto)?;
            fs::write(mdb_path, &data).map_err(|e| e.to_string())?;
            Ok(serde_json::json!({ "ok": true, "assigned_ids": ids }))
        }
        "update_row" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            let table_name = req
                .get("table_name")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing table_name".to_string())?;
            let page_num = req
                .get("page_num")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| "Missing page_num".to_string())? as usize;
            let row_num = req
                .get("row_num")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| "Missing row_num".to_string())? as usize;
            let row_obj = req
                .get("row")
                .and_then(|v| v.as_object())
                .ok_or_else(|| "Missing row object".to_string())?;
            let mut data = fs::read(mdb_path).map_err(|e| e.to_string())?;
            update_row_in_table(&mut data, table_name, page_num, row_num, row_obj)?;
            fs::write(mdb_path, &data).map_err(|e| e.to_string())?;
            Ok(serde_json::json!({ "ok": true }))
        }
        "delete_row" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            let table_name = req
                .get("table_name")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing table_name".to_string())?;
            let page_num = req
                .get("page_num")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| "Missing page_num".to_string())? as usize;
            let row_num = req
                .get("row_num")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| "Missing row_num".to_string())? as usize;
            let mut data = fs::read(mdb_path).map_err(|e| e.to_string())?;
            delete_row_in_table(&mut data, table_name, page_num, row_num)?;
            fs::write(mdb_path, &data).map_err(|e| e.to_string())?;
            Ok(serde_json::json!({ "ok": true }))
        }
        "restore_db" => {
            let target_mdb = req
                .get("target_mdb")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing target_mdb".to_string())?;
            if let Some(schema_val) = req.get("schema") {
                restore_mdb_from_schema_value(schema_val, target_mdb)?;
            } else if let Some(json_path) = req.get("json_path").and_then(|v| v.as_str()) {
                let s = fs::read_to_string(json_path).map_err(|e| e.to_string())?;
                let schema_val: Value = serde_json::from_str(&s).map_err(|e| e.to_string())?;
                restore_mdb_from_schema_value(&schema_val, target_mdb)?;
            } else {
                return Err("Missing schema or json_path".to_string());
            }
            Ok(serde_json::json!({ "ok": true }))
        }
        _ => Err(format!("Unknown jackcess op: {}", op)),
    }
}

pub fn execute_jackcess_op(req: &Value) -> Value {
    match execute_jackcess_op_inner(req) {
        Ok(val) => val,
        Err(err) => serde_json::json!({ "ok": false, "error": err }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    fn make_col(name: &str, col_type: u8, length: u16, auto_number: bool) -> ColumnDef {
        let is_var = matches!(col_type, 9..=12);
        ColumnDef {
            name: name.to_string(),
            col_type_name: crate::mdb::col_type_to_name(col_type).to_string(),
            col_type,
            col_id: 0,
            col_index: 0,
            var_col_num: 0,
            fixed_off: 0,
            length,
            is_fixed: !is_var,
            auto_number,
            precision: if col_type == 16 { 18 } else { 0 },
            scale: if col_type == 16 { 4 } else { 0 },
        }
    }

    #[test]
    fn test_empty_mdb_template() {
        let data = get_empty_v2000_mdb();
        assert_eq!(data.len(), 24 * PAGE_SIZE);
        let ver = JetVersion::from_data(&data).expect("valid Jet4 header");
        assert_eq!(ver, JetVersion::Jet4);
        let sys_tables = discover_tables(&data, true).expect("system tables");
        assert!(sys_tables.contains_key("MSysObjects"));
        assert!(sys_tables.contains_key("MSysACEs"));
        let user_tables = discover_tables(&data, false).expect("user tables");
        assert!(user_tables.is_empty());
    }

    #[test]
    fn test_create_table_and_all_data_types() {
        let mut data = get_empty_v2000_mdb();
        let cols = vec![
            make_col("id", 4, 4, true),
            make_col("flag", 1, 1, false),
            make_col("bval", 2, 1, false),
            make_col("ival", 3, 2, false),
            make_col("lval", 4, 4, false),
            make_col("money_val", 5, 8, false),
            make_col("fval", 6, 4, false),
            make_col("dval", 7, 8, false),
            make_col("dt_val", 8, 8, false),
            make_col("txt_val", 10, 100, false),
            make_col("memo_val", 12, 0, false),
            make_col("ole_val", 11, 0, false),
            make_col("guid_val", 15, 16, false),
            make_col("num_val", 16, 17, false),
        ];
        let idxs = vec![IndexDef {
            name: "PrimaryKey".to_string(),
            unique: true,
            columns: vec!["id".to_string()],
        }];
        let tpage = create_table_in_data(&mut data, "AllTypes", &cols, &idxs).expect("create table");
        assert!(tpage >= 24);

        let mut row1 = Map::new();
        row1.insert("flag".to_string(), Value::Bool(true));
        row1.insert("bval".to_string(), serde_json::json!(42));
        row1.insert("ival".to_string(), serde_json::json!(-1234));
        row1.insert("lval".to_string(), serde_json::json!(987654));
        row1.insert("money_val".to_string(), serde_json::json!(123.45));
        row1.insert("fval".to_string(), serde_json::json!(3.5));
        row1.insert("dval".to_string(), serde_json::json!(2.718281828));
        row1.insert("dt_val".to_string(), serde_json::json!("2026-07-18T09:30:00"));
        row1.insert("txt_val".to_string(), serde_json::json!("Hello Jackcess Rust!"));
        row1.insert("memo_val".to_string(), serde_json::json!("Short inline memo"));
        row1.insert(
            "ole_val".to_string(),
            serde_json::json!(BASE64.encode(b"\x00\x01\x02\x03\xFE\xFF")),
        );
        row1.insert(
            "guid_val".to_string(),
            serde_json::json!("{32A69F00-7C84-11D0-AE4F-00A0C90F26F4}"),
        );
        row1.insert("num_val".to_string(), serde_json::json!("-12345.6789"));

        let ids = add_rows_to_table(&mut data, "AllTypes", &[row1], true).expect("add row");
        assert_eq!(ids, vec![Value::Number(1.into())]);

        let tdef = parse_table_ver(&data, tpage, JetVersion::Jet4).expect("parse table");
        assert_eq!(tdef.rows.len(), 1);
        let r = &tdef.rows[0];
        assert_eq!(r.get("id").and_then(|v| v.as_i64()), Some(1));
        assert_eq!(r.get("flag").and_then(|v| v.as_bool()), Some(true));
        assert_eq!(r.get("bval").and_then(|v| v.as_i64()), Some(42));
        assert_eq!(r.get("ival").and_then(|v| v.as_i64()), Some(-1234));
        assert_eq!(r.get("lval").and_then(|v| v.as_i64()), Some(987654));
        assert_eq!(
            r.get("money_val").and_then(|v| v.as_str()),
            Some("123.4500")
        );
        assert_eq!(r.get("fval").and_then(|v| v.as_f64()), Some(3.5));
        assert_eq!(
            r.get("dt_val").and_then(|v| v.as_str()),
            Some("2026-07-18T09:30:00")
        );
        assert_eq!(
            r.get("txt_val").and_then(|v| v.as_str()),
            Some("Hello Jackcess Rust!")
        );
        assert_eq!(
            r.get("memo_val").and_then(|v| v.as_str()),
            Some("Short inline memo")
        );
        assert_eq!(
            r.get("guid_val").and_then(|v| v.as_str()),
            Some("{32A69F00-7C84-11D0-AE4F-00A0C90F26F4}")
        );
        assert_eq!(
            r.get("num_val").and_then(|v| v.as_str()),
            Some("-12345.6789")
        );
    }

    #[test]
    fn test_lval_inline_single_and_multipage() {
        let mut data = get_empty_v2000_mdb();
        let cols = vec![
            make_col("id", 4, 4, true),
            make_col("notes", 12, 0, false),
            make_col("blob", 11, 0, false),
        ];
        let tpage = create_table_in_data(&mut data, "LvalTest", &cols, &[]).expect("create table");

        let inline_str = "Inline memo <= 64 bytes";
        let single_page_str = "S".repeat(1500);
        let multi_page_str = "M".repeat(12000);
        let multi_page_blob: Vec<u8> = (0..10000).map(|i| (i % 251) as u8).collect();

        let mut r1 = Map::new();
        r1.insert("notes".to_string(), serde_json::json!(inline_str));
        r1.insert("blob".to_string(), serde_json::json!(BASE64.encode(b"tiny")));

        let mut r2 = Map::new();
        r2.insert("notes".to_string(), serde_json::json!(single_page_str));
        r2.insert(
            "blob".to_string(),
            serde_json::json!(BASE64.encode(&multi_page_blob[..1200])),
        );

        let mut r3 = Map::new();
        r3.insert("notes".to_string(), serde_json::json!(multi_page_str));
        r3.insert(
            "blob".to_string(),
            serde_json::json!(BASE64.encode(&multi_page_blob)),
        );

        add_rows_to_table(&mut data, "LvalTest", &[r1, r2, r3], true).expect("add lval rows");

        let tdef = parse_table_ver(&data, tpage, JetVersion::Jet4).expect("parse lval table");
        assert_eq!(tdef.rows.len(), 3);
        assert_eq!(
            tdef.rows[0].get("notes").and_then(|v| v.as_str()),
            Some(inline_str)
        );
        assert_eq!(
            tdef.rows[1].get("notes").and_then(|v| v.as_str()),
            Some(single_page_str.as_str())
        );
        assert_eq!(
            tdef.rows[2].get("notes").and_then(|v| v.as_str()),
            Some(multi_page_str.as_str())
        );
        let decoded_blob = BASE64
            .decode(tdef.rows[2].get("blob").and_then(|v| v.as_str()).unwrap())
            .unwrap();
        assert_eq!(decoded_blob, multi_page_blob);
    }

    #[test]
    fn test_update_and_delete_rows_with_overflow() {
        let mut data = get_empty_v2000_mdb();
        let cols = vec![
            make_col("id", 4, 4, true),
            make_col("val", 10, 500, false),
        ];
        let tpage = create_table_in_data(&mut data, "MutTest", &cols, &[]).expect("create table");

        // Insert 20 rows with 200-char strings so the first data page is mostly full
        let mut rows = Vec::new();
        for i in 0..20 {
            let mut m = Map::new();
            m.insert("val".to_string(), serde_json::json!(format!("row-{}-{}", i, "x".repeat(180))));
            rows.push(m);
        }
        add_rows_to_table(&mut data, "MutTest", &rows, true).expect("insert rows");

        let tdef1 = parse_table_ver(&data, tpage, JetVersion::Jet4).expect("parse");
        assert_eq!(tdef1.rows.len(), 20);
        let (p0, r0) = tdef1.row_ids[0];

        // Update row 0 with a 250-char string (triggers overflow if page is full or in-place shift)
        let mut upd = tdef1.rows[0].clone();
        let new_val = format!("updated-{}", "Z".repeat(240));
        upd.insert("val".to_string(), serde_json::json!(new_val));
        update_row_in_table(&mut data, "MutTest", p0, r0, &upd).expect("update row 0");

        // Delete row 5
        let (p5, r5) = tdef1.row_ids[5];
        delete_row_in_table(&mut data, "MutTest", p5, r5).expect("delete row 5");

        let tdef2 = parse_table_ver(&data, tpage, JetVersion::Jet4).expect("parse after mut");
        assert_eq!(tdef2.rows.len(), 19);
        assert_eq!(tdef2.tdef_row_count, 19);
        assert_eq!(
            tdef2.rows[0].get("val").and_then(|v| v.as_str()),
            Some(new_val.as_str())
        );
        // Row with id=6 (formerly index 5) should be gone
        assert!(!tdef2
            .rows
            .iter()
            .any(|r| r.get("id").and_then(|v| v.as_i64()) == Some(6)));
    }

    #[test]
    fn test_usage_map_reference_promotion_and_multipage_tdef() {
        let mut data = get_empty_v2000_mdb();
        // Create a table with 160 columns to exercise multi-page TDEF creation
        let mut cols = Vec::with_capacity(160);
        for i in 0..160 {
            cols.push(make_col(&format!("Column_{:03}", i), 4, 4, i == 0));
        }
        let tpage = create_table_in_data(&mut data, "WideTable", &cols, &[]).expect("wide table");
        let mut row = Map::new();
        row.insert("Column_001".to_string(), serde_json::json!(12345));
        row.insert("Column_159".to_string(), serde_json::json!(67890));
        add_rows_to_table(&mut data, "WideTable", &[row], true).expect("insert wide row");

        let tdef = parse_table_ver(&data, tpage, JetVersion::Jet4).expect("parse wide table");
        assert_eq!(tdef.columns.len(), 160);
        assert_eq!(tdef.rows.len(), 1);
        assert_eq!(
            tdef.rows[0].get("Column_159").and_then(|v| v.as_i64()),
            Some(67890)
        );

        // Allocate > 520 pages to trigger global usage map promotion from inline (0x00) to reference (0x01)
        for _ in 0..530 {
            allocate_page(&mut data);
        }
        assert!(data.len() / PAGE_SIZE > 550);
    }

    #[test]
    fn test_upstream_jackcess_mdb_files() {
        let upstream_dir = Path::new("/tmp/jackcess-upstream/src/test/data");
        if !upstream_dir.exists() {
            return;
        }
        let mut count = 0;
        for ver_dir in &["V1997", "V2000", "V2003", "V2007", "V2010"] {
            let dir = upstream_dir.join(ver_dir);
            if !dir.exists() {
                continue;
            }
            for entry in fs::read_dir(&dir).unwrap().flatten() {
                let path = entry.path();
                let ext = path.extension().and_then(|e| e.to_str()).unwrap_or("");
                if ext != "mdb" && ext != "accdb" {
                    continue;
                }
                let data = fs::read(&path).unwrap();
                let ver = JetVersion::from_data(&data).expect("valid Jet/ACE version");
                let tables = discover_tables(&data, false)
                    .unwrap_or_else(|e| panic!("discover_tables failed on {:?}: {}", path, e));
                for (tname, tpage) in tables {
                    let _tdef = parse_table_ver(&data, tpage, ver).unwrap_or_else(|e| {
                        panic!("parse_table_ver failed on {:?} table {}: {}", path, tname, e)
                    });
                }
                count += 1;
            }
        }
        assert!(count >= 30, "Expected at least 30 upstream test databases, parsed {}", count);
    }
}


