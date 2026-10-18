use serde_json::{json, Map, Value};
use std::collections::HashMap;

pub type LowerRow = HashMap<String, Value>;

fn is_nan_or_null(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => true,
        Some(Value::Number(n)) => n.as_f64().map(|f| f.is_nan()).unwrap_or(false),
        _ => false,
    }
}

fn safe_int(v: Option<&Value>, default: i64) -> i64 {
    match v {
        None | Some(Value::Null) => default,
        Some(Value::Number(n)) => {
            if let Some(i) = n.as_i64() {
                i
            } else if let Some(f) = n.as_f64() {
                if f.is_nan() || f.is_infinite() {
                    default
                } else {
                    f as i64
                }
            } else {
                default
            }
        }
        Some(Value::Bool(b)) => {
            if *b {
                1
            } else {
                0
            }
        }
        Some(Value::String(s)) => {
            let t = s.trim();
            if let Ok(i) = t.parse::<i64>() {
                i
            } else if let Ok(f) = t.parse::<f64>() {
                if f.is_nan() || f.is_infinite() {
                    default
                } else {
                    f as i64
                }
            } else {
                default
            }
        }
        _ => default,
    }
}

fn safe_float(v: Option<&Value>, default: f64) -> f64 {
    match v {
        None | Some(Value::Null) => default,
        Some(Value::Number(n)) => {
            let f = n.as_f64().unwrap_or(default);
            if f.is_nan() {
                default
            } else {
                f
            }
        }
        Some(Value::String(s)) => {
            let t = s.trim();
            if t.is_empty() {
                default
            } else {
                let f = t.parse::<f64>().unwrap_or(default);
                if f.is_nan() {
                    default
                } else {
                    f
                }
            }
        }
        Some(Value::Bool(b)) => {
            if *b {
                1.0
            } else {
                0.0
            }
        }
        _ => default,
    }
}

fn get_val(row: &LowerRow, key: &str, default: &str) -> String {
    match row.get(key) {
        None | Some(Value::Null) => default.to_string(),
        Some(Value::String(s)) => s.trim().to_string(),
        Some(Value::Number(n)) => {
            if let Some(f) = n.as_f64() {
                if f.is_nan() {
                    return default.to_string();
                }
            }
            n.to_string().trim().to_string()
        }
        Some(Value::Bool(b)) => {
            if *b {
                "True".to_string()
            } else {
                "False".to_string()
            }
        }
        Some(other) => other.to_string().trim().to_string(),
    }
}

fn is_truthy(v: Option<&Value>) -> bool {
    match v {
        None | Some(Value::Null) => false,
        Some(Value::Bool(b)) => *b,
        Some(Value::Number(n)) => {
            if let Some(i) = n.as_i64() {
                i != 0
            } else if let Some(f) = n.as_f64() {
                f != 0.0 && !f.is_nan()
            } else {
                false
            }
        }
        Some(Value::String(s)) => !s.is_empty(),
        Some(Value::Array(a)) => !a.is_empty(),
        Some(Value::Object(o)) => !o.is_empty(),
    }
}

fn num_to_string(val: f64) -> String {
    if val <= 0.0 || val.is_nan() {
        "NT".to_string()
    } else {
        format!("{:.2}", val)
    }
}

fn normalize_status(stat: &str) -> String {
    let s = stat.trim().to_uppercase();
    match s.as_str() {
        "SCR" | "R" => "SCR".to_string(),
        "DNS" => "DNS".to_string(),
        "DNF" => "DNF".to_string(),
        "DQ" | "Q" => "DQ".to_string(),
        _ => s,
    }
}

fn time_to_string(time_val: f64, status: &str) -> String {
    let s = status.trim().to_uppercase();
    match s.as_str() {
        "SCR" | "R" => return "SCR".to_string(),
        "DNS" => return "DNS".to_string(),
        "DNF" => return "DNF".to_string(),
        "DQ" | "Q" => return "DQ".to_string(),
        _ => {}
    }
    if time_val <= 0.0 || time_val.is_nan() {
        "NT".to_string()
    } else {
        format!("{:.2}", time_val)
    }
}

fn time_to_min_sec(time_str: &str) -> String {
    if time_str.is_empty()
        || matches!(time_str, "NT" | "SCR" | "DNS" | "DNF" | "DQ")
    {
        return time_str.to_string();
    }
    let Ok(val) = time_str.parse::<f64>() else {
        return time_str.to_string();
    };
    let seconds = val as i64;
    // Python round((val - seconds) * 100)
    let diff_100 = (val - (seconds as f64)) * 100.0;
    let ms = diff_100.round() as i64;
    let minutes = seconds / 60;
    let rem_seconds = seconds % 60;
    if minutes > 0 {
        format!("{}:{:02}.{:02}", minutes, rem_seconds, ms)
    } else {
        format!("{:02}.{:02}", rem_seconds, ms)
    }
}

fn get_stroke(stroke_id: &str, is_relay: bool) -> String {
    if stroke_id.is_empty() {
        return if is_relay {
            "Relay".to_string()
        } else {
            String::new()
        };
    }
    let sid = stroke_id.chars().next().unwrap_or(' ').to_ascii_uppercase();
    let name = match sid {
        '1' | 'A' => "Freestyle",
        '2' | 'B' => "Backstroke",
        '3' | 'C' => "Breaststroke",
        '4' | 'D' => "Butterfly",
        '5' | 'E' => {
            if is_relay {
                "Medley"
            } else {
                "Individual Medley"
            }
        }
        'F' => "Diving",
        _ => "",
    };
    if is_relay {
        if name.is_empty() {
            return "Relay".to_string();
        }
        if !name.contains("Relay") {
            return format!("{} Relay", name);
        }
    }
    name.to_string()
}

fn parse_lo_hi(val: i64) -> (i64, i64) {
    if val <= 0 {
        return (0, 109);
    }
    if val < 10 {
        return (0, val);
    }
    let s = val.to_string();
    match s.len() {
        2 => {
            let low = s[0..1].parse::<i64>().unwrap_or(0);
            let mut high = s[1..2].parse::<i64>().unwrap_or(0);
            if high == 0 {
                high = low + 1;
            }
            (low, high)
        }
        3 => {
            let low = s[0..1].parse::<i64>().unwrap_or(0);
            let high = s[1..3].parse::<i64>().unwrap_or(0);
            (low, high)
        }
        4 => {
            let low = s[0..2].parse::<i64>().unwrap_or(0);
            let mut high = s[2..4].parse::<i64>().unwrap_or(0);
            if low == 15 && high == 16 {
                high = 18;
            }
            (low, high)
        }
        _ => (0, 109),
    }
}

#[derive(Clone, Debug)]
struct SessionObj {
    sess_id: i64,
    number: i64,
    name: String,
    day: i64,
    start_time: Value,
    is_default: bool,
}

impl SessionObj {
    fn default_session() -> Self {
        Self {
            sess_id: 1,
            number: 1,
            name: "Session 1".to_string(),
            day: 1,
            start_time: Value::String("08:00".to_string()),
            is_default: true,
        }
    }

    fn to_map(&self) -> Map<String, Value> {
        let mut m = Map::new();
        m.insert("sessionNum".to_string(), json!(self.number));
        m.insert("sessionDay".to_string(), json!(self.day));
        m.insert("startTime".to_string(), self.start_time.clone());
        m.insert("sessionDesc".to_string(), json!(self.name));
        m
    }
}

#[derive(Clone, Debug)]
struct EventObj {
    event_no: i64,
    is_relay: bool,
    gender: String,
    gender_desc: String,
    min_age: i64,
    max_age: i64,
    distance: i64,
    stroke: String,
    division: String,
    round_ltr: String,
    event_ptr: i64,
    num_lanes: i64,
    description: String,
    entries: Vec<(i64, i64, Value)>,
}

impl EventObj {
    fn create_description(&mut self) {
        let gender_str = match self.gender.as_str() {
            "F" => "Girls",
            "M" => "Boys",
            "X" => "Mixed",
            _ => self.gender_desc.as_str(),
        };
        let age_str = if self.min_age == 0 && self.max_age >= 109 {
            "Open".to_string()
        } else if self.min_age == 0 {
            format!("{} & under", self.max_age)
        } else if self.max_age >= 109 {
            format!("{} & over", self.min_age)
        } else {
            format!("{}-{}", self.min_age, self.max_age)
        };
        self.description = format!("{} {} {} Yard {}", gender_str, age_str, self.distance, self.stroke);
        if !self.division.is_empty() {
            self.description.push_str(&format!(" ({})", self.division));
        }
    }

    fn to_value(mut self) -> Value {
        self.entries.sort_by_key(|(h, l, _)| (*h, *l));
        let sorted_entries: Vec<Value> = self.entries.into_iter().map(|(_, _, v)| v).collect();
        json!({
            "eventNum": self.event_no,
            "eventDesc": self.description,
            "isRelay": self.is_relay,
            "numLanes": self.num_lanes,
            "gender": self.gender,
            "minAge": self.min_age,
            "maxAge": self.max_age,
            "entries": sorted_entries,
        })
    }
}

#[derive(Clone, Debug)]
struct TeamCacheItem {
    name: String,
    abbr: String,
    raw_abbr: String,
}

fn load_normalized_table(raw_rows: &[Value], keep_last_dup: bool) -> Vec<LowerRow> {
    let id_cols = [
        "event_ptr",
        "team_no",
        "ath_no",
        "sess_ptr",
        "mtevent",
        "mtev",
        "athlete",
    ];
    let mut out = Vec::with_capacity(raw_rows.len());
    for r in raw_rows {
        let Some(obj) = r.as_object() else { continue };
        let mut row = LowerRow::with_capacity(obj.len());
        for (k, v) in obj.iter() {
            let lk = k.to_lowercase();
            if keep_last_dup || !row.contains_key(&lk) {
                row.insert(lk, v.clone());
            }
        }
        if keep_last_dup {
            for &ic in &id_cols {
                if let Some(val) = row.get(ic) {
                    let iv = safe_int(Some(val), 0);
                    row.insert(ic.to_string(), json!(iv));
                }
            }
        }
        out.push(row);
    }
    out
}

pub fn convert_meet_data_rs(root_input: &Map<String, Value>, from_mdb: bool) -> Value {
    let table_data: &Map<String, Value> = if let Some(inner) = root_input.get("data").and_then(|v| v.as_object()) {
        inner
    } else {
        root_input
    };

    let mut schema_type = "A";
    for cand in ["MTEVENT", "mtevent"] {
        if table_data.contains_key(cand) {
            schema_type = "B";
            break;
        }
    }

    let aliases: &[(&str, &[&str])] = &[
        ("meet", &["Meet", "MEET", "meet"]),
        ("session", &["Session", "SESSIONS", "session"]),
        ("sessitem", &["Sessitem", "SESSITEM", "sessitem"]),
        ("event", &["Event", "MTEVENT", "event"]),
        ("entry", &["Entry", "ENTRY", "entry"]),
        ("relay", &["Relay", "RELAY", "relay"]),
        ("relaynames", &["RelayNames", "RELAYNAMES", "relaynames"]),
        ("athlete", &["athlete", "ATHLETE", "Athlete"]),
        ("team", &["Team", "TEAM", "team"]),
        ("divisions", &["Divisions", "DIVISIONS", "divisions"]),
    ];

    let mut tables: HashMap<&'static str, Vec<LowerRow>> = HashMap::new();
    for &(logical, candidates) in aliases {
        let mut found: Option<&Vec<Value>> = None;
        let mut matched_name = "";
        for &cand in candidates {
            if let Some(arr) = table_data.get(cand).and_then(|v| v.as_array()) {
                found = Some(arr);
                matched_name = cand;
                break;
            }
            for (k, v) in table_data.iter() {
                if k.eq_ignore_ascii_case(cand) {
                    if let Some(arr) = v.as_array() {
                        found = Some(arr);
                        matched_name = k.as_str();
                        break;
                    }
                }
            }
            if found.is_some() {
                break;
            }
        }
        if logical == "event" && matched_name.eq_ignore_ascii_case("MTEVENT") {
            schema_type = "B";
        }
        if let Some(arr) = found {
            tables.insert(logical, load_normalized_table(arr, !from_mdb));
        } else {
            tables.insert(logical, Vec::new());
        }
    }

    // Build team map
    let mut team_map: HashMap<i64, TeamCacheItem> = HashMap::new();
    if let Some(team_rows) = tables.get("team") {
        for row in team_rows {
            let tid_val = row
                .get("team")
                .or_else(|| row.get("team_no"))
                .or_else(|| row.get("team_ptr"));
            let tid = safe_int(tid_val, 0);
            let raw_abbr_val = row
                .get("tcode")
                .or_else(|| row.get("team_abbr"))
                .or_else(|| row.get("abbr"));
            let raw_abbr = match raw_abbr_val {
                None | Some(Value::Null) => String::new(),
                Some(Value::String(s)) => s.clone(),
                Some(o) => o.to_string(),
            };
            let abbr = raw_abbr.trim().to_string();
            let full_name = get_val(row, "team_name", "");
            let full_name = if !full_name.is_empty() {
                full_name
            } else {
                get_val(row, "name", "")
            };
            let short = {
                let s1 = get_val(row, "short", "");
                if !s1.is_empty() {
                    s1
                } else {
                    let s2 = get_val(row, "team_short", "");
                    if !s2.is_empty() {
                        s2
                    } else {
                        get_val(row, "short_name", "")
                    }
                }
            };
            let lsc = {
                let l1 = get_val(row, "lsc", "");
                if !l1.is_empty() {
                    l1
                } else {
                    get_val(row, "team_lsc", "")
                }
            };
            let name = if !full_name.is_empty() {
                full_name
            } else if !short.is_empty() {
                short
            } else {
                format!("{}-{}", abbr, lsc).trim_matches('-').to_string()
            };
            let clean_name = name.trim().to_string();
            let final_abbr = if !abbr.is_empty() {
                abbr.clone()
            } else {
                clean_name.clone()
            };
            let final_raw_abbr = if !raw_abbr.is_empty() {
                raw_abbr
            } else {
                final_abbr.clone()
            };
            team_map.insert(
                tid,
                TeamCacheItem {
                    name: clean_name,
                    abbr: final_abbr,
                    raw_abbr: final_raw_abbr,
                },
            );
        }
    }

    let get_team = |team_no: i64| -> TeamCacheItem {
        team_map.get(&team_no).cloned().unwrap_or(TeamCacheItem {
            name: String::new(),
            abbr: String::new(),
            raw_abbr: String::new(),
        })
    };

    // Build division map
    let mut division_map: HashMap<i64, String> = HashMap::new();
    if let Some(div_rows) = tables.get("divisions") {
        for row in div_rows {
            let did = safe_int(row.get("div_no"), 0);
            let name = get_val(row, "div_name", "");
            if !name.is_empty() {
                division_map.insert(did, name);
            }
        }
    }

    // Build athlete map
    let mut athlete_map: HashMap<i64, Value> = HashMap::new();
    if let Some(ath_rows) = tables.get("athlete") {
        for row in ath_rows {
            let aid_val = if is_truthy(row.get("ath_no")) {
                row.get("ath_no")
            } else {
                row.get("athlete")
            };
            let aid = safe_int(aid_val, 0);
            let tno_val = if is_truthy(row.get("team_no")) {
                row.get("team_no")
            } else {
                row.get("team1")
            };
            let team_no = safe_int(tno_val, 0);
            let t_info = get_team(team_no);

            let orig_first = {
                let f1 = get_val(row, "first_name", "");
                if !f1.is_empty() {
                    f1
                } else {
                    get_val(row, "first", "")
                }
            };
            let pref = get_val(row, "pref_name", "");
            let first_name = if !pref.is_empty() {
                pref
            } else {
                orig_first.clone()
            };
            let last_name = {
                let l1 = get_val(row, "last_name", "");
                if !l1.is_empty() {
                    l1
                } else {
                    get_val(row, "last", "")
                }
            };
            let initial = get_val(row, "initial", "");
            let age_val = if is_truthy(row.get("ath_age")) {
                row.get("ath_age")
            } else {
                row.get("age")
            };
            let age = safe_int(age_val, 0);
            let sex = {
                let s1 = get_val(row, "ath_sex", "");
                if !s1.is_empty() {
                    s1
                } else {
                    get_val(row, "sex", "")
                }
            };
            let school_yr = {
                let y1 = get_val(row, "schl_yr", "");
                if !y1.is_empty() {
                    y1
                } else {
                    get_val(row, "class", "")
                }
            };

            athlete_map.insert(
                aid,
                json!({
                    "athleteId": aid,
                    "firstName": first_name,
                    "legalName": orig_first,
                    "lastName": last_name,
                    "initial": initial,
                    "name": format!("{} {}", first_name, last_name),
                    "age": age,
                    "athleteSex": sex,
                    "schoolYear": school_yr,
                    "teamName": t_info.name,
                    "teamCode": t_info.abbr,
                    "rawTeamCode": t_info.raw_abbr,
                    "teamId": team_no,
                }),
            );
        }
    }

    // Group entries & relays by event_ptr / mtevent
    let entry_group_col = if schema_type == "B" { "mtevent" } else { "event_ptr" };
    let mut entry_grouped: HashMap<i64, Vec<&LowerRow>> = HashMap::new();
    if let Some(entry_rows) = tables.get("entry") {
        for row in entry_rows {
            if let Some(v) = row.get(entry_group_col) {
                if !is_nan_or_null(Some(v)) {
                    let k = safe_int(Some(v), 0);
                    entry_grouped.entry(k).or_default().push(row);
                }
            }
        }
    }

    let mut relay_grouped: HashMap<i64, Vec<&LowerRow>> = HashMap::new();
    if let Some(relay_rows) = tables.get("relay") {
        for row in relay_rows {
            if let Some(v) = row.get(entry_group_col) {
                if !is_nan_or_null(Some(v)) {
                    let k = safe_int(Some(v), 0);
                    relay_grouped.entry(k).or_default().push(row);
                }
            }
        }
    }

    // Pre-inspect relaynames columns
    let relaynames_rows = tables.get("relaynames").map(|v| v.as_slice()).unwrap_or(&[]);
    let rn_has_event_ptr = relaynames_rows.iter().any(|r| r.contains_key("event_ptr"));
    let rn_has_team_no = relaynames_rows.iter().any(|r| r.contains_key("team_no"));
    let rn_has_team_ltr = relaynames_rows.iter().any(|r| r.contains_key("team_ltr"));
    let rn_has_event_round = relaynames_rows.iter().any(|r| r.contains_key("event_round"));

    // Meet info
    let meet_rows = tables.get("meet").map(|v| v.as_slice()).unwrap_or(&[]);
    let (meet_name, meet_loc, meet_start, meet_end, meet_type, num_lanes) =
        if let Some(row) = meet_rows.first() {
            if schema_type == "B" {
                (
                    get_val(row, "meet", ""),
                    get_val(row, "location", ""),
                    get_val(row, "start", ""),
                    get_val(row, "end", ""),
                    0i64,
                    0i64,
                )
            } else {
                (
                    get_val(row, "meet_name1", ""),
                    get_val(row, "meet_location", ""),
                    get_val(row, "meet_start", ""),
                    get_val(row, "meet_end", ""),
                    safe_int(row.get("meet_class"), 0),
                    safe_int(row.get("meet_numlanes"), 0),
                )
            }
        } else {
            (
                String::new(),
                String::new(),
                String::new(),
                String::new(),
                0,
                0,
            )
        };

    // Sessions
    let session_rows = tables.get("session").map(|v| v.as_slice()).unwrap_or(&[]);
    let mut sessions: Vec<SessionObj> = Vec::new();
    if !session_rows.is_empty() {
        if schema_type == "B" {
            let mut valid_rows: Vec<(i64, &LowerRow)> = Vec::new();
            let has_session_col = session_rows.iter().any(|r| r.contains_key("session"));
            for row in session_rows {
                if has_session_col && is_nan_or_null(row.get("session")) {
                    continue;
                }
                let sess_num = safe_int(row.get("session"), 0);
                valid_rows.push((sess_num, row));
            }
            if has_session_col {
                valid_rows.sort_by_key(|(n, _)| *n);
            }
            for (sess_num, row) in valid_rows {
                sessions.push(SessionObj {
                    sess_id: sess_num,
                    number: sess_num,
                    name: format!("Session {}", sess_num),
                    day: safe_int(row.get("day"), 1),
                    start_time: Value::String(get_val(row, "starttime", "09:00")),
                    is_default: false,
                });
            }
        } else {
            let mut indexed_rows: Vec<(i64, &LowerRow)> = session_rows
                .iter()
                .map(|r| (safe_int(r.get("sess_no"), 0), r))
                .collect();
            let has_sess_no = session_rows.iter().any(|r| r.contains_key("sess_no"));
            if has_sess_no {
                indexed_rows.sort_by_key(|(n, _)| *n);
            }
            let has_starttime_col = session_rows.iter().any(|r| r.contains_key("sess_starttime"));
            for (_, row) in indexed_rows {
                let st = if let Some(v) = row.get("sess_starttime") {
                    v.clone()
                } else if has_starttime_col {
                    Value::Null
                } else {
                    json!(32400)
                };
                sessions.push(SessionObj {
                    sess_id: safe_int(row.get("sess_ptr"), 0),
                    number: safe_int(row.get("sess_no"), 0),
                    name: get_val(row, "sess_name", ""),
                    day: safe_int(row.get("sess_day"), 1),
                    start_time: st,
                    is_default: false,
                });
            }
        }
    }

    let event_rows = tables.get("event").map(|v| v.as_slice()).unwrap_or(&[]);
    if sessions.is_empty() && schema_type != "B" {
        sessions.push(SessionObj::default_session());
    }
    if sessions.is_empty() && !event_rows.is_empty() {
        sessions.push(SessionObj::default_session());
    }

    let create_event_from_row = |row: &LowerRow, round_ltr: &str| -> EventObj {
        if schema_type == "B" {
            let relay = row
                .get("i_r")
                .map(|v| match v {
                    Value::String(s) => s == "R",
                    _ => v.to_string() == "R",
                })
                .unwrap_or(false);
            let lo_hi = safe_int(row.get("lo_hi"), 0);
            let (min_age, max_age) = parse_lo_hi(lo_hi);
            let stroke_str = get_val(row, "stroke", "");
            let stroke_name = get_stroke(&stroke_str, relay);
            let div_str = if is_truthy(row.get("division")) {
                get_val(row, "division", "")
            } else {
                String::new()
            };
            let ev_no = safe_int(row.get("mtevent"), 0);
            EventObj {
                event_no: ev_no,
                is_relay: relay,
                gender: get_val(row, "sex", ""),
                gender_desc: get_val(row, "sex", ""),
                min_age,
                max_age,
                distance: safe_int(row.get("distance"), 0),
                stroke: stroke_name,
                division: div_str,
                round_ltr: round_ltr.to_string(),
                event_ptr: ev_no,
                num_lanes: 0,
                description: String::new(),
                entries: Vec::new(),
            }
        } else {
            let relay = get_val(row, "ind_rel", "") == "R";
            let pre_lanes = safe_int(row.get("num_prelanes"), 0);
            let fin_lanes = safe_int(row.get("num_finlanes"), 0);
            let evt_rounds = safe_int(row.get("event_rounds"), 1);
            let num_lanes = if evt_rounds == 1 { pre_lanes } else { fin_lanes };
            let div_no = safe_int(row.get("div_no"), 0);
            let division_name = division_map.get(&div_no).cloned().unwrap_or_default();
            let stroke_char = get_val(row, "event_stroke", "");
            let stroke_name = get_stroke(&stroke_char, relay);
            let min_age = safe_int(row.get("low_age"), 0);
            let mut max_age = safe_int(row.get("high_age"), 0);
            if max_age == 0 && min_age > 0 {
                max_age = min_age + 1;
            } else if max_age == 0 && min_age == 0 {
                max_age = 6;
            }
            if min_age == 15 && max_age == 16 {
                max_age = 18;
            }
            EventObj {
                event_no: safe_int(row.get("event_no"), 0),
                is_relay: relay,
                gender: get_val(row, "event_gender", ""),
                gender_desc: get_val(row, "event_sex", ""),
                min_age,
                max_age,
                distance: safe_int(row.get("event_dist"), 0),
                stroke: stroke_name,
                division: division_name,
                round_ltr: round_ltr.to_string(),
                event_ptr: safe_int(row.get("event_ptr"), 0),
                num_lanes,
                description: String::new(),
                entries: Vec::new(),
            }
        }
    };

    // Index events by id (event_ptr or mtev) for O(1) lookup
    let event_id_col = if schema_type == "B" { "mtev" } else { "event_ptr" };
    let mut event_by_id: HashMap<i64, &LowerRow> = HashMap::new();
    for row in event_rows {
        if let Some(v) = row.get(event_id_col) {
            let id = safe_int(Some(v), 0);
            event_by_id.entry(id).or_insert(row);
        }
    }

    let get_all_events = || -> Vec<EventObj> {
        let sort_col = if schema_type == "B" { "mtevent" } else { "event_no" };
        if event_rows.is_empty() || !event_rows.iter().any(|r| r.contains_key(sort_col)) {
            return Vec::new();
        }
        let mut sorted: Vec<(i64, &LowerRow)> = event_rows
            .iter()
            .map(|r| (safe_int(r.get(sort_col), 0), r))
            .collect();
        sorted.sort_by_key(|(k, _)| *k);
        sorted
            .into_iter()
            .map(|(_, r)| create_event_from_row(r, "F"))
            .collect()
    };

    let sessitem_rows = tables.get("sessitem").map(|v| v.as_slice()).unwrap_or(&[]);

    let get_events_by_session = |session: &SessionObj| -> Vec<EventObj> {
        if session.is_default {
            return get_all_events();
        }
        let mut evts = Vec::new();
        if schema_type == "B" {
            if !event_rows.is_empty() && event_rows.iter().any(|r| r.contains_key("session")) {
                let mut matched: Vec<(i64, &LowerRow)> = event_rows
                    .iter()
                    .filter(|r| safe_int(r.get("session"), 0) == session.sess_id)
                    .map(|r| (safe_int(r.get("mtevent"), 0), r))
                    .collect();
                if event_rows.iter().any(|r| r.contains_key("mtevent")) {
                    matched.sort_by_key(|(k, _)| *k);
                }
                for (_, r) in matched {
                    evts.push(create_event_from_row(r, "F"));
                }
            }
        } else if !sessitem_rows.is_empty() && sessitem_rows.iter().any(|r| r.contains_key("sess_ptr")) {
            let mut items: Vec<(i64, &LowerRow)> = sessitem_rows
                .iter()
                .filter(|r| safe_int(r.get("sess_ptr"), 0) == session.sess_id)
                .map(|r| (safe_int(r.get("sess_order"), 0), r))
                .collect();
            if sessitem_rows.iter().any(|r| r.contains_key("sess_order")) {
                items.sort_by_key(|(k, _)| *k);
            }
            for (_, item) in items {
                let evt_ptr = safe_int(item.get("event_ptr"), 0);
                let round_ltr = get_val(item, "sess_rnd", "F");
                if let Some(&erow) = event_by_id.get(&evt_ptr) {
                    evts.push(create_event_from_row(erow, &round_ltr));
                }
            }
        }
        evts
    };

    let get_heat_lane_time = |round_ltr: &str, stroke: &str, row: &LowerRow| -> (i64, i64, String, String, i64, String, String) {
        let seed_time = safe_float(row.get("convseed_time"), 0.0);
        let pre_heat = safe_int(row.get("pre_heat"), 0);
        let pre_lane = safe_int(row.get("pre_lane"), 0);
        let pre_time = safe_float(row.get("pre_time"), 0.0);
        let pre_stat = get_val(row, "pre_stat", "").to_uppercase();
        let pre_dqcode = get_val(row, "pre_dqcode", "");

        let fin_heat = safe_int(row.get("fin_heat"), 0);
        let fin_lane = safe_int(row.get("fin_lane"), 0);
        let fin_time = safe_float(row.get("fin_time"), 0.0);
        let fin_stat = get_val(row, "fin_stat", "").to_uppercase();
        let fin_dqcode = get_val(row, "fin_dqcode", "");

        let mut seed_str = if seed_time > 0.0 {
            num_to_string(seed_time)
        } else {
            "NT".to_string()
        };
        let place_val = row.get("fin_place").or_else(|| row.get("place"));
        let place = safe_int(place_val, 0);

        let (heat, lane, status, dq_code, mut time_str) = if round_ltr == "P" {
            (
                pre_heat,
                pre_lane,
                normalize_status(&pre_stat),
                pre_dqcode,
                time_to_string(pre_time, &pre_stat),
            )
        } else {
            let h = if fin_heat != 0 { fin_heat } else { pre_heat };
            let l = if fin_lane != 0 { fin_lane } else { pre_lane };
            let use_fin = fin_heat != 0 || pre_heat == 0;
            let actual_time = if use_fin { fin_time } else { pre_time };
            let actual_stat = if use_fin { &fin_stat } else { &pre_stat };
            let actual_dq = if use_fin { fin_dqcode } else { pre_dqcode };
            (
                h,
                l,
                normalize_status(actual_stat),
                actual_dq,
                time_to_string(actual_time, actual_stat),
            )
        };

        if stroke != "Diving" {
            seed_str = time_to_min_sec(&seed_str);
            time_str = time_to_min_sec(&time_str);
        }

        (heat, lane, seed_str, time_str, place, status, dq_code)
    };

    let populate_event_entries = |event: &mut EventObj| {
        if event.is_relay {
            let Some(entries) = relay_grouped.get(&event.event_ptr) else {
                return;
            };
            if schema_type == "B" {
                for row in entries {
                    let score = safe_float(row.get("score"), 0.0);
                    let time_str = if score > 0.0 {
                        if score > 200.0 {
                            num_to_string(score / 100.0)
                        } else {
                            num_to_string(score)
                        }
                    } else {
                        "NT".to_string()
                    };
                    let team_no = safe_int(row.get("team"), 0);
                    let team_info = get_team(team_no);
                    let heat = safe_int(row.get("heat"), 0);
                    let lane = safe_int(row.get("lane"), 0);
                    let relay_ltr = get_val(row, "relay_ltr", "A");
                    let ath_id = safe_int(row.get("relay_no").or_else(|| row.get("relay")), 0);
                    event.entries.push((
                        heat,
                        lane,
                        json!({
                            "name": "Relay Team",
                            "team": team_info.name,
                            "teamCode": team_info.abbr,
                            "rawTeamCode": team_info.raw_abbr,
                            "heat": heat,
                            "lane": lane,
                            "seedTime": time_str,
                            "psTime": "NT",
                            "isRelay": true,
                            "relayLtr": relay_ltr,
                            "athleteId": ath_id,
                            "teamId": row.get("team").cloned().unwrap_or(Value::Null),
                            "members": [],
                        }),
                    ));
                }
            } else {
                for row in entries {
                    let (heat, lane, seed_str, time_str, place, status, dq_code) =
                        get_heat_lane_time(&event.round_ltr, &event.stroke, row);
                    if heat != 0 && lane != 0 {
                        let team_no = safe_int(row.get("team_no"), 0);
                        let team_info = get_team(team_no);
                        let relay_ltr = get_val(row, "team_ltr", "A");

                        let mut relay_athletes: Vec<Value> = Vec::new();
                        if !relaynames_rows.is_empty() {
                            for rn in relaynames_rows {
                                if rn_has_event_ptr && safe_int(rn.get("event_ptr"), 0) != event.event_ptr {
                                    continue;
                                }
                                if rn_has_team_no && safe_int(rn.get("team_no"), 0) != team_no {
                                    continue;
                                }
                                if rn_has_team_ltr && get_val(rn, "team_ltr", "") != relay_ltr {
                                    continue;
                                }
                                if rn_has_event_round && get_val(rn, "event_round", "") != event.round_ltr {
                                    continue;
                                }
                                let aid = safe_int(rn.get("ath_no"), 0);
                                if let Some(ath_obj) = athlete_map.get(&aid) {
                                    relay_athletes.push(ath_obj.clone());
                                }
                            }
                        }

                        let mut swimmers_list: Vec<String> = Vec::with_capacity(relay_athletes.len());
                        for a in &relay_athletes {
                            let fn_str = a.get("firstName").and_then(|v| v.as_str()).unwrap_or("");
                            let ln_str = a.get("lastName").and_then(|v| v.as_str()).unwrap_or("");
                            let init_ch = fn_str.chars().next().map(|c| c.to_string()).unwrap_or_default();
                            swimmers_list.push(format!("{}. {}", init_ch, ln_str));
                        }

                        let names_str = format!("{} {}", team_info.name, relay_ltr);
                        event.entries.push((
                            heat,
                            lane,
                            json!({
                                "name": names_str,
                                "team": team_info.name,
                                "teamCode": team_info.abbr,
                                "rawTeamCode": team_info.raw_abbr,
                                "heat": heat,
                                "lane": lane,
                                "seedTime": seed_str,
                                "psTime": time_str,
                                "finalTime": time_str,
                                "place": place,
                                "status": status,
                                "dqCode": dq_code,
                                "isRelay": true,
                                "athleteId": safe_int(row.get("relay_no"), 0),
                                "relayLtr": relay_ltr,
                                "relaySwimmers": swimmers_list,
                                "members": swimmers_list,
                                "relayAthletes": relay_athletes,
                                "teamId": team_no,
                            }),
                        ));
                    }
                }
            }
        } else {
            let Some(entries) = entry_grouped.get(&event.event_ptr) else {
                return;
            };
            if schema_type == "B" {
                for row in entries {
                    let score = safe_float(row.get("score"), 0.0);
                    let time_str = if score > 0.0 {
                        if score > 200.0 {
                            num_to_string(score / 100.0)
                        } else {
                            num_to_string(score)
                        }
                    } else {
                        "NT".to_string()
                    };
                    let ath_no = safe_int(row.get("athlete"), 0);
                    if let Some(athlete) = athlete_map.get(&ath_no) {
                        let heat = safe_int(row.get("heat"), 0);
                        let lane = safe_int(row.get("lane"), 0);
                        event.entries.push((
                            heat,
                            lane,
                            json!({
                                "name": athlete["name"],
                                "age": athlete["age"],
                                "athleteSex": athlete["athleteSex"],
                                "schoolYear": athlete["schoolYear"],
                                "team": athlete["teamName"],
                                "teamCode": athlete["teamCode"],
                                "rawTeamCode": athlete["rawTeamCode"],
                                "firstName": athlete["firstName"],
                                "lastName": athlete["lastName"],
                                "initial": athlete["initial"],
                                "heat": heat,
                                "lane": lane,
                                "seedTime": time_str,
                                "psTime": "NT",
                                "isRelay": false,
                                "athleteId": ath_no,
                                "teamId": athlete["teamId"],
                            }),
                        ));
                    }
                }
            } else {
                for row in entries {
                    let (heat, lane, seed_str, time_str, place, status, dq_code) =
                        get_heat_lane_time(&event.round_ltr, &event.stroke, row);
                    if heat != 0 && lane != 0 {
                        let ath_no = safe_int(row.get("ath_no"), 0);
                        if let Some(athlete) = athlete_map.get(&ath_no) {
                            event.entries.push((
                                heat,
                                lane,
                                json!({
                                    "name": athlete["name"],
                                    "age": athlete["age"],
                                    "athleteSex": athlete["athleteSex"],
                                    "schoolYear": athlete["schoolYear"],
                                    "team": athlete["teamName"],
                                    "teamCode": athlete["teamCode"],
                                    "rawTeamCode": athlete["rawTeamCode"],
                                    "firstName": athlete["firstName"],
                                    "lastName": athlete["lastName"],
                                    "initial": athlete["initial"],
                                    "heat": heat,
                                    "lane": lane,
                                    "seedTime": seed_str,
                                    "psTime": time_str,
                                    "finalTime": time_str,
                                    "place": place,
                                    "status": status,
                                    "dqCode": dq_code,
                                    "isRelay": false,
                                    "athleteId": ath_no,
                                    "teamId": athlete["teamId"],
                                }),
                            ));
                        }
                    }
                }
            }
        }
    };

    let mut meet_sessions_data: Vec<Value> = Vec::new();
    for session in &sessions {
        let mut events = get_events_by_session(session);
        let mut session_events_data: Vec<Value> = Vec::new();
        for mut event in events.drain(..) {
            event.create_description();
            populate_event_entries(&mut event);
            session_events_data.push(event.to_value());
        }
        if session_events_data.is_empty() && session.is_default {
            let mut all_evts = get_all_events();
            for mut event in all_evts.drain(..) {
                event.create_description();
                populate_event_entries(&mut event);
                session_events_data.push(event.to_value());
            }
        }
        let mut s_map = session.to_map();
        s_map.insert("events".to_string(), Value::Array(session_events_data));
        meet_sessions_data.push(Value::Object(s_map));
    }

    let has_any_linked_events = meet_sessions_data.iter().any(|s| {
        s.get("events")
            .and_then(|e| e.as_array())
            .map(|a| !a.is_empty())
            .unwrap_or(false)
    });
    if !has_any_linked_events && !event_rows.is_empty() {
        let default_session = SessionObj::default_session();
        let mut all_evts = get_all_events();
        let mut session_events_data = Vec::new();
        for mut event in all_evts.drain(..) {
            event.create_description();
            populate_event_entries(&mut event);
            session_events_data.push(event.to_value());
        }
        let mut ds_map = default_session.to_map();
        ds_map.insert("events".to_string(), Value::Array(session_events_data));
        meet_sessions_data.push(Value::Object(ds_map));
    }

    json!({
        "meetName": meet_name,
        "meetLocation": meet_loc,
        "meetStart": meet_start,
        "meetEnd": meet_end,
        "meetType": meet_type,
        "numLanes": num_lanes,
        "sessions": meet_sessions_data,
    })
}
