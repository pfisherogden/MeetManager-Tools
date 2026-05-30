import copy
import logging
import re
from typing import TYPE_CHECKING, Any

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from ..mm_to_json import MmToJsonConverter


class ReportDataExtractor:
    def __init__(self, converter: "MmToJsonConverter", full_data: dict[str, Any] | None = None):
        self.converter = converter
        self.full_data = full_data if full_data is not None else self.converter.convert()
        self.team_color_map = self._build_team_color_map()

        # Performance: Pre-calculate lookup maps for common lookups
        self._athlete_map = {}
        athlete_df = self.converter.tables.get("athlete")
        if athlete_df is not None and not athlete_df.empty:
            for _, row in athlete_df.iterrows():
                ath_id = row.get("ath_no")
                if ath_id:
                    self._athlete_map[str(ath_id)] = row.to_dict()

        self._team_map = {}
        team_df = self.converter.tables.get("team")
        if team_df is not None and not team_df.empty:
            for _, row in team_df.iterrows():
                t_id = row.get("team_no")
                if t_id:
                    self._team_map[str(t_id)] = row.to_dict()

        # Performance: Pre-calculate name-to-gender map for fallbacks
        self._name_gender_map = {}
        if athlete_df is not None and not athlete_df.empty:
            for _, row in athlete_df.iterrows():
                last = str(row.get("last_name", "")).strip().lower()
                first = str(row.get("first_name", "")).strip().lower()
                sex = str(row.get("sex", "")).upper()
                gender = "Boys" if sex == "M" else "Girls" if sex == "F" else "Mixed"
                self._name_gender_map[f"{last}, {first}"] = gender
                self._name_gender_map[f"{first} {last}"] = gender

    def _build_team_color_map(self) -> dict[str, str]:
        """Map team names to their assigned colors for UI consistency."""
        df_team = self.converter.tables.get("team")
        if df_team is None or df_team.empty:
            return {}

        color_map = {}
        for _, row in df_team.iterrows():
            t_id = self._safe_int(row.get("team_no"))
            t_name = str(row.get("team_name", "")).strip()
            if t_name:
                # Use same logic as server.py
                palette = [
                    "#3b82f6",
                    "#ef4444",
                    "#10b981",
                    "#f59e0b",
                    "#8b5cf6",
                    "#ec4899",
                    "#06b6d4",
                    "#f97316",
                    "#84cc16",
                    "#6366f1",
                    "#a855f7",
                    "#14b8a6",
                ]
                color = palette[t_id % len(palette)]
                color_map[t_name] = color
        return color_map

    def _get_full_data(self) -> dict[str, Any]:
        """Ensure full_data is populated, refreshing from converter if needed."""
        if not self.full_data or not self.full_data.get("sessions"):
            self.full_data = self.converter.convert()

        # Debugging empty data issues
        sessions = self.full_data.get("sessions", [])
        num_sessions = len(sessions)
        num_events = sum(len(s.get("events", [])) for s in sessions)
        logger.debug(f"DEBUG: _get_full_data: {num_sessions} sessions, {num_events} total events")

        return self.full_data

    def _get_event_sort_key(self, evt: dict[str, Any]) -> tuple[int, str]:
        """Generate a sort key that handles alpha suffixes correctly (e.g., 101A, 101B)."""
        evt_num_str = str(evt.get("eventNum") or evt.get("evt_num") or "0")
        match = re.match(r"(\d+)([A-Za-z]*)", evt_num_str)
        if match:
            num = int(match.group(1))
            suffix = match.group(2).upper()
            return (num, suffix)
        return (0, "")

    def _matches_team_filter(self, entry: dict[str, Any], filter_team: str | None) -> bool:
        """Robust whole-word matching for team filtering, supporting both name and code."""
        if not filter_team:
            return True

        f_t = str(filter_team).strip().lower()
        if not f_t or f_t == "all teams":
            return True

        # Check both full name and abbreviation/code
        candidates = [
            str(entry.get("team", "")).strip().lower(),
            str(entry.get("teamCode", "")).strip().lower(),
            str(entry.get("teamName", "")).strip().lower(),
        ]

        # 1. Try exact match (most reliable)
        if any(f_t == c for c in candidates if c):
            return True

        # 2. Use regex for whole-word matching (handles "TVSL" in "TVSL-CA")
        pattern = r"\b" + re.escape(f_t) + r"\b"
        if any(bool(re.search(pattern, c)) for c in candidates if c):
            return True

        # 3. Last resort: simple inclusion (if filter is at least 3 chars)
        if len(f_t) >= 3 and any(f_t in c for c in candidates if c):
            return True

        return False

    def _normalize_gender(self, gender: str | None) -> str:
        """Normalize gender string to M, F, or X. Return 'X' if no filtering is desired."""
        if not gender:
            return "X"
        g = str(gender).strip().lower()
        if g in ("m", "male", "boys", "boy", "b"):
            return "M"
        if g in ("f", "female", "girls", "girl", "g"):
            return "F"
        return "X"

    def _get_athlete_gender(self, entry: dict[str, Any]) -> str:
        """Helper to look up athlete gender using explicit data elements or pre-calculated maps."""
        if entry.get("athleteSex"):
            sex = self._normalize_gender(entry.get("athleteSex"))
            return "Boys" if sex == "M" else "Girls" if sex == "F" else "Mixed"

        # Performance: Use O(1) map lookup instead of O(N) loop
        name = entry.get("name", "").strip().lower()
        if not name:
            return "Unknown"

        # Check for both common formats
        return self._name_gender_map.get(name, "Unknown")

    def _format_age(self, min_age: int, max_age: int) -> str:
        if min_age == 0 and max_age >= 109:
            return "Open"
        if min_age == 0:
            return f"{max_age} & under"
        if max_age >= 109:
            return f"{min_age} & over"
        return f"{min_age}-{max_age}"

    def _get_report_subtitle(self, base_title: str, team: str | None, gender: str | None, age: str | None) -> str:
        """Helper to append active filters to report title for clarity."""
        parts = [base_title]
        if team:
            parts.append(f"Team: {team}")
        if gender and gender.lower() != "mixed":
            parts.append(f"Gender: {gender}")
        if age and age.lower() != "open":
            parts.append(f"Age: {age}")
        return " - ".join(parts)

    def extract_meet_entries_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
    ) -> dict[str, Any]:
        df_ath = self.converter.tables.get("athlete", None)
        df_team = self.converter.tables.get("team", None)
        if df_ath is None or df_team is None:
            return {"groups": []}

        team_map = {}
        for _, row in df_team.iterrows():
            t_id = row.get("team_no")
            t_code = str(row.get("team_abbr", "")).strip()
            t_lsc = str(row.get("team_lsc", "")).strip()
            full_code = f"{t_code}-{t_lsc}" if t_lsc else t_code
            team_map[t_id] = {"name": str(row.get("team_name", "")).strip(), "code": full_code}

        full_data = self._get_full_data()
        flat_entries = []
        for sess in full_data.get("sessions", []):
            if not sess:
                continue
            for evt in sess.get("events", []):
                if not evt:
                    continue
                evt_num = evt.get("eventNum") or evt.get("evt_num")
                evt_desc = evt.get("eventDesc")
                is_relay = evt.get("isRelay", False)
                evt_gender = evt.get("gender", "")
                evt_min_age = self._safe_int(evt.get("minAge", 0))
                evt_max_age = self._safe_int(evt.get("maxAge", 109))

                if gender_filter:
                    target_g = self._normalize_gender(gender_filter)
                    if (
                        target_g != "X"
                        and self._normalize_gender(evt_gender) != target_g
                        and self._normalize_gender(evt_gender) != "X"
                    ):
                        continue

                if age_group_filter:
                    if age_group_filter.lower() != "open":
                        evt_age_str = self._format_age(evt_min_age, evt_max_age)
                        if age_group_filter.lower() != evt_age_str.lower():
                            continue

                for entry in evt.get("entries", []):
                    if not entry:
                        continue

                    if gender_filter and not is_relay:
                        target_g = self._normalize_gender(gender_filter)
                        ath_sex = self._get_athlete_gender(entry)
                        if (
                            self._normalize_gender(ath_sex) != target_g
                            and self._normalize_gender(ath_sex) != "X"
                            and ath_sex != "Unknown"
                        ):
                            continue

                    t_name = entry.get("team", "")
                    key = (entry.get("name"), self._safe_int(entry.get("age", 0)), t_name)
                    heat = self._safe_int(entry.get("heat", 0))
                    lane = self._safe_int(entry.get("lane", 0))
                    hl = f"{heat}/{lane}" if heat and lane else ""

                    entry_data = {
                        "key": key,
                        "team": t_name,
                        "team_color": self.team_color_map.get(t_name, ""),
                        "name": entry.get("name"),
                        "age": self._safe_int(entry.get("age", 0)),
                        "evt_num": evt_num,
                        "evt_desc": evt_desc,
                        "time": entry.get("seedTime", "NT"),
                        "hl": hl,
                        "is_relay": is_relay,
                        "athleteId": entry.get("athleteId"),
                        "athleteSex": entry.get("athleteSex"),
                    }
                    if is_relay:
                        entry_data["relayAthletes"] = entry.get("relayAthletes", [])
                    flat_entries.append(entry_data)

        # Performance: Use pre-calculated name-gender map and team-code map
        team_code_map = {}
        df_team = self.converter.tables.get("team", None)
        if df_team is not None:
            for _, row in df_team.iterrows():
                t_name = str(row.get("team_name", "")).strip()
                t_code = str(row.get("team_abbr", "")).strip()
                t_lsc = str(row.get("team_lsc", "")).strip()
                full_code = f"{t_code}-{t_lsc}" if t_lsc else t_code
                team_code_map[t_name] = full_code

        grouped: dict[str, Any] = {}
        ind_entries = [e for e in flat_entries if not e["is_relay"]]
        relay_entries = [e for e in flat_entries if e["is_relay"]]

        for item in ind_entries:
            t_name = item["team"]
            if not self._matches_team_filter({"team": t_name}, team_filter):
                continue
            key = item["key"]
            if t_name not in grouped:
                grouped[t_name] = {}
            if key not in grouped[t_name]:
                grouped[t_name][key] = {
                    "name": item["name"],
                    "age": item["age"],
                    "team": t_name,
                    "ind_count": 0,
                    "rel_count": 0,
                    "events": [],
                }
            grouped[t_name][key]["events"].append(item)
            grouped[t_name][key]["ind_count"] += 1

        id_lookup = {}
        for t_name, athletes in grouped.items():
            for key, data in athletes.items():
                if key == "RelayTeams":
                    continue
                if data["events"]:
                    aid = data["events"][0].get("athleteId")
                    if aid:
                        id_lookup[(t_name, aid)] = key

        for item in relay_entries:
            t_name = item["team"]
            if not self._matches_team_filter({"team": t_name}, team_filter):
                continue
            if t_name not in grouped:
                grouped[t_name] = {}
            if "RelayTeams" not in grouped[t_name]:
                grouped[t_name]["RelayTeams"] = []
            grouped[t_name]["RelayTeams"].append(item)
            relay_athletes = item.get("relayAthletes", [])
            for ath in relay_athletes:
                aid = ath.get("id")
                if not aid:
                    continue
                found_key = id_lookup.get((t_name, aid))
                if not found_key:
                    try:
                        found_key = id_lookup.get((t_name, self._safe_int(aid)))
                    except Exception:
                        pass
                if found_key:
                    grp = grouped[t_name][found_key]
                else:
                    s_name = f"{ath.get('first', '')} {ath.get('last', '')}".strip()
                    s_age = self._safe_int(ath.get("age", 0))
                    new_key = (s_name, s_age, t_name)
                    if new_key not in grouped[t_name]:
                        grouped[t_name][new_key] = {
                            "name": s_name,
                            "age": s_age,
                            "team": t_name,
                            "ind_count": 0,
                            "rel_count": 0,
                            "events": [],
                        }
                    grp = grouped[t_name][new_key]
                    id_lookup[(t_name, aid)] = new_key
                grp["events"].append(copy.copy(item))
                grp["rel_count"] += 1

        sorted_teams = sorted(grouped.keys())
        report_groups = []
        for t_name in sorted_teams:
            team_items: list[dict[str, Any]] = []
            real_athletes = [v for k, v in grouped[t_name].items() if k != "RelayTeams"]
            sorted_athletes = sorted(real_athletes, key=lambda x: x["name"])
            seq = 1
            for ath in sorted_athletes:
                gender = self._name_gender_map.get(ath["name"], "")
                t_code = team_code_map.get(t_name, t_name)
                parts = ath["name"].split(" ")
                display_name = f"{parts[-1]}, " + " ".join(parts[:-1]) if len(parts) >= 2 else ath["name"]
                age_val = self._safe_int(ath.get("age", 0))
                h_parts = []
                if seq:
                    h_parts.append(f"{seq} {display_name}")
                if gender:
                    h_parts.append(gender)
                if age_val > 0:
                    h_parts.append(f"Age: {age_val}")
                if t_code:
                    h_parts.append(t_code)
                header_str = " - ".join(h_parts) + f" - Ind/Rel: {ath['ind_count']} / {ath['rel_count']}"
                sorted_events = sorted(ath["events"], key=self._get_event_sort_key)
                sub_rows = []
                for e in sorted_events:
                    desc = e["evt_desc"] + (" (Relay)" if e["is_relay"] else "")
                    sub_rows.append(
                        {
                            "event_num": str(e["evt_num"]),
                            "event_name": desc,
                            "time": e["time"],
                            "heat_lane": e["hl"],
                            "is_relay": e["is_relay"],
                            "swimmers": e.get("swimmers", []) if e["is_relay"] else [],
                        }
                    )
                team_items.append({"header": header_str, "sub_items": sub_rows})
                seq += 1
            relay_teams_list = grouped[t_name].get("RelayTeams", [])
            if relay_teams_list:
                team_items.append({"header": "   RELAY TEAMS", "sub_items": []})
                flat_relays = sorted(relay_teams_list, key=self._get_event_sort_key)
                for _, r in enumerate(flat_relays):
                    hl_text = f"{r['heat']}/{r['lane']}" if r.get("heat") else ""

                    names = []
                    if "relayAthletes" in r:
                        is_mixed = str(r.get("event_sex", "")).upper() == "X"
                        for a in r["relayAthletes"]:
                            age_val = a.get("age", "")
                            age_str = str(age_val)
                            if is_mixed and age_val:
                                gender_pref = str(a.get("athleteSex", ""))[:1].upper()
                                age_str = f"{gender_pref}{age_str}"
                            names.append(
                                f"{a.get('lastName', '').strip()}, {a.get('firstName', '').strip()} {age_str}".strip()
                            )
                    else:
                        names = [n.strip() for n in r.get("name", "").split(",")]

                    sub_items = [
                        {
                            "event_num": str(r["evt_num"]),
                            "event_name": r["evt_desc"],
                            "time": r.get("seedTime", r.get("time", "")),
                            "heat_lane": hl_text,
                            "is_relay": True,
                            "swimmers": names,
                        },
                    ]
                    team_items.append({"header": "", "force_1col": True, "sub_items": sub_items})
            report_groups.append({"header": f"Team Entries - {t_name}", "sub_items": team_items})

        sub_title = self._get_report_subtitle(
            report_title or "Entries - All Events", team_filter, gender_filter, age_group_filter
        )
        return {
            "meet_name": full_data.get("meetName", ""),
            "sub_title": sub_title,
            "groups": report_groups,
        }

    def extract_meet_program_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
        columns_on_page: int = 2,
        show_relay_swimmers: bool = True,
        show_dq_lines: bool = False,
    ) -> dict[str, Any]:
        full_data = self._get_full_data()
        all_events = []
        for sess in full_data.get("sessions", []):
            if not sess:
                continue
            for evt in sess.get("events", []):
                if not evt:
                    continue
                all_events.append(evt)
        all_events.sort(key=self._get_event_sort_key)
        report_groups = []
        for evt in all_events:
            evt_num, evt_desc, is_relay, entries = (
                evt.get("eventNum") or evt.get("evt_num"),
                evt.get("eventDesc"),
                evt.get("isRelay", False),
                evt.get("entries", []),
            )
            evt_gender = evt.get("gender", "")
            evt_min_age = self._safe_int(evt.get("minAge", 0))
            evt_max_age = self._safe_int(evt.get("maxAge", 109))

            if gender_filter:
                target_g = self._normalize_gender(gender_filter)
                if (
                    target_g != "X"
                    and self._normalize_gender(evt_gender) != target_g
                    and self._normalize_gender(evt_gender) != "X"
                ):
                    continue

            if age_group_filter and age_group_filter.lower() != "open":
                evt_age_str = self._format_age(evt_min_age, evt_max_age)
                if evt_age_str.lower() != age_group_filter.lower():
                    continue

            if team_filter:
                entries = [e for e in entries if e and self._matches_team_filter(e, team_filter)]
            if gender_filter:
                filtered = []
                target_g = self._normalize_gender(gender_filter)
                for e in entries:
                    if not e:
                        continue
                    if e.get("isRelay") or target_g == "X":
                        filtered.append(e)
                    else:
                        ath_sex = self._get_athlete_gender(e)
                        if (
                            self._normalize_gender(ath_sex) == target_g
                            or self._normalize_gender(ath_sex) == "X"
                            or ath_sex == "Unknown"
                        ):
                            filtered.append(e)
                entries = filtered
            if not entries:
                continue
            header = f"Event {evt_num}  {evt_desc}"
            heats: dict[int, list[Any]] = {}
            for entry in entries:
                if not entry:
                    continue
                h = self._safe_int(entry.get("heat", 0))
                if h not in heats:
                    heats[h] = []
                heats[h].append(entry)
            sorted_heats, heat_items = sorted(heats.keys()), []
            for h in sorted_heats:
                sub_items = []
                for entry in sorted(heats[h], key=lambda x: self._safe_int(x.get("lane", 0))):
                    lane, seed_time = entry.get("lane", ""), entry.get("seedTime", "NT")
                    if is_relay:
                        names = []
                        if show_relay_swimmers:
                            if "relayAthletes" in entry:
                                is_mixed = str(evt.get("gender", "")).upper() == "X"
                                for a in entry["relayAthletes"]:
                                    age_val = a.get("age", "")
                                    age_str = str(age_val)
                                    if is_mixed and age_val:
                                        gender_pref = str(a.get("athleteSex", ""))[:1].upper()
                                        age_str = f"{gender_pref}{age_str}"
                                    names.append(
                                        f"{a.get('lastName', '').strip()}, {a.get('firstName', '').strip()} {age_str}".strip()
                                    )
                            else:
                                names = [n.strip() for n in entry.get("name", "").split(",")]
                        sub_items.append(
                            {
                                "lane": str(lane),
                                "name": f"{entry.get('team', '')} {entry.get('relayLtr', '')}",
                                "team": entry.get("teamCode") or entry.get("team", ""),
                                "team_color": self.team_color_map.get(entry.get("team", ""), ""),
                                "relayLtr": entry.get("relayLtr", ""),
                                "time": seed_time,
                                "swimmers": names,
                                "is_relay": True,
                            }
                        )
                    else:
                        name = entry.get("name", "")
                        if "," not in name:
                            parts = name.split(" ")
                            name = f"{parts[-1]}, " + " ".join(parts[:-1]) if len(parts) >= 2 else name
                        sub_items.append(
                            {
                                "lane": str(lane),
                                "name": name,
                                "age": str(self._safe_int(entry.get("age", 0))),
                                "team": entry.get("teamCode") or entry.get("team", ""),
                                "team_color": self.team_color_map.get(entry.get("team", ""), ""),
                                "time": seed_time,
                                "is_relay": False,
                            }
                        )
                heat_items.append({"header": f"Heat {h} of {sorted_heats[-1]} Finals", "sub_items": sub_items})
            report_groups.append({"header": header, "heats": heat_items, "items": heat_items})

        sub_title = self._get_report_subtitle(
            report_title or "Meet Program", team_filter, gender_filter, age_group_filter
        )
        return {
            "meet_name": full_data.get("meetName", ""),
            "sub_title": sub_title,
            "groups": report_groups,
            "columns_on_page": columns_on_page,
            "show_relay_swimmers": show_relay_swimmers,
            "show_dq_lines": show_dq_lines,
        }

    def extract_psych_sheet_data(
        self, team_filter=None, report_title=None, gender_filter=None, age_group_filter=None
    ) -> dict[str, Any]:
        full_data = self._get_full_data()
        all_events = []
        for sess in full_data.get("sessions", []):
            if not sess:
                continue
            for evt in sess.get("events", []):
                if not evt:
                    continue
                all_events.append(evt)
        all_events.sort(key=self._get_event_sort_key)
        report_groups = []
        for evt in all_events:
            evt_num, evt_desc, entries = (
                evt.get("eventNum") or evt.get("evt_num"),
                evt.get("eventDesc"),
                evt.get("entries", []),
            )
            evt_gender = evt.get("gender", "")
            evt_min_age = self._safe_int(evt.get("minAge", 0))
            evt_max_age = self._safe_int(evt.get("maxAge", 109))

            if gender_filter:
                target_g = self._normalize_gender(gender_filter)
                if (
                    target_g != "X"
                    and self._normalize_gender(evt_gender) != target_g
                    and self._normalize_gender(evt_gender) != "X"
                ):
                    continue

            if age_group_filter and age_group_filter.lower() != "open":
                evt_age_str = self._format_age(evt_min_age, evt_max_age)
                if evt_age_str.lower() != age_group_filter.lower():
                    continue

            if team_filter:
                entries = [e for e in entries if e and self._matches_team_filter(e, team_filter)]
            if gender_filter:
                filtered = []
                target_g = self._normalize_gender(gender_filter)
                for e in entries:
                    if not e:
                        continue
                    if target_g == "X":
                        filtered.append(e)
                    else:
                        ath_sex = self._get_athlete_gender(e)
                        if (
                            self._normalize_gender(ath_sex) == target_g
                            or self._normalize_gender(ath_sex) == "X"
                            or ath_sex == "Unknown"
                        ):
                            filtered.append(e)
                entries = filtered
            if not entries:
                continue

            def time_sort_key(ent):
                if not ent:
                    return 999999.0
                t = ent.get("seedTime", "NT")
                if t == "NT":
                    return 999999.0
                try:
                    parts = t.split(":")
                    if len(parts) == 2:
                        return float(parts[0]) * 60 + float(parts[1])
                    return float(parts[0])
                except Exception:
                    return 999999.0

            sub_items = [
                {
                    "name": e.get("name", ""),
                    "team": e.get("team", ""),
                    "team_color": self.team_color_map.get(e.get("team", ""), ""),
                    "age": str(self._safe_int(e.get("age", 0))),
                    "time": e.get("seedTime", "NT"),
                }
                for e in sorted(entries, key=time_sort_key)
                if e
            ]
            report_groups.append(
                {
                    "header": f"Event {evt_num}  {evt_desc}",
                    "sub_items": sub_items,
                }
            )

        sub_title = self._get_report_subtitle(
            report_title or "Psych Sheet", team_filter, gender_filter, age_group_filter
        )
        return {
            "meet_name": full_data.get("meetName", ""),
            "sub_title": sub_title,
            "groups": report_groups,
        }

    def extract_lane_timer_sheets_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
    ) -> dict[str, Any]:
        """Extract data grouped by physical Lane (1, 2, 3, etc.) for timer sheets."""
        full_data = self._get_full_data()

        # 1. Collect all valid entries across all sessions/events
        all_entries = []
        for sess in full_data.get("sessions", []):
            if not sess:
                continue
            for evt in sess.get("events", []):
                if not evt:
                    continue

                # Apply event-level filters (Gender, Age)
                evt_gender = evt.get("gender", "")
                if gender_filter:
                    target_g = self._normalize_gender(gender_filter)
                    if target_g != "X" and self._normalize_gender(evt_gender) != target_g:
                        continue

                if age_group_filter and age_group_filter.lower() != "open":
                    evt_age_str = self._format_age(self._safe_int(evt.get("minAge")), self._safe_int(evt.get("maxAge")))
                    if evt_age_str.lower() != age_group_filter.lower():
                        continue

                for entry in evt.get("entries", []):
                    if not entry:
                        continue
                    # Apply entry-level filters (Team)
                    if team_filter and not self._matches_team_filter(entry, team_filter):
                        continue

                    # Attach event context to entry for sorting and display
                    e_copy = entry.copy()
                    e_copy["_event_num"] = evt.get("eventNum") or evt.get("evt_num")
                    e_copy["_event_desc"] = evt.get("eventDesc")
                    e_copy["_is_relay"] = evt.get("isRelay", False)
                    all_entries.append(e_copy)

        # 2. Group by Lane (typically 1-8)
        lanes: dict[int, list[Any]] = {}
        for entry in all_entries:
            lane = self._safe_int(entry.get("lane", 0))
            if lane == 0:
                continue
            if lane not in lanes:
                lanes[lane] = []
            lanes[lane].append(entry)

        # 3. Sort each lane by Event # then Heat #
        report_groups = []
        sorted_lane_nums = sorted(lanes.keys())

        for lane_num in sorted_lane_nums:
            lane_entries = sorted(
                lanes[lane_num], key=lambda x: (self._safe_int(x["_event_num"]), self._safe_int(x.get("heat", 0)))
            )

            # 4. Group by event type and chunk into 12 entries per page
            # We want to break the page whenever the stroke/type changes OR we hit 12 entries.
            current_page_entries: list[dict[str, Any]] = []
            current_stroke_type = None
            page_num = 1

            def finish_page(l_num, p_entries, p_num):
                if p_entries:
                    report_groups.append(
                        {"header": f"Lane {l_num} (Page {p_num})", "lane": l_num, "sub_items": p_entries.copy()}
                    )
                    return [], p_num + 1
                return p_entries, p_num

            for entry in lane_entries:
                is_relay = entry.get("_is_relay", False)
                event_desc = entry["_event_desc"] or ""

                # Determine stroke type for grouping
                stroke_type = "Other"
                desc_lower = event_desc.lower()
                if "freestyle" in desc_lower and "relay" not in desc_lower:
                    stroke_type = "Freestyle"
                elif "backstroke" in desc_lower:
                    stroke_type = "Backstroke"
                elif "breaststroke" in desc_lower:
                    stroke_type = "Breaststroke"
                elif "butterfly" in desc_lower:
                    stroke_type = "Butterfly"
                elif "medley" in desc_lower and "relay" not in desc_lower:
                    stroke_type = "IM"
                elif "freestyle" in desc_lower and "relay" in desc_lower:
                    stroke_type = "Free Relay"
                elif "medley" in desc_lower and "relay" in desc_lower:
                    stroke_type = "Medley Relay"

                # Check if we should break the page
                # Break if type changed (and we have entries) OR if we hit 12 entries
                type_changed = current_stroke_type is not None and stroke_type != current_stroke_type
                if type_changed or len(current_page_entries) >= 12:
                    current_page_entries, page_num = finish_page(lane_num, current_page_entries, page_num)

                current_stroke_type = stroke_type

                item = {
                    "event_num": str(entry["_event_num"]),
                    "event_desc": event_desc,
                    "heat": str(self._safe_int(entry.get("heat", 0))),
                    "lane": str(lane_num),
                    "name": entry.get("name", "Unknown"),
                    "age": str(self._safe_int(entry.get("age", 0))),
                    "team": entry.get("teamCode") or entry.get("team", ""),
                    "time": entry.get("seedTime", "NT"),
                    "is_relay": is_relay,
                }
                if is_relay and "relayAthletes" in entry:
                    item["swimmers"] = [
                        f"{a.get('lastName', '').strip()}, {a.get('firstName', '').strip()}"
                        for a in entry["relayAthletes"]
                    ]

                elif is_relay:
                    item["swimmers"] = [n.strip() for n in entry.get("name", "").split(",")]

                current_page_entries.append(item)

            # Final page for this lane
            current_page_entries, page_num = finish_page(lane_num, current_page_entries, page_num)

        return {
            "meet_name": full_data.get("meetName", ""),
            "sub_title": report_title or "Lane Timer Sheets",
            "groups": report_groups,
        }

    def extract_timer_sheets_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
        lane_filter: int | None = None,
    ) -> dict[str, Any]:
        full_data = self._get_full_data()
        all_events = []
        for sess in full_data.get("sessions", []):
            if not sess:
                continue
            for evt in sess.get("events", []):
                if not evt:
                    continue
                all_events.append(evt)
        all_events.sort(key=self._get_event_sort_key)
        report_groups = []
        for evt in all_events:
            evt_num, evt_desc, entries, is_relay = (
                evt.get("eventNum") or evt.get("evt_num"),
                evt.get("eventDesc"),
                evt.get("entries", []),
                evt.get("isRelay", False),
            )
            evt_gender = evt.get("gender", "")
            evt_min_age = self._safe_int(evt.get("minAge", 0))
            evt_max_age = self._safe_int(evt.get("maxAge", 109))

            if gender_filter:
                target_g = self._normalize_gender(gender_filter)
                if (
                    target_g != "X"
                    and self._normalize_gender(evt_gender) != target_g
                    and self._normalize_gender(evt_gender) != "X"
                ):
                    continue

            if age_group_filter and age_group_filter.lower() != "open":
                evt_age_str = self._format_age(evt_min_age, evt_max_age)
                if evt_age_str.lower() != age_group_filter.lower():
                    continue

            if team_filter:
                entries = [e for e in entries if e and self._matches_team_filter(e, team_filter)]
            if gender_filter:
                filtered = []
                target_g = self._normalize_gender(gender_filter)
                for e in entries:
                    if not e:
                        continue
                    if e.get("isRelay") or target_g == "X":
                        filtered.append(e)
                    else:
                        ath_sex = self._get_athlete_gender(e)
                        if (
                            self._normalize_gender(ath_sex) == target_g
                            or self._normalize_gender(ath_sex) == "X"
                            or ath_sex == "Unknown"
                        ):
                            filtered.append(e)
                entries = filtered
            if not entries:
                continue
            header = f"Event {evt_num}  {evt_desc}"
            heats: dict[int, list[Any]] = {}
            for e in entries:
                if not e:
                    continue
                h = self._safe_int(e.get("heat", 0))
                if h not in heats:
                    heats[h] = []
                heats[h].append(e)
            sorted_heats, heat_items = sorted(heats.keys()), []
            for h in sorted_heats:
                sub_items = []
                for entry in sorted(heats[h], key=lambda x: self._safe_int(x.get("lane", 0))):
                    if not entry:
                        continue
                    item_data = {
                        "lane": str(entry.get("lane", "")),
                        "team": entry.get("teamCode") or entry.get("team", ""),
                        "time": entry.get("seedTime", "NT"),
                        "age": str(self._safe_int(entry.get("age", 0))),
                        "is_relay": is_relay,
                    }
                    if is_relay:
                        item_data["relayLtr"] = entry.get("relayLtr", "A")
                        names = [
                            f"{a.get('lastName', '').strip()}, {a.get('firstName', '').strip()}"
                            for a in entry.get("relayAthletes", [])
                        ]
                        if not names:
                            names = [n.strip() for n in entry.get("name", "").split(",")]
                        item_data["swimmers"] = names
                    else:
                        name = entry.get("name", "")
                        if "," not in name:
                            parts = name.split(" ")
                            name = f"{parts[-1]}, " + " ".join(parts[:-1]) if len(parts) >= 2 else name
                        item_data["name"] = name
                    sub_items.append(item_data)
                heat_items.append({"header": f"Heat {h} of {sorted_heats[-1]} Finals", "sub_items": sub_items})
            report_groups.append({"header": header, "heats": heat_items, "items": heat_items})

        sub_title = self._get_report_subtitle(
            report_title or "Timer Sheets", team_filter, gender_filter, age_group_filter
        )
        return {
            "meet_name": full_data.get("meetName", ""),
            "sub_title": sub_title,
            "groups": report_groups,
        }

    def extract_results_data(
        self, team_filter=None, report_title=None, gender_filter=None, age_group_filter=None
    ) -> dict[str, Any]:
        full_data = self._get_full_data()
        all_events = []
        for sess in full_data.get("sessions", []):
            if not sess:
                continue
            for evt in sess.get("events", []):
                if not evt:
                    continue
                all_events.append(evt)
        all_events.sort(key=self._get_event_sort_key)
        report_groups = []
        for evt in all_events:
            evt_num, evt_desc, entries = (
                evt.get("eventNum") or evt.get("evt_num"),
                evt.get("eventDesc"),
                evt.get("entries", []),
            )
            evt_gender = evt.get("gender", "")
            evt_min_age = self._safe_int(evt.get("minAge", 0))
            evt_max_age = self._safe_int(evt.get("maxAge", 109))

            if gender_filter:
                target_g = self._normalize_gender(gender_filter)
                if (
                    target_g != "X"
                    and self._normalize_gender(evt_gender) != target_g
                    and self._normalize_gender(evt_gender) != "X"
                ):
                    continue

            if age_group_filter and age_group_filter.lower() != "open":
                evt_age_str = self._format_age(evt_min_age, evt_max_age)
                if evt_age_str.lower() != age_group_filter.lower():
                    continue

            if team_filter:
                entries = [e for e in entries if e and self._matches_team_filter(e, team_filter)]
            if gender_filter:
                filtered = []
                target_g = self._normalize_gender(gender_filter)
                for e in entries:
                    if not e:
                        continue
                    if e.get("isRelay") or target_g == "X":
                        filtered.append(e)
                    else:
                        ath_sex = self._get_athlete_gender(e)
                        if (
                            self._normalize_gender(ath_sex) == target_g
                            or self._normalize_gender(ath_sex) == "X"
                            or ath_sex == "Unknown"
                        ):
                            filtered.append(e)
                entries = filtered
            if not entries:
                continue
            finished = [
                e
                for e in entries
                if e
                and (
                    (e.get("place") and self._safe_int(e.get("place", 0)) > 0)
                    or (e.get("finalTime") and e.get("finalTime") != "0.00" and e.get("finalTime") != "")
                )
            ]
            sorted_entries = sorted(finished, key=lambda x: self._safe_int(x.get("place", 0)) or 999)
            sub_items = [
                {
                    "place": str(e.get("place", "")),
                    "name": e.get("name", ""),
                    "team": e.get("team", ""),
                    "team_color": self.team_color_map.get(e.get("team", ""), ""),
                    "age": str(self._safe_int(e.get("age", 0))),
                    "time": e.get("finalTime", e.get("seedTime", "")),
                    "points": str(self._safe_int(e.get("points", 0))),
                }
                for e in sorted_entries
            ]
            report_groups.append(
                {
                    "header": f"Event {evt_num}  {evt_desc}",
                    "sub_items": sub_items,
                }
            )

        sub_title = self._get_report_subtitle(
            report_title or "Meet Results", team_filter, gender_filter, age_group_filter
        )
        return {
            "meet_name": full_data.get("meetName", ""),
            "sub_title": sub_title,
            "groups": report_groups,
        }

    def _safe_int(self, val, default=0):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return default
