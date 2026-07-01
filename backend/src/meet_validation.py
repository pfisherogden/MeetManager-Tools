from __future__ import annotations

import collections
import math
from typing import Any

# Import generated classes
try:
    from meetmanager.v1 import meet_manager_pb2 as pb2
except ImportError:
    # Fallback to ignore during codegen bootstrap
    import typing

    pb2 = typing.cast(Any, None)


def get_table(cache: dict[str, Any] | None, name: str) -> list[dict[str, Any]]:
    """Helper to retrieve a table from cache with case-insensitive key lookup."""
    if not cache:
        return []

    # Try direct lookup first (most common)
    if name in cache:
        return cache[name]

    # Try lowercase lookup (normalized by MmToJsonConverter)
    lower_name = name.lower()
    if lower_name in cache:
        return cache[lower_name]

    # Try plural/singular variations
    variations = [lower_name, lower_name + "s"]
    if lower_name.endswith("s"):
        variations.append(lower_name[:-1])

    # Exhaustive case-insensitive search
    for actual_key in cache.keys():
        lower_actual = actual_key.lower().strip()
        if lower_actual in variations:
            return cache[actual_key]

    return []


def get_field(d: dict[str, Any] | None, keys: list[str], default: Any = None) -> Any:
    """Case-insensitive lookup for a list of potential field keys in a dictionary."""
    if not d:
        return default
    for k in keys:
        if k in d:
            return d[k]
        # Case-insensitive scan
        lower_k = k.lower().strip()
        for actual_key in d.keys():
            if actual_key.lower().strip() == lower_k:
                return d[actual_key]
    return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    # Check for pandas/numpy float NaN
    if isinstance(value, float) and math.isnan(value):
        return ""
    val_str = str(value).strip()
    if val_str.upper() in ["NAN", "NONE", "<NA>"]:
        return ""
    return val_str


def get_stroke_name(stroke_val: Any, is_relay: bool) -> str:
    s = str(stroke_val or "").strip().upper()
    if not s:
        return "Unknown"
    char = s[0]
    if char in ["1", "A"]:
        return "Freestyle"
    if char in ["2", "B"]:
        return "Backstroke"
    if char in ["3", "C"]:
        return "Breaststroke"
    if char in ["4", "D"]:
        return "Butterfly"
    if char in ["5", "E"]:
        return "Medley" if is_relay else "Individual Medley"
    return "Unknown"


def validate_meet_data(cache: dict[str, Any]) -> list[Any]:
    """Validate the active dataset for registry anomalies and rules violations."""
    findings = []

    # Retrieve tables safely (case-insensitive)
    athletes = get_table(cache, "athlete")
    teams = get_table(cache, "team")
    events = get_table(cache, "event")
    entries = get_table(cache, "entry")
    relays = get_table(cache, "relay")
    relay_names = get_table(cache, "relaynames")

    # Build lookups
    teams_map = {}
    for t in teams:
        t_no = safe_int(get_field(t, ["team_no", "Team_no"]))
        t_name = get_field(t, ["team_name", "Team_name"])
        t_lsc = get_field(t, ["team_lsc", "Team_lsc"])
        if t_no:
            teams_map[t_no] = {"name": t_name, "lsc": t_lsc}
            # WARNING: Check for missing LSC code
            if not t_lsc or not str(t_lsc).strip():
                findings.append(
                    pb2.ValidationFinding(
                        severity=pb2.VALIDATION_SEVERITY_WARNING,
                        category="Teams",
                        message=f"Team '{t_name}' is missing an LSC code.",
                        affected_id=str(t_no),
                    )
                )

    athletes_map = {}
    for ath in athletes:
        ath_id = safe_int(get_field(ath, ["ath_no", "Ath_no"]))
        if ath_id:
            first = str(get_field(ath, ["first_name", "First_name"]) or "").strip()
            last = str(get_field(ath, ["last_name", "Last_name"]) or "").strip()
            athletes_map[ath_id] = {
                "name": f"{first} {last}".strip() or f"Athlete #{ath_id}",
                "gender": str(get_field(ath, ["ath_sex", "Ath_sex"]) or "").strip(),
                "age": safe_int(get_field(ath, ["ath_age", "Ath_age"])),
                "team_no": safe_int(get_field(ath, ["team_no", "Team_no"])),
            }

    events_map = {}
    gender_map = {"B": "M", "G": "F", "M": "M", "W": "F", "F": "F"}
    for e in events:
        e_ptr = safe_int(get_field(e, ["event_ptr", "Event_ptr"]) or get_field(e, ["event_no", "Event_no"]))
        if e_ptr:
            events_map[e_ptr] = {
                "sex": str(get_field(e, ["event_sex", "Event_sex"]) or "").strip(),
                "low_age": safe_int(get_field(e, ["low_age", "Low_age"])),
                "high_age": safe_int(get_field(e, ["high_age", "High_age"])),
                "is_relay": safe_str(get_field(e, ["ind_rel", "Ind_rel"])).upper() == "R",
                "desc": f"Event {get_field(e, ['event_no', 'Event_no'])}",
                "dist": safe_int(get_field(e, ["event_dist", "Event_dist"])),
                "stroke": get_field(e, ["event_stroke", "Event_stroke"]),
            }

    # Map entries by athlete: maps ath_id -> list of dict {"evt_id": evt_id, "is_exhibition": bool}
    athlete_entries: dict[int, list[dict[str, Any]]] = collections.defaultdict(list)
    event_times: dict[int, list[tuple[float, int, int, str]]] = collections.defaultdict(list)

    # 1. Map individual entries to athlete_entries
    for entry in entries:
        ath_id = safe_int(get_field(entry, ["ath_no", "Ath_no"]))
        evt_id = safe_int(get_field(entry, ["event_ptr", "Event_ptr"]) or get_field(entry, ["event_no", "Event_no"]))
        pre_exh = safe_str(get_field(entry, ["pre_exh", "Pre_exh"])).upper()
        fin_exh = safe_str(get_field(entry, ["fin_exh", "Fin_exh"])).upper()
        is_exh = pre_exh != "" or fin_exh != ""

        if ath_id and evt_id:
            athlete_entries[ath_id].append({"evt_id": evt_id, "is_exhibition": is_exh})

    # 2. Map relay team exhibition status to (evt_ptr, team_no, relay_no)
    relay_exh_map = {}
    for r in relays:
        evt_id = safe_int(get_field(r, ["event_ptr", "Event_ptr"]))
        t_no = safe_int(get_field(r, ["team_ptr", "team_no", "Team_ptr", "Team_no"]))
        r_no = safe_int(get_field(r, ["relay_no", "Relay_no"]))
        pre_exh = safe_str(get_field(r, ["pre_exh", "Pre_exh"])).upper()
        fin_exh = safe_str(get_field(r, ["fin_exh", "Fin_exh"])).upper()
        is_exh = pre_exh != "" or fin_exh != ""
        relay_exh_map[(evt_id, t_no, r_no)] = is_exh

    # 3. Map relay names (leg assignments) to athlete_entries
    for rn in relay_names:
        ath_id = safe_int(get_field(rn, ["ath_no", "Ath_no"]))
        evt_id = safe_int(get_field(rn, ["event_ptr", "Event_ptr"]))
        t_no = safe_int(get_field(rn, ["team_no", "Team_no"]))
        r_no = safe_int(get_field(rn, ["relay_no", "Relay_no"]))
        if ath_id and evt_id:
            is_exh = relay_exh_map.get((evt_id, t_no, r_no), False)
            athlete_entries[ath_id].append({"evt_id": evt_id, "is_exhibition": is_exh})

    # Pass 1: Build older times map (15-18) for young swimmer fast times comparison
    older_times: dict[tuple[str, int, str], list[float]] = collections.defaultdict(list)
    for entry in entries:
        ath_id = safe_int(get_field(entry, ["ath_no", "Ath_no"]))
        evt_id = safe_int(get_field(entry, ["event_ptr", "Event_ptr"]) or get_field(entry, ["event_no", "Event_no"]))
        fin_time = safe_float(get_field(entry, ["fin_time", "Fin_time"]))
        fin_stat = safe_str(get_field(entry, ["fin_stat", "Fin_stat"])).upper()
        if fin_time > 0 and fin_stat not in ["Q", "R"]:
            ath_info = athletes_map.get(ath_id)
            if ath_info:
                age = safe_int(ath_info.get("age", 0))
                gender = str(ath_info.get("gender", "")).upper().strip()
                if 15 <= age <= 18:
                    evt_info = events_map.get(evt_id)
                    if evt_info:
                        stroke_name = get_stroke_name(evt_info.get("stroke"), False)
                        key = (gender, evt_info.get("dist", 0), stroke_name)
                        older_times[key].append(fin_time)

    fastest_older = {k: min(v) for k, v in older_times.items()}

    for entry in entries:
        ath_id = safe_int(get_field(entry, ["ath_no", "Ath_no"]))
        evt_id = safe_int(get_field(entry, ["event_ptr", "Event_ptr"]) or get_field(entry, ["event_no", "Event_no"]))

        fin_time = safe_float(get_field(entry, ["fin_time", "Fin_time"]))
        fin_stat = safe_str(get_field(entry, ["fin_stat", "Fin_stat"])).upper()
        fin_heat = safe_int(get_field(entry, ["fin_heat", "Fin_heat"]))
        fin_lane = safe_int(get_field(entry, ["fin_lane", "Fin_lane"]))
        ev_score = safe_float(get_field(entry, ["ev_score", "Ev_score"]))
        scr_stat = safe_int(get_field(entry, ["scr_stat", "Scr_stat"]))

        place = safe_int(get_field(entry, ["fin_place", "place", "Fin_place"]))

        ath = athletes_map.get(ath_id, {})
        ath_name = str(ath.get("name", f"Swimmer #{ath_id}"))
        evt = events_map.get(evt_id, {})
        evt_desc = evt.get("desc", f"Event {evt_id}")

        if fin_heat > 0 and fin_lane > 0:
            # Collect times for duplicate check
            if fin_time > 0:
                event_times[evt_id].append((fin_time, fin_heat, fin_lane, ath_name))

            # 1. Points on DQs (CRITICAL)
            if fin_stat == "Q" and ev_score > 0:
                findings.append(
                    pb2.ValidationFinding(
                        severity=pb2.VALIDATION_SEVERITY_CRITICAL,
                        category="Points on DQs",
                        message=f"{ath_name} in {evt_desc} (Heat {fin_heat}, Lane {fin_lane}): DQ status but awarded {ev_score:.1f} points!",
                        affected_id=str(ath_id),
                    )
                )

            # 2. 0 Backup Timers / NS / Missing Times (INFO)
            # Only report if the entry is scored (i.e. has a place > 0 or a non-empty status like NS)
            is_scored = (place > 0) or (fin_stat != "")
            if is_scored and fin_time == 0 and fin_stat not in ["Q", "R"]:
                findings.append(
                    pb2.ValidationFinding(
                        severity=pb2.VALIDATION_SEVERITY_INFO,
                        category="0 Backup Timers",
                        message=f"{ath_name} in {evt_desc} (Heat {fin_heat}, Lane {fin_lane}): 0 backup timers (NS/Missing Time).",
                        affected_id=str(ath_id),
                    )
                )
            elif fin_time > 0:
                # 8. 1 Backup Timer (WARNING)
                back1 = safe_float(get_field(entry, ["fin_back1", "Fin_back1"]))
                back2 = safe_float(get_field(entry, ["fin_back2", "Fin_back2"]))
                back3 = safe_float(get_field(entry, ["fin_back3", "Fin_back3"]))
                num_backups = (1 if back1 > 0 else 0) + (1 if back2 > 0 else 0) + (1 if back3 > 0 else 0)
                if num_backups == 1:
                    findings.append(
                        pb2.ValidationFinding(
                            severity=pb2.VALIDATION_SEVERITY_WARNING,
                            category="1 Backup Timer",
                            message=f"{ath_name} in {evt_desc} (Heat {fin_heat}, Lane {fin_lane}): Only 1 backup timer recorded (Time: {fin_time:.2f}s).",
                            affected_id=str(ath_id),
                        )
                    )

        # 3. Scratched with Times (CRITICAL)
        if fin_stat == "R" or scr_stat == 1:
            back1 = safe_float(get_field(entry, ["fin_back1", "Fin_back1"]))
            back2 = safe_float(get_field(entry, ["fin_back2", "Fin_back2"]))
            back3 = safe_float(get_field(entry, ["fin_back3", "Fin_back3"]))
            if fin_time > 0 or back1 > 0 or back2 > 0 or back3 > 0:
                findings.append(
                    pb2.ValidationFinding(
                        severity=pb2.VALIDATION_SEVERITY_CRITICAL,
                        category="Scratched with Time",
                        message=f"{ath_name} in {evt_desc} (Heat {fin_heat}, Lane {fin_lane}): Scratched but has time {fin_time:.2f}s.",
                        affected_id=str(ath_id),
                    )
                )

        # 6. Wild Times (WARNING)
        if fin_time > 0:
            actualseed_time = safe_float(get_field(entry, ["actualseed_time", "actual_seed"]))
            if actualseed_time > 0:
                age = safe_int(ath.get("age", 0))
                if age >= 9:
                    diff = abs(fin_time - actualseed_time)
                    if diff > 10.0:
                        direction = "Improvement" if fin_time < actualseed_time else "Regression"
                        findings.append(
                            pb2.ValidationFinding(
                                severity=pb2.VALIDATION_SEVERITY_WARNING,
                                category="Wild Times",
                                message=f"{ath_name} (Age {age}) in {evt_desc}: Seed {actualseed_time:.2f}s vs Final {fin_time:.2f}s ({direction} of {diff:.2f}s).",
                                affected_id=str(ath_id),
                            )
                        )

        # 7. Exceptionally Fast Times for Swimmers < 11 (WARNING)
        if fin_time > 0 and fin_stat not in ["Q", "R"]:
            age = safe_int(ath.get("age", 0))
            gender = str(ath.get("gender", "")).upper().strip()
            if 0 < age < 11 and evt:
                dist = evt.get("dist", 0)
                stroke_name = get_stroke_name(evt.get("stroke"), False)
                dynamic_key = (gender, dist, stroke_name)
                target_limit = None
                source = ""

                if dynamic_key in fastest_older:
                    target_limit = fastest_older[dynamic_key]
                    source = f"fastest 15-18 in meet ({target_limit:.2f}s)"
                elif dist == 25:
                    static_standards_25 = {
                        ("F", "Freestyle"): 13.50,
                        ("M", "Freestyle"): 12.00,
                        ("F", "Backstroke"): 16.00,
                        ("M", "Backstroke"): 15.00,
                        ("F", "Breaststroke"): 18.00,
                        ("M", "Breaststroke"): 16.50,
                        ("F", "Butterfly"): 14.50,
                        ("M", "Butterfly"): 13.50,
                    }
                    static_key = (gender, stroke_name)
                    if static_key in static_standards_25:
                        target_limit = static_standards_25[static_key]
                        source = f"static standard ({target_limit:.2f}s)"

                if target_limit and fin_time <= target_limit:
                    findings.append(
                        pb2.ValidationFinding(
                            severity=pb2.VALIDATION_SEVERITY_WARNING,
                            category="Fast Times",
                            message=f"{ath_name} (Age {age}) in {evt_desc}: Time {fin_time:.2f}s is faster than/equal to {source} limit.",
                            affected_id=str(ath_id),
                        )
                    )

    # 4. Relays with NS (INFO)
    for r in relays:
        r_heat = safe_int(get_field(r, ["fin_heat", "Fin_heat"]))
        r_lane = safe_int(get_field(r, ["fin_lane", "Fin_lane"]))
        if r_heat > 0 and r_lane > 0:
            r_place = safe_int(get_field(r, ["fin_place", "place", "Fin_place"]))
            r_stat = safe_str(get_field(r, ["fin_stat", "Fin_stat"])).upper()
            is_scored = (r_place > 0) or (r_stat != "")
            if is_scored:
                r_time = safe_float(get_field(r, ["fin_time", "Fin_time"]))
                if r_time == 0 and r_stat not in ["Q", "R"]:
                    t_id = safe_int(get_field(r, ["team_ptr", "team_no", "Team_ptr", "Team_no"]))
                    team_name = teams_map.get(t_id, {}).get("name", f"Team #{t_id}")
                    team_ltr = safe_str(get_field(r, ["team_ltr", "Team_ltr"]))
                    evt_id = safe_int(get_field(r, ["event_ptr", "Event_ptr"]))
                    evt_desc = events_map.get(evt_id, {}).get("desc", f"Event {evt_id}")
                    findings.append(
                        pb2.ValidationFinding(
                            severity=pb2.VALIDATION_SEVERITY_INFO,
                            category="Relays with NS",
                            message=f"Team {team_name} '{team_ltr}' in {evt_desc} (Heat {r_heat}, Lane {r_lane}): Relay has NS/Missing Time.",
                            affected_id=str(t_id),
                        )
                    )

    # 5. Duplicate Times (WARNING)
    for evt_id, times_list in event_times.items():
        time_to_entries = collections.defaultdict(list)
        for time_val, heat, lane, name in times_list:
            time_to_entries[time_val].append((heat, lane, name))
        for time_val, entries_at_time in time_to_entries.items():
            heats = {heat for heat, _, _ in entries_at_time}
            if len(heats) > 1:
                evt_desc = events_map.get(evt_id, {}).get("desc", f"Event {evt_id}")
                swimmers_info = [f"{name} (Heat {heat}, Lane {lane})" for heat, lane, name in entries_at_time]
                findings.append(
                    pb2.ValidationFinding(
                        severity=pb2.VALIDATION_SEVERITY_WARNING,
                        category="Duplicate Times",
                        message=f"{evt_desc}: Time {time_val:.2f}s matches exactly in different heats: {', '.join(swimmers_info)}.",
                        affected_id=str(evt_id),
                    )
                )

    # 1. Athlete Validations
    for ath in athletes:
        ath_id = safe_int(get_field(ath, ["ath_no", "Ath_no"]))
        ath_info = athletes_map.get(ath_id, {})
        name = str(ath_info.get("name", f"Swimmer #{ath_id}"))
        gender = str(ath_info.get("gender", ""))
        age = safe_int(ath_info.get("age", 0))
        t_no = safe_int(ath_info.get("team_no", 0))

        # CRITICAL: Missing gender
        if not gender or gender not in ["M", "F", "B", "G", "W"]:
            findings.append(
                pb2.ValidationFinding(
                    severity=pb2.VALIDATION_SEVERITY_CRITICAL,
                    category="Athletes",
                    message=f"Swimmer {name} has an invalid or missing gender code: '{gender}'.",
                    affected_id=str(ath_id),
                )
            )

        # CRITICAL: Invalid team link
        if not t_no or t_no not in teams_map:
            findings.append(
                pb2.ValidationFinding(
                    severity=pb2.VALIDATION_SEVERITY_CRITICAL,
                    category="Athletes",
                    message=f"Swimmer {name} is associated with a missing team ID: {t_no}.",
                    affected_id=str(ath_id),
                )
            )

        # WARNING: TVSL Rules Limit (Max 3 individual events, max 4 total)
        # Excludes Exhibition swims
        ath_evts = athlete_entries.get(ath_id, [])
        ind_count = 0
        rel_count = 0
        for item in ath_evts:
            if item["is_exhibition"]:
                continue
            evt_info = events_map.get(item["evt_id"])
            if evt_info:
                if evt_info["is_relay"]:
                    rel_count += 1
                else:
                    ind_count += 1

                # WARNING: Gender Mismatch
                evt_sex = gender_map.get(evt_info["sex"])
                ath_sex = gender_map.get(gender)
                if evt_sex and ath_sex and evt_sex != ath_sex and evt_info["sex"] != "X":
                    findings.append(
                        pb2.ValidationFinding(
                            severity=pb2.VALIDATION_SEVERITY_WARNING,
                            category="Entries",
                            message=f"Swimmer {name} ({gender}) entered in single-sex event {evt_info['desc']} ({evt_info['sex']}).",
                            affected_id=str(ath_id),
                        )
                    )

                # WARNING: Age group mismatch
                low = evt_info["low_age"]
                high = evt_info["high_age"]
                if (low > 0 and age < low) or (high > 0 and age > high):
                    findings.append(
                        pb2.ValidationFinding(
                            severity=pb2.VALIDATION_SEVERITY_WARNING,
                            category="Entries",
                            message=f"Swimmer {name} (age {age}) entered in Event {evt_info['desc']} restricted to ages {low}-{high}.",
                            affected_id=str(ath_id),
                        )
                    )

        if ind_count > 3:
            findings.append(
                pb2.ValidationFinding(
                    severity=pb2.VALIDATION_SEVERITY_WARNING,
                    category="Rules Limit",
                    message=f"Swimmer {name} exceeds TVSL limits with {ind_count} individual entries (Rule 12 max: 3).",
                    affected_id=str(ath_id),
                )
            )
        if rel_count > 2:
            findings.append(
                pb2.ValidationFinding(
                    severity=pb2.VALIDATION_SEVERITY_WARNING,
                    category="Rules Limit",
                    message=f"Swimmer {name} exceeds relay limits with {rel_count} relay entries (max: 2).",
                    affected_id=str(ath_id),
                )
            )
        if (ind_count + rel_count) > 4:
            findings.append(
                pb2.ValidationFinding(
                    severity=pb2.VALIDATION_SEVERITY_WARNING,
                    category="Rules Limit",
                    message=f"Swimmer {name} exceeds total entry limits with {ind_count + rel_count} total entries (max: 4).",
                    affected_id=str(ath_id),
                )
            )

    return findings
