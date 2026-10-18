use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};
use chrono::{Duration, NaiveDate};
use serde::{Deserialize, Serialize};
use serde_json::{json, Map, Value};
use std::collections::{BTreeMap, HashMap};
use std::fs;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum JetVersion {
    Jet3,
    Jet4,
    Ace,
}

impl JetVersion {
    pub fn from_data(data: &[u8]) -> Result<Self, String> {
        if data.len() < 2048 * 3 {
            return Err("File too small to be a valid Jet/ACE database".to_string());
        }
        let engine = &data[4..19];
        let ver = data[20];
        if engine == b"Standard Jet DB" || engine == b"MSISAM Database" {
            if ver == 0 {
                Ok(JetVersion::Jet3)
            } else if ver == 1 {
                Ok(JetVersion::Jet4)
            } else {
                Err(format!("Unsupported Jet version byte: {}", ver))
            }
        } else if engine == b"Standard ACE DB" {
            Ok(JetVersion::Ace)
        } else {
            Err("Not a valid Jet/ACE MDB file".to_string())
        }
    }

    pub fn page_size(self) -> usize {
        match self {
            JetVersion::Jet3 => 2048,
            JetVersion::Jet4 | JetVersion::Ace => 4096,
        }
    }

    pub fn data_row_header_off(self) -> usize {
        match self {
            JetVersion::Jet3 => 10,
            JetVersion::Jet4 | JetVersion::Ace => 14,
        }
    }

    pub fn data_num_rows_off(self) -> usize {
        match self {
            JetVersion::Jet3 => 8,
            JetVersion::Jet4 | JetVersion::Ace => 12,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ColumnDef {
    pub name: String,
    #[serde(rename = "type")]
    pub col_type_name: String,
    pub length: u16,
    pub precision: u8,
    pub scale: u8,
    pub auto_number: bool,
    #[serde(skip)]
    pub col_type: u8,
    #[serde(skip)]
    pub col_id: usize,
    #[serde(skip)]
    pub var_col_num: usize,
    #[serde(skip)]
    pub col_index: u16,
    #[serde(skip)]
    pub is_fixed: bool,
    #[serde(skip)]
    pub fixed_off: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RealIndexDef {
    pub index_data_num: usize,
    pub unique_entry_count: u32,
    pub columns: Vec<(String, usize, bool)>,
    pub umap_row: u8,
    pub umap_page: u32,
    pub root_page: u32,
    pub flags: u8,
    pub unique: bool,
    pub ignore_nulls: bool,
    pub required: bool,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct IndexDef {
    pub name: String,
    pub unique: bool,
    pub columns: Vec<String>,
    #[serde(default)]
    pub column_orders: Vec<bool>,
    #[serde(default)]
    pub primary_key: bool,
    #[serde(default)]
    pub ignore_nulls: bool,
    #[serde(default)]
    pub required: bool,
    #[serde(default)]
    pub foreign_key: bool,
    #[serde(default)]
    pub index_data_num: usize,
    #[serde(default)]
    pub root_page: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableDef {
    pub columns: Vec<ColumnDef>,
    pub indexes: Vec<IndexDef>,
    pub rows: Vec<Map<String, Value>>,
    #[serde(skip)]
    pub real_indexes: Vec<RealIndexDef>,
    #[serde(skip)]
    pub row_ids: Vec<(usize, usize)>,
    #[serde(skip)]
    pub tdef_page: usize,
    #[serde(skip)]
    pub tdef_row_count: u32,
    #[serde(skip)]
    pub next_auto_number: i32,
    #[serde(skip)]
    pub max_cols: u16,
    #[serde(skip)]
    pub var_cols: u16,
    #[serde(skip)]
    pub owned_pages_ptr: u32,
    #[serde(skip)]
    pub free_space_ptr: u32,
}

pub fn read_u16_le(b: &[u8], off: usize) -> u16 {
    if off + 2 > b.len() {
        return 0;
    }
    u16::from_le_bytes([b[off], b[off + 1]])
}

pub fn read_i16_le(b: &[u8], off: usize) -> i16 {
    if off + 2 > b.len() {
        return 0;
    }
    i16::from_le_bytes([b[off], b[off + 1]])
}

pub fn read_u32_le(b: &[u8], off: usize) -> u32 {
    if off + 4 > b.len() {
        return 0;
    }
    u32::from_le_bytes([b[off], b[off + 1], b[off + 2], b[off + 3]])
}

pub fn read_i32_le(b: &[u8], off: usize) -> i32 {
    if off + 4 > b.len() {
        return 0;
    }
    i32::from_le_bytes([b[off], b[off + 1], b[off + 2], b[off + 3]])
}

pub fn read_i64_le(b: &[u8], off: usize) -> i64 {
    if off + 8 > b.len() {
        return 0;
    }
    i64::from_le_bytes([
        b[off],
        b[off + 1],
        b[off + 2],
        b[off + 3],
        b[off + 4],
        b[off + 5],
        b[off + 6],
        b[off + 7],
    ])
}

pub fn read_f32_le(b: &[u8], off: usize) -> f32 {
    if off + 4 > b.len() {
        return 0.0;
    }
    f32::from_le_bytes([b[off], b[off + 1], b[off + 2], b[off + 3]])
}

pub fn read_f64_le(b: &[u8], off: usize) -> f64 {
    if off + 8 > b.len() {
        return 0.0;
    }
    f64::from_le_bytes([
        b[off],
        b[off + 1],
        b[off + 2],
        b[off + 3],
        b[off + 4],
        b[off + 5],
        b[off + 6],
        b[off + 7],
    ])
}

pub fn decode_utf16le(b: &[u8]) -> String {
    let mut u16s = Vec::with_capacity(b.len() / 2);
    let mut i = 0;
    while i + 1 < b.len() {
        u16s.push(u16::from_le_bytes([b[i], b[i + 1]]));
        i += 2;
    }
    String::from_utf16_lossy(&u16s)
}

pub fn decode_latin1(b: &[u8]) -> String {
    b.iter().map(|&c| c as char).collect()
}

pub fn decode_jet_text(vb: &[u8], ver: JetVersion) -> String {
    if vb.is_empty() {
        return String::new();
    }
    if ver == JetVersion::Jet3 {
        return decode_latin1(vb);
    }
    if vb.len() >= 2 && vb[0] == 0xFF && vb[1] == 0xFE {
        let mut u16s = Vec::with_capacity(vb.len());
        let mut compressed = true;
        let mut i = 2;
        while i < vb.len() {
            if vb[i] == 0x00 {
                compressed = !compressed;
                i += 1;
                continue;
            }
            if compressed {
                u16s.push(vb[i] as u16);
                i += 1;
            } else {
                if i + 1 < vb.len() {
                    u16s.push(u16::from_le_bytes([vb[i], vb[i + 1]]));
                }
                i += 2;
            }
        }
        String::from_utf16_lossy(&u16s)
    } else {
        decode_utf16le(vb)
    }
}

pub fn col_type_to_name(ct: u8) -> &'static str {
    match ct {
        1 => "BOOLEAN",
        2 => "BYTE",
        3 => "INT",
        4 => "LONG",
        5 => "MONEY",
        6 => "FLOAT",
        7 => "DOUBLE",
        8 => "SHORT_DATE_TIME",
        9 => "BINARY",
        10 => "TEXT",
        11 => "OLE",
        12 => "MEMO",
        15 => "GUID",
        16 => "NUMERIC",
        18 => "COMPLEX_TYPE",
        19 => "BIG_INT",
        20 => "EXT_DATE_TIME",
        _ => "UNKNOWN",
    }
}

pub fn name_to_col_type(name: &str) -> u8 {
    match name.trim().to_uppercase().as_str() {
        "BOOLEAN" => 1,
        "BYTE" => 2,
        "INT" => 3,
        "LONG" => 4,
        "MONEY" => 5,
        "FLOAT" => 6,
        "DOUBLE" => 7,
        "SHORT_DATE_TIME" => 8,
        "BINARY" => 9,
        "TEXT" => 10,
        "OLE" => 11,
        "MEMO" => 12,
        "GUID" => 15,
        "NUMERIC" => 16,
        "COMPLEX_TYPE" => 18,
        "BIG_INT" => 19,
        "EXT_DATE_TIME" => 20,
        _ => 10,
    }
}

pub fn find_row_end(pg: &[u8], row_num: usize, row_hdr_off: usize, page_size: usize) -> usize {
    let mut prev = row_num;
    while prev > 0 {
        prev -= 1;
        let off = (read_u16_le(pg, row_hdr_off + prev * 2) & 0x1FFF) as usize;
        if off > 0 {
            return off;
        }
    }
    page_size
}

pub fn get_row_slice_ver<'a>(
    data: &'a [u8],
    page_num: usize,
    row_num: usize,
    ver: JetVersion,
) -> &'a [u8] {
    let page_size = ver.page_size();
    let row_hdr_off = ver.data_row_header_off();
    if (page_num + 1) * page_size > data.len() {
        return &[];
    }
    let pg = &data[page_num * page_size..(page_num + 1) * page_size];
    let off_pos = row_hdr_off + row_num * 2;
    if off_pos + 2 > page_size {
        return &[];
    }
    let off = (read_u16_le(pg, off_pos) & 0x1FFF) as usize;
    let end = find_row_end(pg, row_num, row_hdr_off, page_size);
    if off <= end && end <= page_size {
        &pg[off..end]
    } else {
        &[]
    }
}

fn read_lval(data: &[u8], vb: &[u8], ver: JetVersion) -> Vec<u8> {
    if vb.len() < 12 {
        return Vec::new();
    }
    let lval_len_and_type = read_u32_le(vb, 0);
    let lval_len = (lval_len_and_type & 0x3FFF_FFFF) as usize;
    let lval_type = (lval_len_and_type >> 30) & 0x03;
    match lval_type {
        2 => {
            let end = (12 + lval_len).min(vb.len());
            vb[12..end].to_vec()
        }
        1 => {
            let rnum = vb[4] as usize;
            let pnum = u32::from_le_bytes([vb[5], vb[6], vb[7], 0]) as usize;
            let rb = get_row_slice_ver(data, pnum, rnum, ver);
            let end = lval_len.min(rb.len());
            rb[..end].to_vec()
        }
        0 => {
            let mut out = Vec::with_capacity(lval_len.min(65536));
            let mut rnum = vb[4] as usize;
            let mut pnum = u32::from_le_bytes([vb[5], vb[6], vb[7], 0]) as usize;
            let mut guard = 0;
            while pnum != 0 && out.len() < lval_len && guard < 10_000 {
                guard += 1;
                let rb = get_row_slice_ver(data, pnum, rnum, ver);
                if rb.len() < 4 {
                    break;
                }
                rnum = rb[0] as usize;
                pnum = u32::from_le_bytes([rb[1], rb[2], rb[3], 0]) as usize;
                out.extend_from_slice(&rb[4..]);
            }
            out.truncate(lval_len);
            out
        }
        _ => Vec::new(),
    }
}

pub fn read_usage_map_ver(data: &[u8], usage_ptr: u32, ver: JetVersion) -> Vec<usize> {
    let page_size = ver.page_size();
    let mpage = (usage_ptr >> 8) as usize;
    let mrow = (usage_ptr & 0xFF) as usize;
    if mpage == 0 {
        return Vec::new();
    }
    let ub = get_row_slice_ver(data, mpage, mrow, ver);
    if ub.len() < 5 {
        return Vec::new();
    }
    let mtype = ub[0];
    let mut pages = Vec::new();
    if mtype == 0 {
        let start_page = if ver == JetVersion::Jet3 {
            // Jet 3 inline usage map has 1-byte type + 4-byte startPage (Wait: in Jet 3 OFFSET_USAGE_MAP_START = 5 too!)
            read_u32_le(ub, 1) as usize
        } else {
            read_u32_le(ub, 1) as usize
        };
        let bitmap = &ub[5..];
        for (i, &b) in bitmap.iter().enumerate() {
            if b == 0 {
                continue;
            }
            for bit in 0..8 {
                if (b & (1 << bit)) != 0 {
                    pages.push(start_page + i * 8 + bit);
                }
            }
        }
    } else if mtype == 1 {
        let num_refs = (ub.len() - 1) / 4;
        let map_data_bytes = page_size - 4;
        for r in 0..num_refs {
            let rpage = read_u32_le(ub, 1 + r * 4) as usize;
            if rpage == 0 || (rpage + 1) * page_size > data.len() {
                continue;
            }
            let rpg = &data[rpage * page_size..(rpage + 1) * page_size];
            let bitmap = &rpg[4..page_size];
            let base = r * map_data_bytes * 8;
            for (i, &b) in bitmap.iter().enumerate() {
                if b == 0 {
                    continue;
                }
                for bit in 0..8 {
                    if (b & (1 << bit)) != 0 {
                        pages.push(base + i * 8 + bit);
                    }
                }
            }
        }
    }
    pages
}

pub fn read_tdef_bytes_ver(data: &[u8], page_num: usize, ver: JetVersion) -> Result<Vec<u8>, String> {
    let page_size = ver.page_size();
    let min_hdr = if ver == JetVersion::Jet3 { 43 } else { 63 };
    let mut buf = Vec::new();
    let mut cur = page_num;
    let mut first = true;
    let mut guard = 0;
    while cur != 0 && guard < 1000 {
        guard += 1;
        if (cur + 1) * page_size > data.len() {
            return Err(format!("TDEF page {} out of bounds", cur));
        }
        let p = &data[cur * page_size..(cur + 1) * page_size];
        if p[0] != 0x02 {
            return Err(format!("Page {} is not a TDEF page", cur));
        }
        let next_page = read_u32_le(p, 4) as usize;
        if first {
            buf.extend_from_slice(p);
            first = false;
        } else {
            buf.extend_from_slice(&p[8..]);
        }
        cur = next_page;
    }
    if buf.len() < min_hdr {
        return Err("TDEF buffer too short".to_string());
    }
    let tdef_len = read_u32_le(&buf, 8) as usize;
    if tdef_len < min_hdr {
        return Err("Invalid TDEF header length".to_string());
    }
    if tdef_len <= buf.len() {
        buf.truncate(tdef_len);
    }
    Ok(buf)
}

pub fn format_money(mval: i64) -> String {
    let sign = if mval < 0 { "-" } else { "" };
    let abs = mval.unsigned_abs();
    let whole = abs / 10_000;
    let frac = abs % 10_000;
    format!("{}{}.{:04}", sign, whole, frac)
}

pub fn format_numeric(bytes: &[u8], scale: u8) -> String {
    if bytes.len() < 17 {
        return "0".to_string();
    }
    let neg = bytes[0] != 0;
    let mut be = [0u8; 16];
    for seg in 0..4 {
        let off = 1 + seg * 4;
        be[seg * 4] = bytes[off + 3];
        be[seg * 4 + 1] = bytes[off + 2];
        be[seg * 4 + 2] = bytes[off + 1];
        be[seg * 4 + 3] = bytes[off];
    }
    let unscaled = u128::from_be_bytes(be);
    let sign_str = if neg && unscaled > 0 { "-" } else { "" };
    if scale == 0 {
        return format!("{}{}", sign_str, unscaled);
    }
    let s = unscaled.to_string();
    let sc = scale as usize;
    if s.len() <= sc {
        let zeros = "0".repeat(sc - s.len());
        format!("{}0.{}{}", sign_str, zeros, s)
    } else {
        let split = s.len() - sc;
        format!("{}{}.{}", sign_str, &s[..split], &s[split..])
    }
}

pub fn format_guid(bytes: &[u8]) -> String {
    if bytes.len() < 16 {
        return String::new();
    }
    let d1 = read_u32_le(bytes, 0);
    let d2 = read_u16_le(bytes, 4);
    let d3 = read_u16_le(bytes, 6);
    format!(
        "{{{:08X}-{:04X}-{:04X}-{:02X}{:02X}-{:02X}{:02X}{:02X}{:02X}{:02X}{:02X}}}",
        d1,
        d2,
        d3,
        bytes[8],
        bytes[9],
        bytes[10],
        bytes[11],
        bytes[12],
        bytes[13],
        bytes[14],
        bytes[15]
    )
}

pub fn format_access_datetime(dval: f64) -> String {
    let days = if dval >= 0.0 {
        dval.floor() as i64
    } else {
        dval.ceil() as i64
    };
    let frac = (dval - (days as f64)).abs();
    let total_ms = (frac * 86_400_000.0).round() as i64;
    let base = NaiveDate::from_ymd_opt(1899, 12, 30)
        .unwrap()
        .and_hms_opt(0, 0, 0)
        .unwrap();
    let dt = base + Duration::days(days) + Duration::milliseconds(total_ms);
    dt.format("%Y-%m-%dT%H:%M:%S").to_string()
}

pub fn parse_table(data: &[u8], page_num: usize) -> Result<TableDef, String> {
    let ver = JetVersion::from_data(data)?;
    parse_table_ver(data, page_num, ver)
}

pub fn parse_table_ver(data: &[u8], page_num: usize, ver: JetVersion) -> Result<TableDef, String> {
    let page_size = ver.page_size();
    let tdef = read_tdef_bytes_ver(data, page_num, ver)?;
    let is_jet3 = ver == JetVersion::Jet3;

    let tdef_row_count = read_u32_le(&tdef, if is_jet3 { 12 } else { 16 });
    let next_auto_number = read_i32_le(&tdef, if is_jet3 { 16 } else { 20 });
    let max_cols = read_u16_le(&tdef, if is_jet3 { 21 } else { 41 });
    let var_cols = read_u16_le(&tdef, if is_jet3 { 23 } else { 43 }) as usize;
    let col_count = read_u16_le(&tdef, if is_jet3 { 25 } else { 45 }) as usize;
    let idx_count = read_u32_le(&tdef, if is_jet3 { 27 } else { 47 }) as usize;
    let real_idx_count = read_u32_le(&tdef, if is_jet3 { 31 } else { 51 }) as usize;
    let row_page_map = read_u32_le(&tdef, if is_jet3 { 35 } else { 55 });
    let free_space_map = read_u32_le(&tdef, if is_jet3 { 39 } else { 59 });

    let hdr_size = if is_jet3 { 43usize } else { 63usize };
    let idx_def_size = if is_jet3 { 8usize } else { 12usize };
    let col_def_size = if is_jet3 { 18usize } else { 25usize };
    let real_idx_blk_size = if is_jet3 { 39usize } else { 52usize };
    let log_idx_blk_size = if is_jet3 { 20usize } else { 28usize };

    let mut pos = hdr_size.saturating_add(real_idx_count.saturating_mul(idx_def_size));
    let mut raw_cols = Vec::with_capacity(col_count.min(512));

    for _ in 0..col_count {
        if pos + col_def_size > tdef.len() {
            return Err("Unexpected EOF reading column descriptors".to_string());
        }
        let cb = &tdef[pos..pos + col_def_size];
        pos += col_def_size;
        let col_type = cb[0];
        let col_id = read_u16_le(cb, if is_jet3 { 1 } else { 5 }) as usize;
        let var_col_num = read_u16_le(cb, if is_jet3 { 3 } else { 7 }) as usize;
        let col_index = read_u16_le(cb, if is_jet3 { 5 } else { 9 });
        let flags = cb[if is_jet3 { 13 } else { 15 }];
        let is_fixed = (flags & 0x01) != 0;
        let auto_number = (flags & 0x44) != 0;
        let fixed_off = read_u16_le(cb, if is_jet3 { 14 } else { 21 }) as usize;
        let length = read_u16_le(cb, if is_jet3 { 16 } else { 23 });
        let (precision, scale) = match col_type {
            5 => (19, 4),
            16 => (cb[11], cb[12]),
            _ => (0, 0),
        };
        raw_cols.push(ColumnDef {
            name: String::new(),
            col_type_name: col_type_to_name(col_type).to_string(),
            length,
            precision,
            scale,
            auto_number,
            col_type,
            col_id,
            var_col_num,
            col_index,
            is_fixed,
            fixed_off,
        });
    }

    for col in &mut raw_cols {
        if is_jet3 {
            if pos + 1 > tdef.len() {
                break;
            }
            let nlen = tdef[pos] as usize;
            pos += 1;
            if pos + nlen <= tdef.len() {
                col.name = decode_latin1(&tdef[pos..pos + nlen]);
            }
            pos += nlen;
        } else {
            if pos + 2 > tdef.len() {
                break;
            }
            let nlen = read_u16_le(&tdef, pos) as usize;
            pos += 2;
            if pos + nlen <= tdef.len() {
                col.name = decode_utf16le(&tdef[pos..pos + nlen]);
            }
            pos += nlen;
        }
    }

    let mut col_name_by_id: HashMap<usize, String> = HashMap::with_capacity(raw_cols.len());
    for c in &raw_cols {
        col_name_by_id.insert(c.col_id, c.name.clone());
    }

    let mut real_indexes: Vec<RealIndexDef> = Vec::with_capacity(real_idx_count.min(256));
    for r_idx in 0..real_idx_count {
        if pos + real_idx_blk_size > tdef.len() {
            break;
        }
        let ib = &tdef[pos..pos + real_idx_blk_size];
        pos += real_idx_blk_size;
        let unique_entry_count = read_u32_le(&tdef, hdr_size + r_idx * idx_def_size + 4);
        let mut cols = Vec::new();
        for s in 0..10 {
            let cid = read_u16_le(ib, 4 + s * 3);
            let cflags = ib[4 + s * 3 + 2];
            if cid != 0xFFFF {
                if let Some(cname) = col_name_by_id.get(&(cid as usize)) {
                    cols.push((cname.clone(), cid as usize, (cflags & 0x01) != 0));
                }
            }
        }
        let umap_row = ib[34];
        let umap_page = if is_jet3 {
            0
        } else {
            (ib[35] as u32) | ((ib[36] as u32) << 8) | ((ib[37] as u32) << 16)
        };
        let root_page = if is_jet3 {
            read_u32_le(ib, 34)
        } else {
            read_u32_le(ib, 38)
        };
        let flags_off = if is_jet3 { 38 } else { 46 };
        let flags = ib[flags_off];
        let unique = (flags & 0x01) != 0;
        let ignore_nulls = (flags & 0x02) != 0;
        let required = (flags & 0x08) != 0;
        real_indexes.push(RealIndexDef {
            index_data_num: r_idx,
            unique_entry_count,
            columns: cols,
            umap_row,
            umap_page,
            root_page,
            flags,
            unique,
            ignore_nulls,
            required,
        });
    }

    struct LogIdx {
        idx_num: i32,
        real_idx_num: usize,
        idx_type: u8,
        name: String,
    }
    let mut logical_indexes = Vec::with_capacity(idx_count.min(256));
    for _ in 0..idx_count {
        if pos + log_idx_blk_size > tdef.len() {
            break;
        }
        let lb = &tdef[pos..pos + log_idx_blk_size];
        pos += log_idx_blk_size;
        let idx_num = read_i32_le(lb, 4);
        let real_idx_num = read_i32_le(lb, 8) as usize;
        let idx_type = lb[if is_jet3 { 19 } else { 23 }];
        logical_indexes.push(LogIdx {
            idx_num,
            real_idx_num,
            idx_type,
            name: String::new(),
        });
    }

    for li in &mut logical_indexes {
        if is_jet3 {
            if pos + 1 > tdef.len() {
                break;
            }
            let nlen = tdef[pos] as usize;
            pos += 1;
            if pos + nlen <= tdef.len() {
                li.name = decode_latin1(&tdef[pos..pos + nlen]);
            }
            pos += nlen;
        } else {
            if pos + 2 > tdef.len() {
                break;
            }
            let nlen = read_u16_le(&tdef, pos) as usize;
            pos += 2;
            if pos + nlen <= tdef.len() {
                li.name = decode_utf16le(&tdef[pos..pos + nlen]);
            }
            pos += nlen;
        }
    }

    raw_cols.sort_by_key(|c| c.col_id);
    logical_indexes.sort_by_key(|li| li.idx_num);

    let mut indexes = Vec::with_capacity(logical_indexes.len());
    for li in logical_indexes {
        if let Some(ri) = real_indexes.get(li.real_idx_num) {
            indexes.push(IndexDef {
                name: li.name,
                unique: ri.unique,
                columns: ri.columns.iter().map(|(n, _, _)| n.clone()).collect(),
                column_orders: ri.columns.iter().map(|(_, _, asc)| *asc).collect(),
                primary_key: li.idx_type == 0x01,
                ignore_nulls: ri.ignore_nulls,
                required: ri.required,
                foreign_key: li.idx_type == 0x02,
                index_data_num: ri.index_data_num,
                root_page: ri.root_page,
            });
        }
    }

    let data_pages = read_usage_map_ver(data, row_page_map, ver);
    let mut rows = Vec::new();
    let mut row_ids = Vec::new();
    let row_hdr_off = ver.data_row_header_off();
    let num_rows_off = ver.data_num_rows_off();

    for p in data_pages {
        if (p + 1) * page_size > data.len() {
            continue;
        }
        let pg = &data[p * page_size..(p + 1) * page_size];
        if pg[0] != 0x01 || (read_u32_le(pg, 4) as usize) != page_num {
            continue;
        }
        let nrows = read_u16_le(pg, num_rows_off) as usize;
        for r in 0..nrows {
            let off_pos = row_hdr_off + r * 2;
            if off_pos + 2 > page_size {
                break;
            }
            let off_raw = read_u16_le(pg, off_pos);
            if (off_raw & 0x8000) != 0 {
                continue;
            }
            let end = find_row_end(pg, r, row_hdr_off, page_size);
            let off = (off_raw & 0x1FFF) as usize;
            if off > end || end > page_size {
                continue;
            }
            let rbytes = if (off_raw & 0x4000) != 0 {
                let ptr = &pg[off..end];
                if ptr.len() < 4 {
                    continue;
                }
                let t_row = ptr[0] as usize;
                let t_page = u32::from_le_bytes([ptr[1], ptr[2], ptr[3], 0]) as usize;
                get_row_slice_ver(data, t_page, t_row, ver)
            } else {
                &pg[off..end]
            };
            let col_cnt_size = if is_jet3 { 1usize } else { 2usize };
            if rbytes.len() < col_cnt_size {
                continue;
            }
            let ncols = if is_jet3 {
                rbytes[0] as usize
            } else {
                read_u16_le(rbytes, 0) as usize
            };
            let null_len = (ncols + 7) / 8;
            if rbytes.len() < col_cnt_size + null_len {
                continue;
            }
            let null_map = &rbytes[rbytes.len() - null_len..];

            let mut row_map = Map::with_capacity(raw_cols.len());
            for c in &raw_cols {
                let cid = c.col_id;
                let is_not_null = if cid < ncols {
                    (null_map[cid / 8] & (1 << (cid % 8))) != 0
                } else {
                    false
                };

                if c.col_type == 1 {
                    row_map.insert(c.name.clone(), Value::Bool(is_not_null));
                    continue;
                }
                if !is_not_null {
                    row_map.insert(c.name.clone(), Value::Null);
                    continue;
                }

                let val = if c.is_fixed {
                    let foff = col_cnt_size + c.fixed_off;
                    match c.col_type {
                        2 => {
                            if foff < rbytes.len() {
                                json!(rbytes[foff] as i8)
                            } else {
                                Value::Null
                            }
                        }
                        3 => json!(read_i16_le(rbytes, foff)),
                        4 | 18 => json!(read_i32_le(rbytes, foff)),
                        5 => Value::String(format_money(read_i64_le(rbytes, foff))),
                        6 => json!(read_f32_le(rbytes, foff) as f64),
                        7 => json!(read_f64_le(rbytes, foff)),
                        8 => Value::String(format_access_datetime(read_f64_le(rbytes, foff))),
                        9 => {
                            let end_f = (foff + c.length as usize).min(rbytes.len());
                            if foff <= end_f {
                                Value::String(BASE64.encode(&rbytes[foff..end_f]))
                            } else {
                                Value::Null
                            }
                        }
                        10 => {
                            let end_f = (foff + c.length as usize).min(rbytes.len());
                            if foff <= end_f {
                                Value::String(decode_jet_text(&rbytes[foff..end_f], ver))
                            } else {
                                Value::Null
                            }
                        }
                        15 => {
                            let end_f = (foff + 16).min(rbytes.len());
                            if foff + 16 <= end_f {
                                Value::String(format_guid(&rbytes[foff..end_f]))
                            } else {
                                Value::Null
                            }
                        }
                        16 => {
                            let end_f = (foff + 17).min(rbytes.len());
                            if foff + 17 <= end_f {
                                Value::String(format_numeric(&rbytes[foff..end_f], c.scale))
                            } else {
                                Value::Null
                            }
                        }
                        19 => json!(read_i64_le(rbytes, foff)),
                        _ => Value::Null,
                    }
                } else {
                    let vnum = c.var_col_num;
                    let vb: &[u8] = if is_jet3 {
                        extract_jet3_var_slice(rbytes, null_len, var_cols, vnum)
                    } else {
                        let var_table_end = if var_cols > 0 && rbytes.len() >= null_len + 2 {
                            rbytes.len() - null_len - 2
                        } else {
                            0
                        };
                        let num_var = if var_cols > 0 && var_table_end >= 2 {
                            read_u16_le(rbytes, var_table_end) as usize
                        } else {
                            0
                        };
                        if vnum < num_var && var_table_end >= 2 * (vnum + 2) {
                            let s = read_u16_le(rbytes, var_table_end - 2 * (vnum + 1)) as usize;
                            let e = read_u16_le(rbytes, var_table_end - 2 * (vnum + 2)) as usize;
                            if s <= e && e <= rbytes.len() {
                                &rbytes[s..e]
                            } else {
                                &[]
                            }
                        } else {
                            &[]
                        }
                    };
                    match c.col_type {
                        10 => Value::String(decode_jet_text(vb, ver)),
                        12 => {
                            let lbytes = read_lval(data, vb, ver);
                            Value::String(decode_jet_text(&lbytes, ver))
                        }
                        9 => Value::String(BASE64.encode(vb)),
                        11 => {
                            let lbytes = read_lval(data, vb, ver);
                            Value::String(BASE64.encode(&lbytes))
                        }
                        16 => {
                            if vb.len() >= 17 {
                                Value::String(format_numeric(&vb[..17], c.scale))
                            } else {
                                Value::Null
                            }
                        }
                        _ => Value::String(BASE64.encode(vb)),
                    }
                };
                row_map.insert(c.name.clone(), val);
            }
            rows.push(row_map);
            row_ids.push((p, r));
        }
    }

    Ok(TableDef {
        columns: raw_cols,
        indexes,
        rows,
        real_indexes,
        row_ids,
        tdef_page: page_num,
        tdef_row_count,
        next_auto_number,
        max_cols,
        var_cols: var_cols as u16,
        owned_pages_ptr: row_page_map,
        free_space_ptr: free_space_map,
    })
}

fn extract_jet3_var_slice<'a>(
    rbytes: &'a [u8],
    null_len: usize,
    var_cols: usize,
    vnum: usize,
) -> &'a [u8] {
    if var_cols == 0 || rbytes.len() < null_len + 2 {
        return &[];
    }
    let var_cnt_pos = rbytes.len() - null_len - 1;
    let num_var = rbytes[var_cnt_pos] as usize;
    if vnum >= num_var {
        return &[];
    }
    let mut num_jumps = (rbytes.len() - 1) / 256;
    if var_cnt_pos < num_jumps + num_var + 1 {
        return &[];
    }
    // Check if trailing jumps are unused (Jackcess TableImpl.readJumpTable)
    while num_jumps > 0 {
        let jump_table_off = var_cnt_pos - num_jumps;
        let eod_pos = jump_table_off - num_var - 1;
        let last_jump_col = rbytes[var_cnt_pos - 1] as usize;
        if last_jump_col > num_var && eod_pos < rbytes.len() {
            num_jumps -= 1;
        } else {
            break;
        }
    }
    let jump_table_off = var_cnt_pos - num_jumps;
    if jump_table_off < num_var + 1 {
        return &[];
    }
    let jump_slice = &rbytes[jump_table_off..var_cnt_pos];
    let mut start_step = 0usize;
    let mut end_step = 0usize;
    for &jcol in jump_slice {
        let jc = jcol as usize;
        if jc <= vnum {
            start_step += 1;
        }
        if jc <= vnum + 1 {
            end_step += 1;
        }
    }
    let s_pos = jump_table_off - 1 - vnum;
    let e_pos = jump_table_off - 2 - vnum;
    let s = (rbytes[s_pos] as usize) + start_step * 256;
    let e = (rbytes[e_pos] as usize) + end_step * 256;
    if s <= e && e <= rbytes.len() {
        &rbytes[s..e]
    } else {
        &[]
    }
}

pub fn discover_tables(data: &[u8], include_system: bool) -> Result<BTreeMap<String, usize>, String> {
    let ver = JetVersion::from_data(data)?;
    let msys = parse_table_ver(data, 2, ver)?;
    let mut tables: Vec<(String, usize)> = Vec::new();
    for r in msys.rows {
        let rtype = r.get("Type").and_then(|v| v.as_i64()).unwrap_or(0);
        let rflags = r.get("Flags").and_then(|v| v.as_i64()).unwrap_or(0);
        let rname = r.get("Name").and_then(|v| v.as_str()).unwrap_or("");
        let rid = r.get("Id").and_then(|v| v.as_i64()).unwrap_or(0);
        if rtype == 1 && rid > 0 && !rname.starts_with('~') {
            let is_sys = ((rflags as u32) & 0x8000_0002) != 0;
            if include_system || !is_sys {
                tables.push((rname.to_string(), rid as usize));
            }
        }
    }
    tables.sort_by(|a, b| a.0.to_lowercase().cmp(&b.0.to_lowercase()));
    let mut map = BTreeMap::new();
    for (name, id) in tables {
        map.insert(name, id);
    }
    Ok(map)
}

pub fn discover_user_tables(data: &[u8]) -> Result<BTreeMap<String, usize>, String> {
    discover_tables(data, false)
}

pub fn export_full_schema_from_file(mdb_path: &str) -> Result<Value, String> {
    let data = fs::read(mdb_path).map_err(|e| format!("Failed to read MDB {}: {}", mdb_path, e))?;
    let ver = JetVersion::from_data(&data)?;
    let user_tables = discover_user_tables(&data)?;
    let mut tables_map = Map::with_capacity(user_tables.len());
    for (tname, tpage) in user_tables {
        let tdef = parse_table_ver(&data, tpage, ver)?;
        let val = serde_json::to_value(&tdef).map_err(|e| e.to_string())?;
        tables_map.insert(tname, val);
    }
    Ok(json!({ "tables": Value::Object(tables_map) }))
}
