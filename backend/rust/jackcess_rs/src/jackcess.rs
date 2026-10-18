use crate::empty_mdb::get_empty_v2000_mdb;
use crate::mdb::{
    decode_jet_text, decode_utf16le, discover_tables, find_row_end, name_to_col_type,
    parse_table_ver, read_f32_le, read_f64_le, read_i16_le, read_i32_le, read_i64_le, read_u16_le,
    read_u32_le, read_usage_map_ver, ColumnDef, IndexDef, JetVersion, TableDef,
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

const GENLEG_CODES: [&str; 256] = [
    "X", "U3", "U4", "U5", "U6", "U7", "U8", "U9", "UA", "S803", "S804", "S805", "S806", "S807",
    "UB", "UC", "UD", "UE", "UF", "U10", "U11", "U12", "U13", "U14", "U15", "U16", "U17", "U18",
    "U19", "U1A", "U1B", "U1C", "S7", "S9", "SA", "SC", "SE", "S10", "S12", "U80", "S14", "S16",
    "S18", "S2C", "S1A", "U82", "S1C", "S1E", "S36", "S38", "S3A", "S3C", "S3E", "S40", "S42",
    "S44", "S46", "S48", "S20", "S22", "S2E", "S30", "S32", "S24", "S26", "S4A", "S4C", "S4D",
    "S4F", "S51", "S53", "S55", "S57", "S59", "S5B", "S5C", "S5E", "S60", "S62", "S64", "S66",
    "S68", "S69", "S6B", "S6D", "S6F", "S71", "S73", "S75", "S76", "S78", "S27", "S29", "S2A",
    "S2B02", "S2B03", "S2B07", "S4A", "S4C", "S4D", "S4F", "S51", "S53", "S55", "S57", "S59",
    "S5B", "S5C", "S5E", "S60", "S62", "S64", "S66", "S68", "S69", "S6B", "S6D", "S6F", "S71",
    "S73", "S75", "S76", "S78", "S2B09", "S2B0B", "S2B0D", "S2B0F", "U1D", "U1E", "U1F", "U20",
    "U21", "U22", "U23", "U24", "U25", "U26", "U27", "U28", "U29", "U2A", "U2B", "U2C", "U2D",
    "U2E", "U2F", "U30", "U31", "U32", "U33", "U34", "U35", "U36", "U37", "U38", "U39", "U3A",
    "U3B", "U3C", "U3D", "S802", "S2B10", "S34A6", "S34A7", "S34A8", "S34A9", "S2B11", "S34AA",
    "S2B12", "S34AB", "I4A,3", "S3305", "S34AC", "U83", "S34AD", "S2B13", "S34AE", "S3304", "S3A",
    "S3C", "S2B14", "S34AF", "S34B0", "S34B1", "S2B15", "S38", "I64,3", "S3307", "S3712", "S3716",
    "S371A", "S2B16", "I4A,F", "I4A,E", "I4A,12", "I4A,19", "I4A,13", "I4A,1A", "S4A51",
    "I4D,1C", "I51,F", "I51,E", "I51,12", "I51,13", "I59,F", "I59,E", "I59,12", "I59,13",
    "I4F,68", "I62,19", "I64,F", "I64,E", "I64,12", "I64,19", "I64,13", "S3309", "I64,21",
    "I6F,F", "I6F,E", "I6F,12", "I6F,13", "I76,E", "S6D57", "S6B6B", "I4A,F", "I4A,E", "I4A,12",
    "I4A,19", "I4A,13", "I4A,1A", "S4A51", "I4D,1C", "I51,F", "I51,E", "I51,12", "I51,13",
    "I59,F", "I59,E", "I59,12", "I59,13", "I4F,68", "I62,19", "I64,F", "I64,E", "I64,12",
    "I64,19", "I64,13", "S330A", "I64,21", "I6F,F", "I6F,E", "I6F,12", "I6F,13", "I76,E",
    "S6D57", "I76,13",
];

fn parse_code_hex_bytes(hex_str: &str) -> Vec<u8> {
    if hex_str.is_empty() {
        return Vec::new();
    }
    let padded = if hex_str.len() % 2 != 0 {
        format!("0{}", hex_str)
    } else {
        hex_str.to_string()
    };
    let mut out = Vec::with_capacity(padded.len() / 2);
    for i in 0..(padded.len() / 2) {
        if let Ok(b) = u8::from_str_radix(&padded[i * 2..i * 2 + 2], 16) {
            out.push(b);
        }
    }
    out
}

fn write_genleg_text_key(text: &str, is_asc: bool, out: &mut Vec<u8>) {
    let mut chars: Vec<char> = text.chars().take(255).collect();
    while chars.last() == Some(&' ') {
        chars.pop();
    }
    let prev_len = out.len();
    let mut extra_codes: Vec<u8> = Vec::new();
    let mut extra_num_chars: usize = 0;
    let mut unprintable_codes: Vec<u8> = Vec::new();
    let mut char_offset: usize = 0;

    for ch in chars {
        let code_idx = ch as u32;
        let spec = if code_idx <= 0xFF {
            GENLEG_CODES[code_idx as usize]
        } else if (0xD800..=0xDFFF).contains(&code_idx) {
            "X"
        } else {
            "S4A"
        };
        if spec == "X" || spec.is_empty() {
            continue;
        }
        let prefix = spec.as_bytes()[0];
        let suffix = &spec[1..];
        let cur_char_offset = char_offset;
        match prefix {
            b'S' | b'G' => {
                let ib = parse_code_hex_bytes(suffix);
                if !ib.is_empty() {
                    out.extend_from_slice(&ib);
                    char_offset += 1;
                }
            }
            b'I' => {
                let mut parts = suffix.splitn(2, ',');
                let ib = parse_code_hex_bytes(parts.next().unwrap_or(""));
                let eb = parse_code_hex_bytes(parts.next().unwrap_or(""));
                if !ib.is_empty() {
                    out.extend_from_slice(&ib);
                    char_offset += 1;
                }
                if !eb.is_empty() {
                    if extra_num_chars < cur_char_offset {
                        let fill = cur_char_offset - extra_num_chars;
                        extra_codes.resize(extra_codes.len() + fill, 0x02);
                        extra_num_chars += fill;
                    }
                    extra_codes.extend_from_slice(&eb);
                    extra_num_chars += 1;
                }
            }
            b'U' => {
                let ub = parse_code_hex_bytes(suffix);
                if !ub.is_empty() {
                    let unprint_char_offset = if !extra_codes.is_empty() {
                        extra_codes.len() + cur_char_offset.saturating_sub(extra_num_chars)
                    } else {
                        cur_char_offset
                    };
                    let offset_val = ((7 + 4 * unprint_char_offset) as u16) | 0x8000;
                    unprintable_codes.extend_from_slice(&offset_val.to_be_bytes());
                    unprintable_codes.push(0x06);
                    unprintable_codes.extend_from_slice(&ub);
                }
            }
            _ => {}
        }
    }

    out.push(0x01); // END_TEXT

    while let Some(&last_b) = extra_codes.last() {
        if last_b <= 0x02 {
            extra_codes.pop();
        } else {
            break;
        }
    }
    let has_extra = !extra_codes.is_empty();
    let has_unprint = !unprintable_codes.is_empty();
    if has_extra || has_unprint {
        if has_extra {
            out.extend_from_slice(&extra_codes);
        }
        if has_unprint {
            out.extend_from_slice(&[0x01, 0x01, 0x01]);
            out.extend_from_slice(&unprintable_codes);
        }
    }

    if !is_asc {
        out.push(0x00);
        for b in &mut out[prev_len..] {
            *b = !*b;
        }
    }
    out.push(0x00); // END_EXTRA_TEXT
}

fn genleg_ascii_sort_bytes(name: &str) -> Vec<u8> {
    let mut out = Vec::with_capacity(name.len() + 4);
    out.push(0x7F);
    write_genleg_text_key(name, true, &mut out);
    out
}

fn write_general_binary_entry(raw: &[u8], is_asc: bool, out: &mut Vec<u8>) {
    if raw.is_empty() {
        return;
    }
    let mut pos = 0usize;
    while pos + 8 < raw.len() {
        let mut partial = [0u8; 9];
        partial[0..8].copy_from_slice(&raw[pos..pos + 8]);
        if !is_asc {
            for b in &mut partial[0..8] {
                *b = !*b;
            }
        }
        partial[8] = 0x09;
        out.extend_from_slice(&partial);
        pos += 8;
    }
    let seg_len = raw.len() - pos;
    let mut partial = [0u8; 9];
    partial[0..seg_len].copy_from_slice(&raw[pos..]);
    partial[8] = seg_len as u8;
    if !is_asc {
        for b in &mut partial[0..9] {
            *b = !*b;
        }
    }
    out.extend_from_slice(&partial);
}

fn encode_guid_be_16(v: &Value) -> [u8; 16] {
    let mut out = [0u8; 16];
    let s = v.as_str().unwrap_or("").trim().trim_matches(|c| c == '{' || c == '}');
    let hex: String = s.chars().filter(|c| c.is_ascii_hexdigit()).collect();
    if hex.len() == 32 {
        for i in 0..16 {
            out[i] = u8::from_str_radix(&hex[i * 2..i * 2 + 2], 16).unwrap_or(0);
        }
    }
    out
}

fn encode_numeric_index_17(v: &Value, scale: u8, is_asc: bool) -> [u8; 17] {
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
    let is_neg = neg && unscaled > 0;
    out[0] = if is_neg { 0x80 } else { 0x00 };
    out[1..17].copy_from_slice(&unscaled.to_be_bytes());
    if is_neg == is_asc {
        for b in &mut out {
            *b = !*b;
        }
    }
    out[0] = if is_neg { 0x00 } else { 0xFF };
    out
}

fn truncate_index_key_bytes(key_bytes: Vec<u8>) -> Vec<u8> {
    if key_bytes.len() <= 510 {
        return key_bytes;
    }
    let mut crc_table = [0u16; 256];
    for i in 0..256 {
        let mut r = (i as u16) << 8;
        for _ in 0..8 {
            if (r & 0x8000) != 0 {
                r = (r << 1) ^ 0x8005;
            } else {
                r <<= 1;
            }
        }
        crc_table[i] = r;
    }
    let mut digest: u16 = 0;
    for &b in &key_bytes[508..key_bytes.len() - 1] {
        digest = (digest >> 8) ^ crc_table[(digest & 0xFF) as usize] ^ (b as u16);
    }
    let mut truncated = key_bytes[..508].to_vec();
    truncated.push((digest >> 8) as u8);
    truncated.push((digest & 0xFF) as u8);
    truncated
}

fn encode_index_column_key(col: &ColumnDef, val_opt: Option<&Value>, is_asc: bool, out: &mut Vec<u8>) -> bool {
    if col.col_type == 1 {
        // BOOLEAN is never null in Access
        let b = val_opt.map(value_to_bool).unwrap_or(false);
        out.push(if is_asc { 0x7F } else { 0x80 });
        out.push(if b {
            if is_asc { 0x00 } else { 0xFF }
        } else if is_asc {
            0xFF
        } else {
            0x00
        });
        return false;
    }
    let val = match val_opt {
        Some(v) if !v.is_null() => v,
        _ => {
            out.push(if is_asc { 0x00 } else { 0xFF });
            return true;
        }
    };
    out.push(if is_asc { 0x7F } else { 0x80 });
    match col.col_type {
        2 => {
            let b = value_to_i64(val).unwrap_or(0) as u8;
            out.push(if is_asc { b } else { !b });
        }
        3 => {
            let mut b = (value_to_i64(val).unwrap_or(0) as i16).to_be_bytes();
            b[0] ^= 0x80;
            if !is_asc {
                for x in &mut b {
                    *x = !*x;
                }
            }
            out.extend_from_slice(&b);
        }
        4 | 18 => {
            let mut b = (value_to_i64(val).unwrap_or(0) as i32).to_be_bytes();
            b[0] ^= 0x80;
            if !is_asc {
                for x in &mut b {
                    *x = !*x;
                }
            }
            out.extend_from_slice(&b);
        }
        5 | 19 => {
            let v = if col.col_type == 5 {
                encode_money_i64(val)
            } else {
                value_to_i64(val).unwrap_or(0)
            };
            let mut b = v.to_be_bytes();
            b[0] ^= 0x80;
            if !is_asc {
                for x in &mut b {
                    *x = !*x;
                }
            }
            out.extend_from_slice(&b);
        }
        6 => {
            let mut f = value_to_f64(val).unwrap_or(0.0) as f32;
            if f == 0.0 {
                f = 0.0;
            }
            let mut b = f.to_be_bytes();
            let is_neg = (b[0] & 0x80) != 0;
            if !is_neg {
                b[0] ^= 0x80;
            }
            if is_neg == is_asc {
                for x in &mut b {
                    *x = !*x;
                }
            }
            out.extend_from_slice(&b);
        }
        7 | 8 => {
            let mut f = if col.col_type == 8 {
                value_to_access_date_f64(val).unwrap_or(0.0)
            } else {
                value_to_f64(val).unwrap_or(0.0)
            };
            if f == 0.0 {
                f = 0.0;
            }
            let mut b = f.to_be_bytes();
            let is_neg = (b[0] & 0x80) != 0;
            if !is_neg {
                b[0] ^= 0x80;
            }
            if is_neg == is_asc {
                for x in &mut b {
                    *x = !*x;
                }
            }
            out.extend_from_slice(&b);
        }
        9 | 11 => {
            let raw = val
                .as_str()
                .and_then(|s| BASE64.decode(s).ok())
                .unwrap_or_default();
            write_general_binary_entry(&raw, is_asc, out);
        }
        10 | 12 => {
            let s_cow = match val {
                Value::String(s) => s.clone(),
                Value::Number(n) => n.to_string(),
                Value::Bool(b) => b.to_string(),
                _ => String::new(),
            };
            write_genleg_text_key(&s_cow, is_asc, out);
        }
        15 => {
            let raw = encode_guid_be_16(val);
            write_general_binary_entry(&raw, is_asc, out);
        }
        16 => {
            let b = encode_numeric_index_17(val, col.scale, is_asc);
            out.extend_from_slice(&b);
        }
        _ => {}
    }
    false
}

fn encode_index_row_key(
    tdef: &TableDef,
    real_idx: & crate::mdb::RealIndexDef,
    row_map: &Map<String, Value>,
) -> (Vec<u8>, usize, bool) {
    let mut lower_lookup: HashMap<String, &Value> = HashMap::with_capacity(row_map.len());
    for (k, v) in row_map {
        lower_lookup.insert(k.to_lowercase(), v);
    }
    let mut key_bytes = Vec::with_capacity(real_idx.columns.len() * 12);
    let mut null_count = 0usize;
    for (col_name, col_id, is_asc) in &real_idx.columns {
        if let Some(col_def) = tdef.columns.iter().find(|c| c.col_id == *col_id) {
            let val_opt = row_map
                .get(col_name)
                .or_else(|| lower_lookup.get(&col_name.to_lowercase()).copied());
            if encode_index_column_key(col_def, val_opt, *is_asc, &mut key_bytes) {
                null_count += 1;
            }
        }
    }
    let all_null = !real_idx.columns.is_empty() && null_count == real_idx.columns.len();
    (truncate_index_key_bytes(key_bytes), null_count, all_null)
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct BTreeEntry {
    key_bytes: Vec<u8>,
    page_num: u32,
    row_num: u8,
}

impl PartialOrd for BTreeEntry {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for BTreeEntry {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.key_bytes
            .cmp(&other.key_bytes)
            .then_with(|| self.page_num.cmp(&other.page_num))
            .then_with(|| self.row_num.cmp(&other.row_num))
    }
}

fn read_index_btree_entries(data: &[u8], root_page: usize) -> Vec<BTreeEntry> {
    let mut out = Vec::new();
    let mut visited = Vec::new();
    collect_btree_leaf_entries(data, root_page, &mut out, &mut visited);
    out.sort();
    out
}

fn collect_btree_leaf_entries(
    data: &[u8],
    page_num: usize,
    out: &mut Vec<BTreeEntry>,
    visited: &mut Vec<usize>,
) {
    if page_num == 0 || (page_num + 1) * PAGE_SIZE > data.len() || visited.contains(&page_num) {
        return;
    }
    visited.push(page_num);
    let pg = &data[page_num * PAGE_SIZE..(page_num + 1) * PAGE_SIZE];
    let ptype = pg[0];
    if ptype != 0x03 && ptype != 0x04 {
        return;
    }
    let is_leaf = ptype == 0x04;
    let prefix_len = read_u16_le(pg, 24) as usize;
    let mask = &pg[27..480];
    let mut ends = Vec::new();
    for bit_idx in 0..(453 * 8) {
        if (mask[bit_idx / 8] & (1 << (bit_idx % 8))) != 0 {
            ends.push(bit_idx);
        }
    }
    let mut last_start = 0usize;
    let mut prefix: Vec<u8> = Vec::new();
    let mut first = true;
    for end in ends {
        if end < last_start || 480 + end > PAGE_SIZE {
            break;
        }
        let slice = &pg[480 + last_start..480 + end];
        let full = if first {
            first = false;
            if prefix_len <= slice.len() {
                prefix = slice[..prefix_len].to_vec();
            }
            slice.to_vec()
        } else {
            let mut v = Vec::with_capacity(prefix.len() + slice.len());
            v.extend_from_slice(&prefix);
            v.extend_from_slice(slice);
            v
        };
        last_start = end;
        if is_leaf {
            if full.len() >= 4 {
                let klen = full.len() - 4;
                let pnum = u32::from_be_bytes([0, full[klen], full[klen + 1], full[klen + 2]]);
                let rnum = full[klen + 3];
                out.push(BTreeEntry {
                    key_bytes: full[..klen].to_vec(),
                    page_num: pnum,
                    row_num: rnum,
                });
            }
        } else if full.len() >= 8 {
            let n = full.len();
            let sub_page =
                u32::from_be_bytes([full[n - 4], full[n - 3], full[n - 2], full[n - 1]]) as usize;
            collect_btree_leaf_entries(data, sub_page, out, visited);
        }
    }
    if !is_leaf {
        let child_tail = read_u32_le(pg, 20) as usize;
        if child_tail != 0 {
            collect_btree_leaf_entries(data, child_tail, out, visited);
        }
    }
}

fn write_btree_page(
    data: &mut [u8],
    page_num: usize,
    tdef_page: usize,
    is_leaf: bool,
    level: u8,
    prev_page: u32,
    next_page: u32,
    child_tail_page: u32,
    entries: &[(BTreeEntry, Option<u32>)],
) -> bool {
    let suffix_len = if is_leaf { 4usize } else { 8usize };
    let uncomp_total: usize = entries
        .iter()
        .map(|(e, _)| e.key_bytes.len() + suffix_len)
        .sum();
    let mut prefix: Vec<u8> = Vec::new();
    if uncomp_total > 3616 && entries.len() > 1 {
        let first_k = &entries[0].0.key_bytes;
        let last_k = &entries[entries.len() - 1].0.key_bytes;
        let mlen = first_k.len().min(last_k.len());
        let mut plen = 0usize;
        while plen < mlen && first_k[plen] == last_k[plen] {
            plen += 1;
        }
        prefix = first_k[..plen].to_vec();
    }
    let comp_total = if entries.is_empty() {
        0
    } else {
        uncomp_total - prefix.len() * (entries.len() - 1)
    };
    if comp_total > 3616 {
        return false;
    }

    let ip_off = page_num * PAGE_SIZE;
    for b in &mut data[ip_off..ip_off + PAGE_SIZE] {
        *b = 0;
    }
    data[ip_off] = if is_leaf { 0x04 } else { 0x03 };
    data[ip_off + 1] = 0x01;
    write_u16_le(data, ip_off + 2, (3616 - comp_total) as u16);
    write_u32_le(data, ip_off + 4, tdef_page as u32);
    write_u32_le(data, ip_off + 12, prev_page);
    write_u32_le(data, ip_off + 16, next_page);
    write_u32_le(data, ip_off + 20, child_tail_page);
    write_u16_le(data, ip_off + 24, prefix.len() as u16);
    data[ip_off + 26] = level;

    if !entries.is_empty() {
        let mut pos = 0usize;
        data[ip_off + 480..ip_off + 480 + prefix.len()].copy_from_slice(&prefix);
        pos += prefix.len();
        for (e, sub_opt) in entries {
            let k_rem = &e.key_bytes[prefix.len()..];
            data[ip_off + 480 + pos..ip_off + 480 + pos + k_rem.len()].copy_from_slice(k_rem);
            pos += k_rem.len();
            let p_be = e.page_num.to_be_bytes();
            data[ip_off + 480 + pos] = p_be[1];
            data[ip_off + 480 + pos + 1] = p_be[2];
            data[ip_off + 480 + pos + 2] = p_be[3];
            data[ip_off + 480 + pos + 3] = e.row_num;
            pos += 4;
            if let Some(sub_p) = sub_opt {
                data[ip_off + 480 + pos..ip_off + 480 + pos + 4]
                    .copy_from_slice(&sub_p.to_be_bytes());
                pos += 4;
            }
            data[ip_off + 27 + (pos / 8)] |= 1 << (pos % 8);
        }
    }
    true
}

fn write_index_btree_entries(
    data: &mut Vec<u8>,
    tdef_page: usize,
    real_idx: &crate::mdb::RealIndexDef,
    sorted_entries: &[BTreeEntry],
) {
    let root_page = real_idx.root_page as usize;
    if root_page == 0 || (root_page + 1) * PAGE_SIZE > data.len() {
        return;
    }
    let leaf_items: Vec<(BTreeEntry, Option<u32>)> =
        sorted_entries.iter().cloned().map(|e| (e, None)).collect();
    if write_btree_page(data, root_page, tdef_page, true, 0, 0, 0, 0, &leaf_items) {
        return;
    }

    // Split into multiple leaf pages and convert root_page into a Node Page (0x03)
    let uptr = (real_idx.umap_page << 8) | (real_idx.umap_row as u32);
    let mut existing_owned = read_usage_map_ver(data, uptr, JetVersion::Jet4);
    existing_owned.retain(|&p| p != root_page);

    let mut chunks: Vec<Vec<(BTreeEntry, Option<u32>)>> = Vec::new();
    let mut cur_chunk: Vec<(BTreeEntry, Option<u32>)> = Vec::new();
    let mut cur_size = 0usize;
    for item in leaf_items {
        let esize = item.0.key_bytes.len() + 4;
        if !cur_chunk.is_empty() && cur_size + esize > 3000 {
            chunks.push(cur_chunk);
            cur_chunk = Vec::new();
            cur_size = 0;
        }
        cur_size += esize;
        cur_chunk.push(item);
    }
    if !cur_chunk.is_empty() {
        chunks.push(cur_chunk);
    }

    let num_leaves = chunks.len();
    let mut leaf_pages = Vec::with_capacity(num_leaves);
    for i in 0..num_leaves {
        let lp = if i < existing_owned.len() {
            existing_owned[i]
        } else {
            let np = allocate_page(data);
            if real_idx.umap_page != 0 {
                set_usage_map_bit(data, uptr, np, true);
            }
            np
        };
        leaf_pages.push(lp);
    }

    let mut node_items: Vec<(BTreeEntry, Option<u32>)> = Vec::with_capacity(num_leaves);
    for (i, chunk) in chunks.iter().enumerate() {
        let prev_p = if i > 0 { leaf_pages[i - 1] as u32 } else { 0 };
        let next_p = if i + 1 < num_leaves {
            leaf_pages[i + 1] as u32
        } else {
            0
        };
        write_btree_page(
            data,
            leaf_pages[i],
            tdef_page,
            true,
            0,
            prev_p,
            next_p,
            0,
            chunk,
        );
        let last_e = chunk.last().unwrap().0.clone();
        node_items.push((last_e, Some(leaf_pages[i] as u32)));
    }

    // Promote last leaf child to childTailPageNumber on root node page (matching Jackcess promoteTail)
    let tail_page = if node_items.len() > 1 {
        node_items.pop().and_then(|(_, sp)| sp).unwrap_or(0)
    } else {
        0
    };
    let _ = write_btree_page(
        data,
        root_page,
        tdef_page,
        false,
        1,
        0,
        0,
        tail_page,
        &node_items,
    );
}

fn insert_uncompressed_index_leaf_entry(
    data: &mut [u8],
    idx_page: usize,
    entry_bytes: &[u8],
) -> bool {
    if entry_bytes.len() < 4 {
        return false;
    }
    let klen = entry_bytes.len() - 4;
    let pnum = u32::from_be_bytes([
        0,
        entry_bytes[klen],
        entry_bytes[klen + 1],
        entry_bytes[klen + 2],
    ]);
    let rnum = entry_bytes[klen + 3];
    let new_entry = BTreeEntry {
        key_bytes: entry_bytes[..klen].to_vec(),
        page_num: pnum,
        row_num: rnum,
    };
    let ip_off = idx_page * PAGE_SIZE;
    if data[ip_off] != 0x04 {
        return false;
    }
    let tdef_page = read_u32_le(data, ip_off + 4) as usize;
    let mut entries = read_index_btree_entries(data, idx_page);
    entries.push(new_entry);
    entries.sort();
    let items: Vec<(BTreeEntry, Option<u32>)> = entries.into_iter().map(|e| (e, None)).collect();
    write_btree_page(data, idx_page, tdef_page, true, 0, 0, 0, 0, &items)
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

    let col_id_by_lower_name: HashMap<String, u16> = cols
        .iter()
        .map(|c| (c.name.to_lowercase(), c.col_id as u16))
        .collect();

    let valid_indexes: Vec<&IndexDef> = indexes
        .iter()
        .filter(|ix| !ix.name.starts_with('.'))
        .collect();
    let log_idx_count = valid_indexes.len();

    // Deduplicate physical IndexData states (matching Jackcess TableCreator.findIndexDataState)
    struct PhysIdxSpec {
        cols: Vec<(u16, u8)>, // (col_id, col_flags: 0x01=ASC, 0x00=DESC)
        flags: u8,
    }
    let mut phys_indexes: Vec<PhysIdxSpec> = Vec::with_capacity(log_idx_count);
    let mut log_to_phys: Vec<usize> = Vec::with_capacity(log_idx_count);

    for ix in &valid_indexes {
        let is_pk = ix.primary_key || ix.name.eq_ignore_ascii_case("PrimaryKey");
        let mut flags = 0x80u8; // UNKNOWN_INDEX_FLAG always set in Jet 4
        if ix.unique || is_pk {
            flags |= 0x01;
        }
        if ix.ignore_nulls {
            flags |= 0x02;
        }
        if ix.required || is_pk {
            flags |= 0x08;
        }
        let mut pcols = Vec::with_capacity(ix.columns.len().min(10));
        for (s, cname) in ix.columns.iter().take(10).enumerate() {
            let cid = col_id_by_lower_name
                .get(&cname.to_lowercase())
                .copied()
                .unwrap_or(0xFFFF);
            let asc = ix.column_orders.get(s).copied().unwrap_or(true);
            pcols.push((cid, if asc { 0x01u8 } else { 0x00u8 }));
        }
        if let Some(existing_idx) = phys_indexes
            .iter()
            .position(|p| p.flags == flags && p.cols == pcols)
        {
            log_to_phys.push(existing_idx);
        } else {
            let new_idx = phys_indexes.len();
            phys_indexes.push(PhysIdxSpec { cols: pcols, flags });
            log_to_phys.push(new_idx);
        }
    }
    let real_idx_count = phys_indexes.len();

    let tdef_page = allocate_page(data);
    let umap_page = allocate_page(data);

    let mut idx_root_pages = Vec::with_capacity(real_idx_count);
    for _ in 0..real_idx_count {
        let ipage = allocate_page(data);
        let ip_off = ipage * PAGE_SIZE;
        data[ip_off] = 0x04;
        data[ip_off + 1] = 0x01;
        write_u16_le(data, ip_off + 2, (PAGE_SIZE - 480) as u16);
        write_u32_le(data, ip_off + 4, tdef_page as u32);
        idx_root_pages.push(ipage);
    }

    // Initialize umap_page rows (Row 0 = owned pages, Row 1 = free space, Rows 2.. = index + LVAL umaps)
    let total_umap_rows = 2 + real_idx_count + lval_col_ids.len() * 2;
    {
        let up_off = umap_page * PAGE_SIZE;
        data[up_off] = 0x01;
        data[up_off + 1] = 0x01;
        write_u16_le(data, up_off + 2, 4082);
        write_u32_le(data, up_off + 4, 0);
        write_u16_le(data, up_off + 12, 0);
        let empty_inline_umap = [0u8; 69];
        for r in 0..total_umap_rows {
            append_row_to_data_page(data, umap_page, &empty_inline_umap, false);
            if r >= 2 && r < 2 + real_idx_count {
                let ipage = idx_root_pages[r - 2];
                let uptr = ((umap_page as u32) << 8) | (r as u32);
                set_usage_map_bit(data, uptr, ipage, true);
            }
        }
    }

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
    write_u32_le(&mut tdef_buf, 47, log_idx_count as u32);
    write_u32_le(&mut tdef_buf, 51, real_idx_count as u32);
    let owned_ptr = ((umap_page as u32) << 8) | 0;
    let free_ptr = ((umap_page as u32) << 8) | 1;
    write_u32_le(&mut tdef_buf, 55, owned_ptr);
    write_u32_le(&mut tdef_buf, 59, free_ptr);

    // 1. Physical index row-count definitions (12 bytes * real_idx_count)
    tdef_buf.resize(tdef_buf.len() + real_idx_count * 12, 0);

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

    // 4. Physical index column blocks (52 bytes * real_idx_count)
    for (i, pix) in phys_indexes.iter().enumerate() {
        let mut ib = [0u8; 52];
        write_u32_le(&mut ib, 0, 1923);
        for s in 0..10 {
            let off = 4 + s * 3;
            if let Some(&(cid, cflag)) = pix.cols.get(s) {
                write_u16_le(&mut ib, off, cid);
                ib[off + 2] = cflag;
            } else {
                write_u16_le(&mut ib, off, 0xFFFF);
                ib[off + 2] = 0x00;
            }
        }
        let idx_umap_row = (2 + i) as u8;
        let idx_uptr = ((umap_page as u32) << 8) | (idx_umap_row as u32);
        write_u32_le(&mut ib, 34, idx_uptr);
        write_u32_le(&mut ib, 38, idx_root_pages[i] as u32);
        ib[46] = pix.flags;
        tdef_buf.extend_from_slice(&ib);
    }

    // 5. Logical index info blocks (28 bytes * log_idx_count)
    for (i, ix) in valid_indexes.iter().enumerate() {
        let mut lb = [0u8; 28];
        write_u32_le(&mut lb, 0, 1625); // MAGIC_TABLE_NUMBER
        write_u32_le(&mut lb, 4, i as u32);
        write_u32_le(&mut lb, 8, log_to_phys[i] as u32);
        write_i32_le(&mut lb, 13, -1); // relIndexNumber = -1 for non-FK
        let is_pk = ix.primary_key || ix.name.eq_ignore_ascii_case("PrimaryKey");
        lb[23] = if is_pk {
            0x01
        } else if ix.foreign_key {
            0x02
        } else {
            0x00
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
        let r_owned = (2 + real_idx_count + li * 2) as u32;
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
    add_rows_to_table_ex(data, table_name, rows, allow_autonum, true)
}

pub fn add_rows_to_table_ex(
    data: &mut Vec<u8>,
    table_name: &str,
    rows: &[Map<String, Value>],
    allow_autonum: bool,
    enforce_constraints: bool,
) -> Result<Vec<i64>, String> {
    let tdef_page = find_table_page(data, table_name)?;
    let tdef = parse_table_ver(data, tdef_page, JetVersion::Jet4)?;
    let auto_col = tdef.columns.iter().find(|c| c.auto_number).cloned();
    let mut cur_auto = tdef.next_auto_number as i64;
    let mut cur_row_count = tdef.tdef_row_count;
    let mut assigned_ids = Vec::with_capacity(rows.len());

    // Load current B-Tree entries for each physical index on the table
    let mut index_trees: Vec<Vec<BTreeEntry>> = tdef
        .real_indexes
        .iter()
        .map(|ri| read_index_btree_entries(data, ri.root_page as usize))
        .collect();
    let mut unique_counts: Vec<u32> = tdef
        .real_indexes
        .iter()
        .map(|ri| ri.unique_entry_count)
        .collect();

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

        // Pre-validate index constraints before mutating page data
        let mut row_idx_keys: Vec<Option<Vec<u8>>> = Vec::with_capacity(tdef.real_indexes.len());
        for (ri_pos, ri) in tdef.real_indexes.iter().enumerate() {
            let (kbytes, null_cnt, all_null) = encode_index_row_key(&tdef, ri, &row_copy);
            if enforce_constraints && ri.required && null_cnt > 0 {
                return Err(format!(
                    "ConstraintViolationException: Null value in required index on table '{}'",
                    table_name
                ));
            }
            if ri.ignore_nulls && all_null {
                row_idx_keys.push(None);
                continue;
            }
            if ri.unique && !all_null {
                let is_dup = index_trees[ri_pos].iter().any(|e| e.key_bytes == kbytes);
                if is_dup {
                    if enforce_constraints {
                        return Err(format!(
                            "ConstraintViolationException: Duplicate key in unique index on table '{}'",
                            table_name
                        ));
                    } else {
                        row_idx_keys.push(None);
                        continue;
                    }
                }
            }
            row_idx_keys.push(Some(kbytes));
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
        let rnum = append_row_to_data_page(data, dpage, &row_bytes, false);

        for (ri_pos, kopt) in row_idx_keys.into_iter().enumerate() {
            if let Some(kbytes) = kopt {
                let existed = index_trees[ri_pos].iter().any(|e| e.key_bytes == kbytes);
                if !existed {
                    unique_counts[ri_pos] = unique_counts[ri_pos].saturating_add(1);
                }
                index_trees[ri_pos].push(BTreeEntry {
                    key_bytes: kbytes,
                    page_num: dpage as u32,
                    row_num: rnum as u8,
                });
                index_trees[ri_pos].sort();
            }
        }

        cur_row_count += 1;
        assigned_ids.push(assigned);
    }

    // Write updated B-Tree index pages and uniqueEntryCounts
    let tp_off = tdef_page * PAGE_SIZE;
    for (ri_pos, ri) in tdef.real_indexes.iter().enumerate() {
        write_index_btree_entries(data, tdef_page, ri, &index_trees[ri_pos]);
        if 63 + ri.index_data_num * 12 + 8 <= PAGE_SIZE {
            write_u32_le(
                data,
                tp_off + 63 + ri.index_data_num * 12 + 4,
                unique_counts[ri_pos],
            );
        }
    }

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

    // Validate index constraints and prepare updated B-Tree entries
    let mut updated_trees: Vec<Vec<BTreeEntry>> = Vec::with_capacity(tdef.real_indexes.len());
    for ri in &tdef.real_indexes {
        let mut tree = read_index_btree_entries(data, ri.root_page as usize);
        tree.retain(|e| !(e.page_num == page_num as u32 && e.row_num == row_num as u8));
        let (kbytes, null_cnt, all_null) = encode_index_row_key(&tdef, ri, updated_row);
        if ri.required && null_cnt > 0 {
            return Err(format!(
                "ConstraintViolationException: Null value in required index on table '{}'",
                table_name
            ));
        }
        if !(ri.ignore_nulls && all_null) {
            if ri.unique && !all_null && tree.iter().any(|e| e.key_bytes == kbytes) {
                return Err(format!(
                    "ConstraintViolationException: Duplicate key in unique index on table '{}'",
                    table_name
                ));
            }
            tree.push(BTreeEntry {
                key_bytes: kbytes,
                page_num: page_num as u32,
                row_num: row_num as u8,
            });
            tree.sort();
        }
        updated_trees.push(tree);
    }

    let new_row_bytes = encode_row_jet4(data, &tdef, updated_row);
    replace_or_overflow_row_on_page(
        data,
        tdef_page,
        tdef.owned_pages_ptr,
        tdef.free_space_ptr,
        page_num,
        row_num,
        &new_row_bytes,
    )?;

    for (ri_pos, ri) in tdef.real_indexes.iter().enumerate() {
        write_index_btree_entries(data, tdef_page, ri, &updated_trees[ri_pos]);
    }
    Ok(())
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
        let target_page = find_or_alloc_data_page_for_row(
            data,
            tdef_page,
            owned_ptr,
            free_ptr,
            new_size,
            Some(page_num),
        );
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
    write_u16_le(
        data,
        dp_off + 14 + row_num * 2,
        ((old_end as u16) & 0x1FFF) | 0xC000,
    );
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
    let tdef = parse_table_ver(data, tdef_page, JetVersion::Jet4)?;
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

    for ri in &tdef.real_indexes {
        let mut tree = read_index_btree_entries(data, ri.root_page as usize);
        tree.retain(|e| !(e.page_num == page_num as u32 && e.row_num == row_num as u8));
        write_index_btree_entries(data, tdef_page, ri, &tree);
    }

    let tp_off = tdef_page * PAGE_SIZE;
    let old_cnt = read_u32_le(data, tp_off + 16);
    write_u32_le(data, tp_off + 16, old_cnt.saturating_sub(1));
    Ok(())
}

// ============================================================================
// PropertyMaps (`LvProp` MR2\0 & KKD\0) Binary Reader & Writer
// ============================================================================

fn decode_lvprop_value(
    prop_name: &str,
    dtype: u8,
    vbytes: &[u8],
    ver: JetVersion,
) -> Value {
    match dtype {
        1 => Value::Bool(!vbytes.is_empty() && vbytes[0] != 0),
        2 => {
            if !vbytes.is_empty() {
                serde_json::json!(vbytes[0] as i8)
            } else {
                Value::Null
            }
        }
        3 => serde_json::json!(read_i16_le(vbytes, 0)),
        4 | 18 => serde_json::json!(read_i32_le(vbytes, 0)),
        5 => Value::String(crate::mdb::format_money(read_i64_le(vbytes, 0))),
        6 => serde_json::json!(read_f32_le(vbytes, 0) as f64),
        7 => serde_json::json!(read_f64_le(vbytes, 0)),
        8 => Value::String(crate::mdb::format_access_datetime(read_f64_le(vbytes, 0))),
        9 | 11 => {
            if dtype == 9 && prop_name.eq_ignore_ascii_case("GUID") && vbytes.len() == 16 {
                Value::String(crate::mdb::format_guid(vbytes))
            } else {
                Value::String(BASE64.encode(vbytes))
            }
        }
        10 | 12 => Value::String(decode_jet_text(vbytes, ver)),
        15 => Value::String(crate::mdb::format_guid(vbytes)),
        16 => Value::String(crate::mdb::format_numeric(vbytes, 0)),
        19 => serde_json::json!(read_i64_le(vbytes, 0)),
        _ => Value::String(BASE64.encode(vbytes)),
    }
}

fn encode_lvprop_value(prop_name: &str, dtype: u8, val: &Value) -> Vec<u8> {
    match dtype {
        1 => vec![if value_to_bool(val) { 0xFF } else { 0x00 }],
        2 => vec![value_to_i64(val).unwrap_or(0) as u8],
        3 => (value_to_i64(val).unwrap_or(0) as i16).to_le_bytes().to_vec(),
        4 | 18 => (value_to_i64(val).unwrap_or(0) as i32).to_le_bytes().to_vec(),
        5 => encode_money_i64(val).to_le_bytes().to_vec(),
        6 => (value_to_f64(val).unwrap_or(0.0) as f32).to_le_bytes().to_vec(),
        7 => value_to_f64(val).unwrap_or(0.0).to_le_bytes().to_vec(),
        8 => value_to_access_date_f64(val)
            .unwrap_or(0.0)
            .to_le_bytes()
            .to_vec(),
        9 | 11 => {
            if dtype == 9
                && prop_name.eq_ignore_ascii_case("GUID")
                && val
                    .as_str()
                    .map(|s| s.trim_start().starts_with('{'))
                    .unwrap_or(false)
            {
                encode_guid_16(val).to_vec()
            } else {
                val.as_str()
                    .and_then(|s| BASE64.decode(s).ok())
                    .unwrap_or_default()
            }
        }
        10 | 12 => {
            let s = match val {
                Value::String(st) => st.clone(),
                Value::Number(n) => n.to_string(),
                Value::Bool(b) => b.to_string(),
                _ => String::new(),
            };
            encode_utf16le(&s)
        }
        15 => encode_guid_16(val).to_vec(),
        16 => encode_numeric_17(val, 0).to_vec(),
        19 => value_to_i64(val).unwrap_or(0).to_le_bytes().to_vec(),
        _ => Vec::new(),
    }
}

pub fn decode_lvprop_bytes(bytes: &[u8], ver: JetVersion) -> Result<Value, String> {
    let mut default_props = Vec::new();
    let mut col_props: Map<String, Value> = Map::new();
    let mut idx_props: Map<String, Value> = Map::new();

    if bytes.len() < 4 {
        return Ok(serde_json::json!({
            "default": default_props,
            "columns": col_props,
            "indexes": idx_props,
        }));
    }
    let hdr = &bytes[0..4];
    if hdr != b"MR2\0" && hdr != b"KKD\0" {
        return Ok(serde_json::json!({
            "default": default_props,
            "columns": col_props,
            "indexes": idx_props,
        }));
    }
    let is_jet3 = ver == JetVersion::Jet3 || hdr == b"KKD\0";
    let mut prop_names: Vec<String> = Vec::new();
    let mut pos = 4usize;

    while pos + 6 <= bytes.len() {
        let chunk_len = read_u32_le(bytes, pos) as usize;
        let chunk_type = read_u16_le(bytes, pos + 4);
        if chunk_len < 6 || pos + chunk_len > bytes.len() {
            break;
        }
        let payload = &bytes[pos + 6..pos + chunk_len];
        pos += chunk_len;

        if chunk_type == 0x0080 {
            let mut npos = 0usize;
            while npos + 2 <= payload.len() {
                let nlen = read_u16_le(payload, npos) as usize;
                npos += 2;
                if npos + nlen > payload.len() {
                    break;
                }
                let pname = if is_jet3 {
                    crate::mdb::decode_latin1(&payload[npos..npos + nlen])
                } else {
                    decode_utf16le(&payload[npos..npos + nlen])
                };
                prop_names.push(pname);
                npos += nlen;
            }
        } else if chunk_type == 0x0000 || chunk_type == 0x0001 || chunk_type == 0x0002 {
            if payload.len() < 4 {
                continue;
            }
            let name_blk_len = read_u32_le(payload, 0) as usize;
            if name_blk_len < 4 || name_blk_len > payload.len() {
                continue;
            }
            let map_name = if name_blk_len > 6 {
                let mlen = read_u16_le(payload, 4) as usize;
                let end_m = (6 + mlen).min(name_blk_len);
                if is_jet3 {
                    crate::mdb::decode_latin1(&payload[6..end_m])
                } else {
                    decode_utf16le(&payload[6..end_m])
                }
            } else {
                String::new()
            };

            let mut rpos = name_blk_len;
            let mut list = Vec::new();
            while rpos + 8 <= payload.len() {
                let rec_len = read_u16_le(payload, rpos) as usize;
                if rec_len < 8 || rpos + rec_len > payload.len() {
                    break;
                }
                let flags = payload[rpos + 2];
                let dtype = payload[rpos + 3];
                let name_idx = read_u16_le(payload, rpos + 4) as usize;
                let data_size = read_u16_le(payload, rpos + 6) as usize;
                let v_end = (rpos + 8 + data_size).min(rpos + rec_len);
                let vbytes = &payload[rpos + 8..v_end];
                rpos += rec_len;

                if let Some(pname) = prop_names.get(name_idx) {
                    let val = decode_lvprop_value(pname, dtype, vbytes, ver);
                    list.push(serde_json::json!({
                        "name": pname,
                        "type": crate::mdb::col_type_to_name(dtype),
                        "type_code": dtype,
                        "value": val,
                        "ddl": (flags & 0x01) != 0,
                        "skip_handler": (flags & 0x80) != 0,
                    }));
                }
            }

            if chunk_type == 0x0000 || map_name.is_empty() {
                default_props.extend(list);
            } else if chunk_type == 0x0002 {
                idx_props.insert(map_name, Value::Array(list));
            } else {
                col_props.insert(map_name, Value::Array(list));
            }
        }
    }

    Ok(serde_json::json!({
        "default": default_props,
        "columns": col_props,
        "indexes": idx_props,
    }))
}

pub fn encode_lvprop_bytes(props_obj: &Value) -> Vec<u8> {
    let default_arr = props_obj
        .get("default")
        .and_then(|v| v.as_array())
        .cloned()
        .unwrap_or_default();
    let cols_map = props_obj
        .get("columns")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();
    let idxs_map = props_obj
        .get("indexes")
        .and_then(|v| v.as_object())
        .cloned()
        .unwrap_or_default();

    // Collect all unique property names in order
    let mut prop_names: Vec<String> = Vec::new();
    let mut name_to_idx: HashMap<String, u16> = HashMap::new();
    let mut register_name = |n: &str| {
        let low = n.to_lowercase();
        if !name_to_idx.contains_key(&low) {
            let idx = prop_names.len() as u16;
            prop_names.push(n.to_string());
            name_to_idx.insert(low, idx);
        }
    };

    for item in &default_arr {
        if let Some(n) = item.get("name").and_then(|v| v.as_str()) {
            register_name(n);
        }
    }
    for (_, arr_v) in &cols_map {
        if let Some(arr) = arr_v.as_array() {
            for item in arr {
                if let Some(n) = item.get("name").and_then(|v| v.as_str()) {
                    register_name(n);
                }
            }
        }
    }
    for (_, arr_v) in &idxs_map {
        if let Some(arr) = arr_v.as_array() {
            for item in arr {
                if let Some(n) = item.get("name").and_then(|v| v.as_str()) {
                    register_name(n);
                }
            }
        }
    }

    if prop_names.is_empty() {
        return Vec::new();
    }

    let mut out = Vec::from(&b"MR2\0"[..]);

    // 1. Write 0x0080 PROPERTY_NAME_LIST chunk
    let mut names_payload = Vec::new();
    for pname in &prop_names {
        let nb = encode_utf16le(pname);
        names_payload.extend_from_slice(&(nb.len() as u16).to_le_bytes());
        names_payload.extend_from_slice(&nb);
    }
    let names_chunk_len = (6 + names_payload.len()) as u32;
    out.extend_from_slice(&names_chunk_len.to_le_bytes());
    out.extend_from_slice(&0x0080u16.to_le_bytes());
    out.extend_from_slice(&names_payload);

    let write_val_chunk = |out: &mut Vec<u8>, chunk_type: u16, map_name: &str, items: &[Value]| {
        if items.is_empty() {
            return;
        }
        let mut chunk_payload = Vec::new();
        let name_bytes = if map_name.is_empty() {
            Vec::new()
        } else {
            encode_utf16le(map_name)
        };
        let name_blk_len = (6 + name_bytes.len()) as u32;
        chunk_payload.extend_from_slice(&name_blk_len.to_le_bytes());
        chunk_payload.extend_from_slice(&(name_bytes.len() as u16).to_le_bytes());
        chunk_payload.extend_from_slice(&name_bytes);

        for item in items {
            let pname = item.get("name").and_then(|v| v.as_str()).unwrap_or("");
            if pname.is_empty() {
                continue;
            }
            let Some(&nidx) = name_to_idx.get(&pname.to_lowercase()) else {
                continue;
            };
            let dtype = item
                .get("type_code")
                .and_then(|v| v.as_u64())
                .map(|u| u as u8)
                .unwrap_or_else(|| {
                    item.get("type")
                        .and_then(|v| v.as_str())
                        .map(name_to_col_type)
                        .unwrap_or(10)
                });
            let mut flags = 0u8;
            if item.get("ddl").and_then(|v| v.as_bool()).unwrap_or(false) {
                flags |= 0x01;
            }
            if item
                .get("skip_handler")
                .and_then(|v| v.as_bool())
                .unwrap_or(false)
            {
                flags |= 0x80;
            }
            let val = item.get("value").unwrap_or(&Value::Null);
            let vbytes = encode_lvprop_value(pname, dtype, val);
            let rec_len = (8 + vbytes.len()) as u16;
            chunk_payload.extend_from_slice(&rec_len.to_le_bytes());
            chunk_payload.push(flags);
            chunk_payload.push(dtype);
            chunk_payload.extend_from_slice(&nidx.to_le_bytes());
            chunk_payload.extend_from_slice(&(vbytes.len() as u16).to_le_bytes());
            chunk_payload.extend_from_slice(&vbytes);
        }

        let chunk_len = (6 + chunk_payload.len()) as u32;
        out.extend_from_slice(&chunk_len.to_le_bytes());
        out.extend_from_slice(&chunk_type.to_le_bytes());
        out.extend_from_slice(&chunk_payload);
    };

    write_val_chunk(&mut out, 0x0000, "", &default_arr);
    for (cname, arr_v) in &cols_map {
        if let Some(arr) = arr_v.as_array() {
            write_val_chunk(&mut out, 0x0001, cname, arr);
        }
    }
    for (iname, arr_v) in &idxs_map {
        if let Some(arr) = arr_v.as_array() {
            write_val_chunk(&mut out, 0x0002, iname, arr);
        }
    }
    out
}

pub fn get_object_properties(
    data: &[u8],
    table_name: Option<&str>,
    object_name: Option<&str>,
) -> Result<Value, String> {
    let ver = JetVersion::from_data(data)?;
    let msys = parse_table_ver(data, 2, ver)?;
    let target_tpage = if let Some(tname) = table_name {
        Some(find_table_page(data, tname)? as i64)
    } else {
        None
    };

    for row in &msys.rows {
        let matched = if let Some(tp) = target_tpage {
            let rid = row.get("Id").and_then(value_to_i64).unwrap_or(-1);
            let rtype = row.get("Type").and_then(value_to_i64).unwrap_or(0);
            rid == tp && (rtype == 1 || rtype == 6)
        } else if let Some(oname) = object_name {
            let rname = row.get("Name").and_then(|v| v.as_str()).unwrap_or("");
            rname.eq_ignore_ascii_case(oname)
        } else {
            false
        };
        if matched {
            if let Some(b64_str) = row.get("LvProp").and_then(|v| v.as_str()) {
                if let Ok(raw) = BASE64.decode(b64_str) {
                    return decode_lvprop_bytes(&raw, ver);
                }
            }
            break;
        }
    }
    decode_lvprop_bytes(&[], ver)
}

pub fn save_object_properties(
    data: &mut Vec<u8>,
    table_name: Option<&str>,
    object_name: Option<&str>,
    props_obj: &Value,
) -> Result<(), String> {
    let msys = parse_table_ver(data, 2, JetVersion::Jet4)?;
    let target_tpage = if let Some(tname) = table_name {
        Some(find_table_page(data, tname)? as i64)
    } else {
        None
    };
    let lvprop_bytes = encode_lvprop_bytes(props_obj);

    let mut found_idx: Option<usize> = None;
    for (idx, row) in msys.rows.iter().enumerate() {
        let matched = if let Some(tp) = target_tpage {
            let rid = row.get("Id").and_then(value_to_i64).unwrap_or(-1);
            let rtype = row.get("Type").and_then(value_to_i64).unwrap_or(0);
            rid == tp && (rtype == 1 || rtype == 6)
        } else if let Some(oname) = object_name {
            let rname = row.get("Name").and_then(|v| v.as_str()).unwrap_or("");
            rname.eq_ignore_ascii_case(oname)
        } else {
            false
        };
        if matched {
            found_idx = Some(idx);
            break;
        }
    }

    if let Some(idx) = found_idx {
        let (pnum, rnum) = msys.row_ids[idx];
        let mut updated_row = msys.rows[idx].clone();
        if lvprop_bytes.is_empty() {
            updated_row.insert("LvProp".to_string(), Value::Null);
        } else {
            updated_row.insert(
                "LvProp".to_string(),
                Value::String(BASE64.encode(&lvprop_bytes)),
            );
        }
        let new_row_bytes = encode_row_jet4(data, &msys, &updated_row);
        replace_or_overflow_row_on_page(
            data,
            2,
            msys.owned_pages_ptr,
            msys.free_space_ptr,
            pnum,
            rnum,
            &new_row_bytes,
        )?;
        return Ok(());
    }

    if let Some(oname) = object_name {
        // Insert new Databases child row (e.g. SummaryInfo / UserDefined) into MSysObjects
        let db_parent_id = msys
            .rows
            .iter()
            .find(|r| {
                r.get("Name")
                    .and_then(|v| v.as_str())
                    .map(|s| s.eq_ignore_ascii_case("Databases"))
                    .unwrap_or(false)
            })
            .and_then(|r| r.get("Id").and_then(value_to_i64))
            .unwrap_or(0x0F00_0002);
        let new_id = msys
            .rows
            .iter()
            .filter_map(|r| r.get("Id").and_then(value_to_i64))
            .filter(|&id| id > 0 && id < 0x0F00_0000)
            .max()
            .unwrap_or(20)
            + 1;
        let mut row_map = Map::new();
        row_map.insert("Id".to_string(), Value::Number(new_id.into()));
        row_map.insert("ParentId".to_string(), Value::Number(db_parent_id.into()));
        row_map.insert("Name".to_string(), Value::String(oname.to_string()));
        row_map.insert("Type".to_string(), Value::Number(2.into()));
        row_map.insert("Flags".to_string(), Value::Number(0.into()));
        if !lvprop_bytes.is_empty() {
            row_map.insert(
                "LvProp".to_string(),
                Value::String(BASE64.encode(&lvprop_bytes)),
            );
        }
        let row_bytes = encode_row_jet4(data, &msys, &row_map);
        let dpage = find_or_alloc_data_page_for_row(
            data,
            2,
            msys.owned_pages_ptr,
            msys.free_space_ptr,
            row_bytes.len(),
            None,
        );
        let rnum = append_row_to_data_page(data, dpage, &row_bytes, false);
        let p2_off = 2 * PAGE_SIZE;
        let old_cnt = read_u32_le(data, p2_off + 16);
        write_u32_le(data, p2_off + 16, old_cnt + 1);

        let mut p7_entry = vec![0x7F];
        let pid_be = ((db_parent_id as u32) ^ 0x8000_0000).to_be_bytes();
        p7_entry.extend_from_slice(&pid_be);
        p7_entry.extend_from_slice(&genleg_ascii_sort_bytes(oname));
        let dp_be = (dpage as u32).to_be_bytes();
        p7_entry.push(dp_be[1]);
        p7_entry.push(dp_be[2]);
        p7_entry.push(dp_be[3]);
        p7_entry.push(rnum as u8);

        let mut p8_entry = vec![0x7F];
        let id_be = ((new_id as u32) ^ 0x8000_0000).to_be_bytes();
        p8_entry.extend_from_slice(&id_be);
        p8_entry.push(dp_be[1]);
        p8_entry.push(dp_be[2]);
        p8_entry.push(dp_be[3]);
        p8_entry.push(rnum as u8);

        let _ = insert_uncompressed_index_leaf_entry(data, 7, &p7_entry);
        let _ = insert_uncompressed_index_leaf_entry(data, 8, &p8_entry);
        return Ok(());
    }

    Err("Target object not found in MSysObjects".to_string())
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
            add_rows_to_table_ex(&mut data, table_name, &row_maps, has_auto, false)?;
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
        "get_properties" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            let table_name = req.get("table_name").and_then(|v| v.as_str());
            let object_name = req.get("object_name").and_then(|v| v.as_str());
            let data = fs::read(mdb_path).map_err(|e| e.to_string())?;
            let props = get_object_properties(&data, table_name, object_name)?;
            Ok(serde_json::json!({ "ok": true, "properties": props }))
        }
        "save_properties" => {
            let mdb_path = req
                .get("mdb_path")
                .and_then(|v| v.as_str())
                .ok_or_else(|| "Missing mdb_path".to_string())?;
            let table_name = req.get("table_name").and_then(|v| v.as_str());
            let object_name = req.get("object_name").and_then(|v| v.as_str());
            let props = req
                .get("properties")
                .ok_or_else(|| "Missing properties object".to_string())?;
            let mut data = fs::read(mdb_path).map_err(|e| e.to_string())?;
            save_object_properties(&mut data, table_name, object_name, props)?;
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
            primary_key: true,
            required: true,
            ..Default::default()
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
        assert_eq!(ids, vec![1i64]);

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
    fn test_btree_index_split_constraints_and_lvprop_roundtrip() {
        let mut data = get_empty_v2000_mdb();
        let cols = vec![
            make_col("id", 4, 4, false),
            make_col("code", 10, 100, false),
        ];
        let idxs = vec![
            IndexDef {
                name: "PrimaryKey".to_string(),
                unique: true,
                columns: vec!["id".to_string()],
                primary_key: true,
                required: true,
                ..Default::default()
            },
            IndexDef {
                name: "CodeIdx".to_string(),
                unique: true,
                columns: vec!["code".to_string()],
                ..Default::default()
            },
        ];
        let tpage = create_table_in_data(&mut data, "IndexedTbl", &cols, &idxs).expect("create");

        // Insert 120 rows with 40-char codes so the index B-Tree splits into Node (0x03) + Leaf (0x04) pages
        let mut rows = Vec::with_capacity(120);
        for i in 1..=120 {
            let mut m = Map::new();
            m.insert("id".to_string(), serde_json::json!(i));
            m.insert(
                "code".to_string(),
                serde_json::json!(format!("CODE_{:04}_{}", i, "A".repeat(30))),
            );
            rows.push(m);
        }
        add_rows_to_table(&mut data, "IndexedTbl", &rows, true).expect("insert 120 indexed rows");

        let tdef = parse_table_ver(&data, tpage, JetVersion::Jet4).expect("parse indexed");
        assert_eq!(tdef.real_indexes.len(), 2);
        let code_ri = &tdef.real_indexes[1];
        let root_pg_type = data[(code_ri.root_page as usize) * PAGE_SIZE];
        // Root page of CodeIdx must have split into a Node Page (0x03)!
        assert_eq!(root_pg_type, 0x03);
        let entries = read_index_btree_entries(&data, code_ri.root_page as usize);
        assert_eq!(entries.len(), 120);

        // Verify unique constraint violation on duplicate key
        let mut dup_row = Map::new();
        dup_row.insert("id".to_string(), serde_json::json!(999));
        dup_row.insert(
            "code".to_string(),
            serde_json::json!(format!("CODE_{:04}_{}", 50, "A".repeat(30))),
        );
        let dup_err = add_rows_to_table(&mut data, "IndexedTbl", &[dup_row], true);
        assert!(dup_err.is_err());

        // Verify LvProp PropertyMaps save & load roundtrip
        let props_in = serde_json::json!({
            "default": [
                { "name": "Description", "type": "MEMO", "type_code": 12, "value": "Indexed test table", "ddl": false }
            ],
            "columns": {
                "code": [
                    { "name": "Required", "type": "BOOLEAN", "type_code": 1, "value": true, "ddl": true },
                    { "name": "Format", "type": "TEXT", "type_code": 10, "value": ">", "ddl": true }
                ]
            },
            "indexes": {}
        });
        save_object_properties(&mut data, Some("IndexedTbl"), None, &props_in).expect("save props");
        let props_out = get_object_properties(&data, Some("IndexedTbl"), None).expect("get props");
        assert_eq!(
            props_out["default"][0]["value"].as_str(),
            Some("Indexed test table")
        );
        assert_eq!(
            props_out["columns"]["code"][0]["value"].as_bool(),
            Some(true)
        );
        assert_eq!(
            props_out["columns"]["code"][1]["value"].as_str(),
            Some(">")
        );
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


