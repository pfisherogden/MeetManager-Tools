use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};
use std::collections::{BTreeMap, HashMap, HashSet};

pub const SEVERITY_INFO: i32 = 1;
pub const SEVERITY_WARNING: i32 = 2;
pub const SEVERITY_CRITICAL: i32 = 3;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FindingDto {
    pub severity: i32,
    pub category: String,
    pub message: String,
    pub affected_id: String,
}

pub fn get_table<'a>(cache: &'a Map<String, Value>, name: &str) -> &'a [Value] {
    if let Some(v) = cache.get(name).and_then(|v| v.as_array()) {
        return v.as_slice();
    }
    let lower_name = name.to_ascii_lowercase();
    if let Some(v) = cache.get(&lower_name).and_then(|v| v.as_array()) {
        return v.as_slice();
    }
    let plural = format!("{}s", lower_name);
    let singular = if lower_name.ends_with('s') && lower_name.len() > 1 {
        Some(&lower_name[..lower_name.len() - 1])
    } else {
        None
    };
    for (actual_key, val) in cache.iter() {
        let trimmed = actual_key.trim();
        if trimmed.eq_ignore_ascii_case(&lower_name)
            || trimmed.eq_ignore_ascii_case(&plural)
            || singular.map(|s| trimmed.eq_ignore_ascii_case(s)).unwrap_or(false)
        {
            if let Some(arr) = val.as_array() {
                return arr.as_slice();
            }
        }
    }
    &[]
}

pub fn get_field<'a>(d: &'a Map<String, Value>, keys: &[&str]) -> Option<&'a Value> {
    for &k in keys {
        if let Some(v) = d.get(k) {
            return Some(v);
        }
        let tk = k.trim();
        for (actual_key, val) in d.iter() {
            if actual_key.trim().eq_ignore_ascii_case(tk) {
                return Some(val);
            }
        }
    }
    None
}

pub fn safe_int(val: Option<&Value>, default: i64) -> i64 {
    match val {
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
            let trimmed = s.trim();
            if let Ok(i) = trimmed.parse::<i64>() {
                i
            } else if let Ok(f) = trimmed.parse::<f64>() {
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

pub fn safe_float(val: Option<&Value>, default: f64) -> f64 {
    match val {
        None | Some(Value::Null) => default,
        Some(Value::Number(n)) => n.as_f64().unwrap_or(default),
        Some(Value::String(s)) => s.trim().parse::<f64>().unwrap_or(default),
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

pub fn safe_str(val: Option<&Value>) -> String {
    match val {
        None | Some(Value::Null) => String::new(),
        Some(Value::String(s)) => {
            let trimmed = s.trim();
            let upper = trimmed.to_uppercase();
            if upper == "NAN" || upper == "NONE" || upper == "<NA>" {
                String::new()
            } else {
                trimmed.to_string()
            }
        }
        Some(Value::Number(n)) => {
            if let Some(f) = n.as_f64() {
                if f.is_nan() {
                    return String::new();
                }
            }
            n.to_string()
        }
        Some(Value::Bool(b)) => {
            if *b {
                "True".to_string()
            } else {
                "False".to_string()
            }
        }
        Some(other) => other.to_string(),
    }
}

pub fn is_truthy_value(val: Option<&Value>) -> bool {
    match val {
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

pub fn get_stroke_name(stroke_val: Option<&Value>, is_relay: bool) -> &'static str {
    let s = safe_str(stroke_val).to_uppercase();
    let Some(ch) = s.chars().next() else {
        return "Unknown";
    };
    match ch {
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
        _ => "Unknown",
    }
}

pub fn get_tvsl_age_group_index(age: i64) -> i32 {
    if age <= 6 {
        0
    } else if age <= 8 {
        1
    } else if age <= 10 {
        2
    } else if age <= 12 {
        3
    } else if age <= 14 {
        4
    } else {
        5
    }
}

fn map_gender_code(g: &str) -> Option<&'static str> {
    match g {
        "B" | "M" => Some("M"),
        "G" | "W" | "F" => Some("F"),
        _ => None,
    }
}

#[derive(Clone, Debug)]
struct TeamInfo {
    name: String,
    abbr: String,
    lsc: String,
}

#[derive(Clone, Debug)]
struct AthleteInfo {
    name: String,
    gender: String,
    age: i64,
    team_no: i64,
}

#[derive(Clone, Debug)]
struct EventInfo {
    sex: String,
    low_age: i64,
    high_age: i64,
    is_relay: bool,
    desc: String,
    dist: i64,
    stroke: Option<Value>,
}

#[derive(Clone, Debug)]
struct AthEntryItem {
    evt_id: i64,
    is_exhibition: bool,
    is_scratched: bool,
}

pub fn validate_meet_data_rs(root_cache: &Map<String, Value>) -> Vec<FindingDto> {
    let cache: &Map<String, Value> = if let Some(inner) = root_cache.get("data").and_then(|v| v.as_object()) {
        inner
    } else {
        root_cache
    };
    let mut findings = Vec::new();

    let athletes = get_table(cache, "athlete");
    let teams = get_table(cache, "team");
    let events = get_table(cache, "event");
    let entries = get_table(cache, "entry");
    let relays = get_table(cache, "relay");
    let relay_names = get_table(cache, "relaynames");
    let meet_table = get_table(cache, "meet");

    let mut is_champs = false;
    if let Some(meet_info) = meet_table.first().and_then(|v| v.as_object()) {
        let meet_name = safe_str(get_field(meet_info, &["meet_name1", "Meet_name1"])).to_lowercase();
        if meet_name.contains("championship") || meet_name.contains("champs") {
            is_champs = true;
        }
    }

    let mut teams_map: HashMap<i64, TeamInfo> = HashMap::new();
    for t_val in teams {
        let Some(t) = t_val.as_object() else { continue };
        let t_no = safe_int(get_field(t, &["team_no", "Team_no"]), 0);
        let t_name_val = get_field(t, &["team_name", "Team_name"]);
        let t_name = match t_name_val {
            None | Some(Value::Null) => "None".to_string(),
            Some(Value::String(s)) => s.clone(),
            Some(other) => other.to_string(),
        };
        let t_abbr = safe_str(get_field(t, &["team_abbr", "Team_abbr"]));
        let t_lsc_val = get_field(t, &["team_lsc", "Team_lsc"]);
        let t_lsc = safe_str(t_lsc_val);
        if t_no != 0 {
            teams_map.insert(
                t_no,
                TeamInfo {
                    name: t_name.clone(),
                    abbr: t_abbr,
                    lsc: t_lsc.clone(),
                },
            );
            if !is_truthy_value(t_lsc_val) || t_lsc.is_empty() {
                findings.push(FindingDto {
                    severity: SEVERITY_WARNING,
                    category: "Teams".to_string(),
                    message: format!("Team '{}' is missing an LSC code.", t_name),
                    affected_id: t_no.to_string(),
                });
            }
        }
    }

    let mut athletes_map: HashMap<i64, AthleteInfo> = HashMap::new();
    for ath_val in athletes {
        let Some(ath) = ath_val.as_object() else { continue };
        let ath_id = safe_int(get_field(ath, &["ath_no", "Ath_no"]), 0);
        if ath_id != 0 {
            let first = safe_str(get_field(ath, &["first_name", "First_name"]));
            let last = safe_str(get_field(ath, &["last_name", "Last_name"]));
            let combined = format!("{} {}", first, last).trim().to_string();
            let name = if combined.is_empty() {
                format!("Athlete #{}", ath_id)
            } else {
                combined
            };
            let gender = safe_str(get_field(ath, &["ath_sex", "Ath_sex"]));
            let age = safe_int(get_field(ath, &["ath_age", "Ath_age"]), 0);
            let team_no = safe_int(get_field(ath, &["team_no", "Team_no"]), 0);
            athletes_map.insert(
                ath_id,
                AthleteInfo {
                    name,
                    gender,
                    age,
                    team_no,
                },
            );
        }
    }

    let mut events_map: HashMap<i64, EventInfo> = HashMap::new();
    for e_val in events {
        let Some(e) = e_val.as_object() else { continue };
        let ptr_val = get_field(e, &["event_ptr", "Event_ptr"]);
        let e_ptr_raw = if is_truthy_value(ptr_val) {
            ptr_val
        } else {
            get_field(e, &["event_no", "Event_no"])
        };
        let e_ptr = safe_int(e_ptr_raw, 0);
        if e_ptr != 0 {
            let ev_no_val = get_field(e, &["event_no", "Event_no"]);
            let ev_no_str = match ev_no_val {
                None | Some(Value::Null) => "None".to_string(),
                Some(Value::String(s)) => s.clone(),
                Some(other) => other.to_string(),
            };
            events_map.insert(
                e_ptr,
                EventInfo {
                    sex: safe_str(get_field(e, &["event_sex", "Event_sex"])),
                    low_age: safe_int(get_field(e, &["low_age", "Low_age"]), 0),
                    high_age: safe_int(get_field(e, &["high_age", "High_age"]), 0),
                    is_relay: safe_str(get_field(e, &["ind_rel", "Ind_rel"])).to_uppercase() == "R",
                    desc: format!("Event {}", ev_no_str),
                    dist: safe_int(get_field(e, &["event_dist", "Event_dist"]), 0),
                    stroke: get_field(e, &["event_stroke", "Event_stroke"]).cloned(),
                },
            );
        }
    }

    let mut athlete_entries: HashMap<i64, Vec<AthEntryItem>> = HashMap::new();
    let mut event_times: Vec<(i64, Vec<(i64, i64, i64, String, f64)>)> = Vec::new();
    let mut event_times_idx: HashMap<i64, usize> = HashMap::new();

    for entry_val in entries {
        let Some(entry) = entry_val.as_object() else { continue };
        let ath_id = safe_int(get_field(entry, &["ath_no", "Ath_no"]), 0);
        let ptr_val = get_field(entry, &["event_ptr", "Event_ptr"]);
        let evt_raw = if is_truthy_value(ptr_val) {
            ptr_val
        } else {
            get_field(entry, &["event_no", "Event_no"])
        };
        let evt_id = safe_int(evt_raw, 0);
        let pre_exh = safe_str(get_field(entry, &["pre_exh", "Pre_exh"])).to_uppercase();
        let fin_exh = safe_str(get_field(entry, &["fin_exh", "Fin_exh"])).to_uppercase();
        let is_exh = !pre_exh.is_empty() || !fin_exh.is_empty();

        let scr_stat = safe_int(get_field(entry, &["scr_stat", "Scr_stat"]), 0);
        let fin_stat = safe_str(get_field(entry, &["fin_stat", "Fin_stat"])).to_uppercase();
        let pre_stat = safe_str(get_field(entry, &["pre_stat", "Pre_stat"])).to_uppercase();
        let is_scr =
            scr_stat == 1 || fin_stat == "R" || fin_stat == "NS" || pre_stat == "R" || pre_stat == "NS";

        if ath_id != 0 && evt_id != 0 {
            athlete_entries.entry(ath_id).or_default().push(AthEntryItem {
                evt_id,
                is_exhibition: is_exh,
                is_scratched: is_scr,
            });
        }
    }

    let mut relay_exh_map: HashMap<(i64, i64, i64), bool> = HashMap::new();
    let mut relay_scratched_map: HashMap<(i64, i64, i64), bool> = HashMap::new();
    for r_val in relays {
        let Some(r) = r_val.as_object() else { continue };
        let evt_id = safe_int(get_field(r, &["event_ptr", "Event_ptr"]), 0);
        let t_no = safe_int(get_field(r, &["team_ptr", "team_no", "Team_ptr", "Team_no"]), 0);
        let r_no = safe_int(get_field(r, &["relay_no", "Relay_no"]), 0);
        let pre_exh = safe_str(get_field(r, &["pre_exh", "Pre_exh"])).to_uppercase();
        let fin_exh = safe_str(get_field(r, &["fin_exh", "Fin_exh"])).to_uppercase();
        let is_exh = !pre_exh.is_empty() || !fin_exh.is_empty();
        relay_exh_map.insert((evt_id, t_no, r_no), is_exh);

        let fin_stat = safe_str(get_field(r, &["fin_stat", "Fin_stat"])).to_uppercase();
        let pre_stat = safe_str(get_field(r, &["pre_stat", "Pre_stat"])).to_uppercase();
        let is_scr = fin_stat == "R" || fin_stat == "NS" || pre_stat == "R" || pre_stat == "NS";
        relay_scratched_map.insert((evt_id, t_no, r_no), is_scr);
    }

    for rn_val in relay_names {
        let Some(rn) = rn_val.as_object() else { continue };
        let ath_id = safe_int(get_field(rn, &["ath_no", "Ath_no"]), 0);
        let evt_id = safe_int(get_field(rn, &["event_ptr", "Event_ptr"]), 0);
        let t_no = safe_int(get_field(rn, &["team_no", "Team_no"]), 0);
        let r_no = safe_int(get_field(rn, &["relay_no", "Relay_no"]), 0);
        let pos_no = safe_int(get_field(rn, &["pos_no", "pos", "Pos_no", "Pos"]), 0);
        if pos_no > 4 {
            continue;
        }
        if ath_id != 0 && evt_id != 0 {
            let is_exh = *relay_exh_map.get(&(evt_id, t_no, r_no)).unwrap_or(&false);
            let is_scr = *relay_scratched_map.get(&(evt_id, t_no, r_no)).unwrap_or(&false);
            athlete_entries.entry(ath_id).or_default().push(AthEntryItem {
                evt_id,
                is_exhibition: is_exh,
                is_scratched: is_scr,
            });
        }
    }

    let mut fastest_older: HashMap<(String, i64, &'static str), f64> = HashMap::new();
    let mut athlete_has_valid_time: HashSet<i64> = HashSet::new();
    for entry_val in entries {
        let Some(entry) = entry_val.as_object() else { continue };
        let ath_id = safe_int(get_field(entry, &["ath_no", "Ath_no"]), 0);
        let ptr_val = get_field(entry, &["event_ptr", "Event_ptr"]);
        let evt_raw = if is_truthy_value(ptr_val) {
            ptr_val
        } else {
            get_field(entry, &["event_no", "Event_no"])
        };
        let evt_id = safe_int(evt_raw, 0);
        let fin_time = safe_float(get_field(entry, &["fin_time", "Fin_time"]), 0.0);
        let fin_stat = safe_str(get_field(entry, &["fin_stat", "Fin_stat"])).to_uppercase();
        let fin_dq = safe_str(get_field(entry, &["fin_dqcode", "Fin_dqcode"])).to_uppercase();
        let is_dfs_dq = fin_stat == "Q" && fin_dq.starts_with('7');
        if fin_time > 0.0 && fin_stat != "R" && fin_stat != "NS" && !is_dfs_dq {
            athlete_has_valid_time.insert(ath_id);
            if let Some(ath_info) = athletes_map.get(&ath_id) {
                if (15..=18).contains(&ath_info.age) {
                    if let Some(evt_info) = events_map.get(&evt_id) {
                        let stroke_name = get_stroke_name(evt_info.stroke.as_ref(), false);
                        let key = (ath_info.gender.trim().to_uppercase(), evt_info.dist, stroke_name);
                        fastest_older
                            .entry(key)
                            .and_modify(|e| {
                                if fin_time < *e {
                                    *e = fin_time;
                                }
                            })
                            .or_insert(fin_time);
                    }
                }
            }
        }
    }

    for entry_val in entries {
        let Some(entry) = entry_val.as_object() else { continue };
        let ath_id = safe_int(get_field(entry, &["ath_no", "Ath_no"]), 0);
        let ptr_val = get_field(entry, &["event_ptr", "Event_ptr"]);
        let evt_raw = if is_truthy_value(ptr_val) {
            ptr_val
        } else {
            get_field(entry, &["event_no", "Event_no"])
        };
        let evt_id = safe_int(evt_raw, 0);

        let fin_time = safe_float(get_field(entry, &["fin_time", "Fin_time"]), 0.0);
        let fin_stat = safe_str(get_field(entry, &["fin_stat", "Fin_stat"])).to_uppercase();
        let fin_heat = safe_int(get_field(entry, &["fin_heat", "Fin_heat"]), 0);
        let fin_lane = safe_int(get_field(entry, &["fin_lane", "Fin_lane"]), 0);
        let ev_score = safe_float(get_field(entry, &["ev_score", "Ev_score"]), 0.0);
        let scr_stat = safe_int(get_field(entry, &["scr_stat", "Scr_stat"]), 0);
        let place = safe_int(get_field(entry, &["fin_place", "place", "Fin_place"]), 0);

        let ath_opt = athletes_map.get(&ath_id);
        let t_no = ath_opt.map(|a| a.team_no).unwrap_or(0);
        let t_code = teams_map
            .get(&t_no)
            .map(|t| {
                if !t.abbr.is_empty() {
                    t.abbr.as_str()
                } else {
                    t.lsc.as_str()
                }
            })
            .unwrap_or("");
        let base_ath_name = ath_opt
            .map(|a| a.name.clone())
            .unwrap_or_else(|| format!("Swimmer #{}", ath_id));
        let ath_name = if !t_code.is_empty() {
            format!("{} [{}]", base_ath_name, t_code)
        } else {
            base_ath_name
        };
        let evt_opt = events_map.get(&evt_id);
        let evt_desc = evt_opt
            .map(|e| e.desc.clone())
            .unwrap_or_else(|| format!("Event {}", evt_id));

        if fin_heat > 0 && fin_lane > 0 {
            if fin_time > 0.0 {
                let idx = *event_times_idx.entry(evt_id).or_insert_with(|| {
                    let i = event_times.len();
                    event_times.push((evt_id, Vec::new()));
                    i
                });
                let time_bits = fin_time.to_bits() as i64;
                event_times[idx]
                    .1
                    .push((time_bits, fin_heat, fin_lane, ath_name.clone(), fin_time));
            }

            if fin_stat == "Q" && ev_score > 0.0 {
                findings.push(FindingDto {
                    severity: SEVERITY_CRITICAL,
                    category: "Points on DQs".to_string(),
                    message: format!(
                        "{} in {} (Heat {}, Lane {}): DQ status but awarded {:.1} points!",
                        ath_name, evt_desc, fin_heat, fin_lane, ev_score
                    ),
                    affected_id: ath_id.to_string(),
                });
            }

            let is_scored = (place > 0) || (!fin_stat.is_empty());
            if is_scored && fin_time == 0.0 && fin_stat != "Q" && fin_stat != "R" {
                findings.push(FindingDto {
                    severity: SEVERITY_INFO,
                    category: "0 Backup Timers".to_string(),
                    message: format!(
                        "{} in {} (Heat {}, Lane {}): 0 backup timers (NS/Missing Time).",
                        ath_name, evt_desc, fin_heat, fin_lane
                    ),
                    affected_id: ath_id.to_string(),
                });
            } else if fin_time > 0.0 {
                let back1 = safe_float(get_field(entry, &["fin_back1", "Fin_back1"]), 0.0);
                let back2 = safe_float(get_field(entry, &["fin_back2", "Fin_back2"]), 0.0);
                let back3 = safe_float(get_field(entry, &["fin_back3", "Fin_back3"]), 0.0);
                let num_backups =
                    (if back1 > 0.0 { 1 } else { 0 }) + (if back2 > 0.0 { 1 } else { 0 }) + (if back3 > 0.0 { 1 } else { 0 });
                if num_backups == 1 {
                    findings.push(FindingDto {
                        severity: SEVERITY_WARNING,
                        category: "1 Backup Timer".to_string(),
                        message: format!(
                            "{} in {} (Heat {}, Lane {}): Only 1 backup timer recorded (Time: {:.2}s).",
                            ath_name, evt_desc, fin_heat, fin_lane, fin_time
                        ),
                        affected_id: ath_id.to_string(),
                    });
                }
            }
        }

        if fin_stat == "R" || scr_stat == 1 {
            let back1 = safe_float(get_field(entry, &["fin_back1", "Fin_back1"]), 0.0);
            let back2 = safe_float(get_field(entry, &["fin_back2", "Fin_back2"]), 0.0);
            let back3 = safe_float(get_field(entry, &["fin_back3", "Fin_back3"]), 0.0);
            if fin_time > 0.0 || back1 > 0.0 || back2 > 0.0 || back3 > 0.0 {
                findings.push(FindingDto {
                    severity: SEVERITY_CRITICAL,
                    category: "Scratched with Time".to_string(),
                    message: format!(
                        "{} in {} (Heat {}, Lane {}): Scratched but has time {:.2}s.",
                        ath_name, evt_desc, fin_heat, fin_lane, fin_time
                    ),
                    affected_id: ath_id.to_string(),
                });
            }
        }

        if athlete_has_valid_time.contains(&ath_id) {
            let is_ns = fin_stat == "NS";
            let is_scratch = fin_stat == "R" || scr_stat == 1;
            let fin_dq = safe_str(get_field(entry, &["fin_dqcode", "Fin_dqcode"])).to_uppercase();
            let is_dfs_dq = fin_stat == "Q" && fin_dq.starts_with('7');
            if is_ns || is_scratch || is_dfs_dq {
                let loc = if fin_heat > 0 && fin_lane > 0 {
                    format!(" (Heat {}, Lane {})", fin_heat, fin_lane)
                } else {
                    String::new()
                };
                findings.push(FindingDto {
                    severity: SEVERITY_WARNING,
                    category: "NS/Scratch with Times".to_string(),
                    message: format!(
                        "{} in {}{}: Swimmer marked as NS/Scratch/DQ-7 but has valid times in other events.",
                        ath_name, evt_desc, loc
                    ),
                    affected_id: ath_id.to_string(),
                });
            }
        }

        if fin_time > 0.0 {
            let actualseed_time = safe_float(get_field(entry, &["actualseed_time", "actual_seed"]), 0.0);
            if actualseed_time > 0.0 {
                let age = ath_opt.map(|a| a.age).unwrap_or(0);
                if age >= 9 {
                    let diff = (fin_time - actualseed_time).abs();
                    if diff > 10.0 {
                        let direction = if fin_time < actualseed_time {
                            "Improvement"
                        } else {
                            "Regression"
                        };
                        findings.push(FindingDto {
                            severity: SEVERITY_WARNING,
                            category: "Wild Times".to_string(),
                            message: format!(
                                "{} (Age {}) in {}: Seed {:.2}s vs Final {:.2}s ({} of {:.2}s).",
                                ath_name, age, evt_desc, actualseed_time, fin_time, direction, diff
                            ),
                            affected_id: ath_id.to_string(),
                        });
                    }
                }
            }
        }

        if fin_time > 0.0 && fin_stat != "Q" && fin_stat != "R" {
            let age = ath_opt.map(|a| a.age).unwrap_or(0);
            let gender = ath_opt
                .map(|a| a.gender.trim().to_uppercase())
                .unwrap_or_default();
            if age > 0 && age < 11 {
                if let Some(evt) = evt_opt {
                    let dist = evt.dist;
                    let stroke_name = get_stroke_name(evt.stroke.as_ref(), false);
                    let dynamic_key = (gender.clone(), dist, stroke_name);
                    let mut target_limit: Option<f64> = None;
                    let mut source = String::new();

                    if let Some(&lim) = fastest_older.get(&dynamic_key) {
                        target_limit = Some(lim);
                        source = format!("fastest 15-18 in meet ({:.2}s)", lim);
                    } else if dist == 25 {
                        let static_lim = match (gender.as_str(), stroke_name) {
                            ("F", "Freestyle") => Some(13.50),
                            ("M", "Freestyle") => Some(12.00),
                            ("F", "Backstroke") => Some(16.00),
                            ("M", "Backstroke") => Some(15.00),
                            ("F", "Breaststroke") => Some(18.00),
                            ("M", "Breaststroke") => Some(16.50),
                            ("F", "Butterfly") => Some(14.50),
                            ("M", "Butterfly") => Some(13.50),
                            _ => None,
                        };
                        if let Some(lim) = static_lim {
                            target_limit = Some(lim);
                            source = format!("static standard ({:.2}s)", lim);
                        }
                    }

                    if let Some(lim) = target_limit {
                        if lim > 0.0 && fin_time <= lim {
                            findings.push(FindingDto {
                                severity: SEVERITY_WARNING,
                                category: "Fast Times".to_string(),
                                message: format!(
                                    "{} (Age {}) in {}: Time {:.2}s is faster than/equal to {} limit.",
                                    ath_name, age, evt_desc, fin_time, source
                                ),
                                affected_id: ath_id.to_string(),
                            });
                        }
                    }
                }
            }
        }
    }

    // 4. Relays with NS
    for r_val in relays {
        let Some(r) = r_val.as_object() else { continue };
        let r_heat = safe_int(get_field(r, &["fin_heat", "Fin_heat"]), 0);
        let r_lane = safe_int(get_field(r, &["fin_lane", "Fin_lane"]), 0);
        if r_heat > 0 && r_lane > 0 {
            let r_place = safe_int(get_field(r, &["fin_place", "place", "Fin_place"]), 0);
            let r_stat = safe_str(get_field(r, &["fin_stat", "Fin_stat"])).to_uppercase();
            let is_scored = (r_place > 0) || (!r_stat.is_empty());
            if is_scored {
                let r_time = safe_float(get_field(r, &["fin_time", "Fin_time"]), 0.0);
                if r_time == 0.0 && r_stat != "Q" && r_stat != "R" {
                    let t_id = safe_int(get_field(r, &["team_ptr", "team_no", "Team_ptr", "Team_no"]), 0);
                    let team_name = teams_map
                        .get(&t_id)
                        .map(|t| t.name.clone())
                        .unwrap_or_else(|| format!("Team #{}", t_id));
                    let team_ltr = safe_str(get_field(r, &["team_ltr", "Team_ltr"]));
                    let evt_id = safe_int(get_field(r, &["event_ptr", "Event_ptr"]), 0);
                    let evt_desc = events_map
                        .get(&evt_id)
                        .map(|e| e.desc.clone())
                        .unwrap_or_else(|| format!("Event {}", evt_id));
                    findings.push(FindingDto {
                        severity: SEVERITY_INFO,
                        category: "Relays with NS".to_string(),
                        message: format!(
                            "Team {} '{}' in {} (Heat {}, Lane {}): Relay has NS/Missing Time.",
                            team_name, team_ltr, evt_desc, r_heat, r_lane
                        ),
                        affected_id: t_id.to_string(),
                    });
                }
            }
        }
    }

    // 5. Duplicate Times
    for (evt_id, times_list) in event_times {
        let mut time_order: Vec<i64> = Vec::new();
        let mut time_to_entries: HashMap<i64, (f64, Vec<(i64, i64, String)>)> = HashMap::new();
        for (time_bits, heat, lane, name, time_val) in times_list {
            let entry = time_to_entries.entry(time_bits).or_insert_with(|| {
                time_order.push(time_bits);
                (time_val, Vec::new())
            });
            entry.1.push((heat, lane, name));
        }
        for time_bits in time_order {
            let (time_val, entries_at_time) = &time_to_entries[&time_bits];
            let heats: HashSet<i64> = entries_at_time.iter().map(|(h, _, _)| *h).collect();
            if heats.len() > 1 {
                let evt_desc = events_map
                    .get(&evt_id)
                    .map(|e| e.desc.clone())
                    .unwrap_or_else(|| format!("Event {}", evt_id));
                let swimmers_info: Vec<String> = entries_at_time
                    .iter()
                    .map(|(h, l, n)| format!("{} (Heat {}, Lane {})", n, h, l))
                    .collect();
                findings.push(FindingDto {
                    severity: SEVERITY_WARNING,
                    category: "Duplicate Times".to_string(),
                    message: format!(
                        "{}: Time {:.2}s matches exactly in different heats: {}.",
                        evt_desc,
                        time_val,
                        swimmers_info.join(", ")
                    ),
                    affected_id: evt_id.to_string(),
                });
            }
        }
    }

    // 1. Athlete Validations
    for ath_val in athletes {
        let Some(ath) = ath_val.as_object() else { continue };
        let ath_id = safe_int(get_field(ath, &["ath_no", "Ath_no"]), 0);
        let ath_info = athletes_map.get(&ath_id);
        let t_no = ath_info.map(|a| a.team_no).unwrap_or(0);
        let t_code = teams_map
            .get(&t_no)
            .map(|t| {
                if !t.abbr.is_empty() {
                    t.abbr.as_str()
                } else {
                    t.lsc.as_str()
                }
            })
            .unwrap_or("");
        let base_name = ath_info
            .map(|a| a.name.clone())
            .unwrap_or_else(|| format!("Swimmer #{}", ath_id));
        let name = if !t_code.is_empty() {
            format!("{} [{}]", base_name, t_code)
        } else {
            base_name
        };
        let gender = ath_info.map(|a| a.gender.as_str()).unwrap_or("");
        let age = ath_info.map(|a| a.age).unwrap_or(0);

        if gender.is_empty() || !matches!(gender, "M" | "F" | "B" | "G" | "W") {
            findings.push(FindingDto {
                severity: SEVERITY_CRITICAL,
                category: "Athletes".to_string(),
                message: format!(
                    "Swimmer {} has an invalid or missing gender code: '{}'.",
                    name, gender
                ),
                affected_id: ath_id.to_string(),
            });
        }

        if t_no == 0 || !teams_map.contains_key(&t_no) {
            findings.push(FindingDto {
                severity: SEVERITY_CRITICAL,
                category: "Athletes".to_string(),
                message: format!(
                    "Swimmer {} is associated with a missing team ID: {}.",
                    name, t_no
                ),
                affected_id: ath_id.to_string(),
            });
        }

        let ath_evts = athlete_entries.get(&ath_id).map(|v| v.as_slice()).unwrap_or(&[]);
        let mut ind_count = 0;
        let mut rel_count = 0;
        for item in ath_evts {
            if item.is_scratched || item.is_exhibition {
                continue;
            }
            if let Some(evt_info) = events_map.get(&item.evt_id) {
                if evt_info.is_relay {
                    rel_count += 1;
                } else {
                    ind_count += 1;
                }

                let evt_sex = map_gender_code(&evt_info.sex);
                let ath_sex = map_gender_code(gender);
                if let (Some(es), Some(as_)) = (evt_sex, ath_sex) {
                    if es != as_ && evt_info.sex != "X" {
                        findings.push(FindingDto {
                            severity: SEVERITY_WARNING,
                            category: "Entries".to_string(),
                            message: format!(
                                "Swimmer {} ({}) entered in single-sex event {} ({}).",
                                name, gender, evt_info.desc, evt_info.sex
                            ),
                            affected_id: ath_id.to_string(),
                        });
                    }
                }

                let low = evt_info.low_age;
                let high = evt_info.high_age;
                if high > 0 && age > high {
                    findings.push(FindingDto {
                        severity: SEVERITY_WARNING,
                        category: "Entries".to_string(),
                        message: format!(
                            "Swimmer {} (age {}) entered in Event {} restricted to younger swimmers (max age: {}).",
                            name, age, evt_info.desc, high
                        ),
                        affected_id: ath_id.to_string(),
                    });
                } else if low > 0 && age < low {
                    if !evt_info.is_relay {
                        findings.push(FindingDto {
                            severity: SEVERITY_WARNING,
                            category: "Swim Up Limit".to_string(),
                            message: format!(
                                "Swimmer {} (age {}) is swimming up in individual Event {} (restricted to ages {}-{}), which is not permitted under TVSL Rule 13.",
                                name, age, evt_info.desc, low, high
                            ),
                            affected_id: ath_id.to_string(),
                        });
                    } else {
                        let event_group_idx = get_tvsl_age_group_index(high);
                        let swimmer_group_idx = get_tvsl_age_group_index(age);
                        if event_group_idx > swimmer_group_idx + 1 {
                            findings.push(FindingDto {
                                severity: SEVERITY_WARNING,
                                category: "Swim Up Limit".to_string(),
                                message: format!(
                                    "Swimmer {} (age {}) is swimming up too far in relay Event {} (restricted to ages {}-{}), exceeding the max one age group up limit under TVSL Rule 14a.",
                                    name, age, evt_info.desc, low, high
                                ),
                                affected_id: ath_id.to_string(),
                            });
                        }
                    }
                }
            }
        }

        if ind_count > 3 {
            findings.push(FindingDto {
                severity: SEVERITY_WARNING,
                category: "Rules Limit".to_string(),
                message: format!(
                    "Swimmer {} exceeds TVSL limits with {} individual entries (Rule 12 max: 3).",
                    name, ind_count
                ),
                affected_id: ath_id.to_string(),
            });
        }
        if rel_count > 2 {
            findings.push(FindingDto {
                severity: SEVERITY_WARNING,
                category: "Rules Limit".to_string(),
                message: format!(
                    "Swimmer {} exceeds relay limits with {} relay entries (max: 2).",
                    name, rel_count
                ),
                affected_id: ath_id.to_string(),
            });
        }
        if (ind_count + rel_count) > 4 {
            findings.push(FindingDto {
                severity: SEVERITY_WARNING,
                category: "Rules Limit".to_string(),
                message: format!(
                    "Swimmer {} exceeds total entry limits with {} total entries (max: 4).",
                    name,
                    ind_count + rel_count
                ),
                affected_id: ath_id.to_string(),
            });
        }
        if is_champs && (ind_count + rel_count) == 1 {
            let mut single_event_desc = "Unknown".to_string();
            for item in ath_evts {
                if !item.is_scratched && !item.is_exhibition {
                    if let Some(evt_info) = events_map.get(&item.evt_id) {
                        single_event_desc = evt_info.desc.clone();
                        break;
                    }
                }
            }
            findings.push(FindingDto {
                severity: SEVERITY_WARNING,
                category: "Champs Single Entry".to_string(),
                message: format!(
                    "Swimmer {} is entered in only 1 event ({}) in Championship meet.",
                    name, single_event_desc
                ),
                affected_id: ath_id.to_string(),
            });
        }
    }

    // 2. Team Splashes Validation (preserve insertion order of teams encountered)
    let mut team_splashes_order: Vec<i64> = Vec::new();
    let mut team_splashes: BTreeMap<i64, i64> = BTreeMap::new();

    for entry_val in entries {
        let Some(entry) = entry_val.as_object() else { continue };
        let ath_id = safe_int(get_field(entry, &["ath_no", "Ath_no"]), 0);
        let fin_stat = safe_str(get_field(entry, &["fin_stat", "Fin_stat"])).to_uppercase();
        let pre_stat = safe_str(get_field(entry, &["pre_stat", "Pre_stat"])).to_uppercase();
        let scr_stat = safe_int(get_field(entry, &["scr_stat", "Scr_stat"]), 0);
        if fin_stat == "R" || fin_stat == "NS" || pre_stat == "R" || pre_stat == "NS" || scr_stat == 1 {
            continue;
        }
        if let Some(ath_info) = athletes_map.get(&ath_id) {
            if ath_info.team_no != 0 {
                if !team_splashes.contains_key(&ath_info.team_no) {
                    team_splashes_order.push(ath_info.team_no);
                }
                *team_splashes.entry(ath_info.team_no).or_insert(0) += 1;
            }
        }
    }

    for r_val in relays {
        let Some(r) = r_val.as_object() else { continue };
        let t_no = safe_int(get_field(r, &["team_ptr", "team_no", "Team_ptr", "Team_no"]), 0);
        let fin_stat = safe_str(get_field(r, &["fin_stat", "Fin_stat"])).to_uppercase();
        let pre_stat = safe_str(get_field(r, &["pre_stat", "Pre_stat"])).to_uppercase();
        if fin_stat == "R" || fin_stat == "NS" || pre_stat == "R" || pre_stat == "NS" {
            continue;
        }
        if t_no != 0 {
            if !team_splashes.contains_key(&t_no) {
                team_splashes_order.push(t_no);
            }
            *team_splashes.entry(t_no).or_insert(0) += 4;
        }
    }

    for t_no in team_splashes_order {
        let count = team_splashes[&t_no];
        if count > 420 {
            let t_name = teams_map
                .get(&t_no)
                .map(|t| t.name.clone())
                .unwrap_or_else(|| format!("Team #{}", t_no));
            findings.push(FindingDto {
                severity: SEVERITY_WARNING,
                category: "Splashes Limit".to_string(),
                message: format!(
                    "Team {} exceeds splashes limit with {} splashes (max: 420).",
                    t_name, count
                ),
                affected_id: t_no.to_string(),
            });
        }
    }

    findings
}
