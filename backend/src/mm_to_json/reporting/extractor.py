from typing import TYPE_CHECKING, Any
import copy
import re

if TYPE_CHECKING:
    from ..mm_to_json import MmToJsonConverter


class ReportDataExtractor:
    def __init__(self, converter: "MmToJsonConverter"):
        self.converter = converter

    def _format_age(self, min_age: int, max_age: int) -> str:
        if min_age == 0 and max_age >= 109:
            return "Open"
        if min_age == 0:
            return f"{max_age} & under"
        if max_age >= 109:
            return f"{min_age} & over"
        return f"{min_age}-{max_age}"

    def extract_meet_entries_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
    ) -> dict[str, Any]:
        """
        Extracts data for the Meet Entries report.
        Hierarchy: Team -> Athlete -> Events
        """
        # 1. Get raw dataframes
        df_ath = self.converter.tables.get("Athlete", None)
        df_team = self.converter.tables.get("Team", None)

        if df_ath is None or df_team is None:
            return {"groups": []}

        # 2. Build Team Map (ID -> {Code, Name})
        team_map = {}
        for _, row in df_team.iterrows():
            t_id = row.get("Team_no")
            t_code = str(row.get("Team_abbr", "")).strip()
            t_lsc = str(row.get("Team_lsc", "")).strip()
            # Construct code like DP-TV
            full_code = f"{t_code}-{t_lsc}" if t_lsc else t_code
            team_map[t_id] = {"name": str(row.get("Team_name", "")).strip(), "code": full_code}

        # 3. Build Athlete Map (ID -> {Name, Gender, Age, TeamID})
        ath_map = {}
        for _, row in df_ath.iterrows():
            a_id = row.get("Ath_no")
            t_id = row.get("Team_no")
            last = str(row.get("Last_name", "")).strip()
            first = str(row.get("First_name", "")).strip()
            initial = str(row.get("Initial", "")).strip()
            sex = str(row.get("Sex", "")).strip()
            age = row.get("Ath_age")

            # Filter by team if requested
            t_info = team_map.get(t_id)
            if team_filter:
                if not t_info:
                    continue
                if team_filter.lower() not in [t_info["code"].lower(), t_info["name"].lower()]:
                    continue

            # Filter by gender if requested
            if gender_filter:
                ath_sex = "Female" if sex == "F" else "Male" if sex == "M" else sex
                if gender_filter.lower() not in ath_sex.lower():
                    continue

            name_str = f"{last}, {first}"
            if initial:
                name_str += f" {initial}"

            ath_map[a_id] = {
                "id": a_id,
                "name": name_str,
                "sex": "Female" if sex == "F" else "Male" if sex == "M" else sex,
                "age": age,
                "team_id": t_id,
                "team_code": t_info["code"] if t_info else "UNK",
                "events": [],
            }

        full_data = self.converter.convert()
        flat_entries = []

        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                evt_num = evt.get("eventNum")
                evt_desc = evt.get("eventDesc")
                is_relay = evt.get("isRelay", False)

                # Filter by gender/age group at event level
                if gender_filter or age_group_filter:
                    if gender_filter:
                        if gender_filter.lower() not in evt_desc.lower() and "mixed" not in evt_desc.lower():
                            continue
                    if age_group_filter and age_group_filter.lower() not in evt_desc.lower():
                        continue

                for entry in evt.get("entries", []):
                    t_name = entry.get("team", "")
                    key = (entry.get("name"), entry.get("age"), t_name)
                    heat = entry.get("heat", 0)
                    lane = entry.get("lane", 0)
                    hl = f"{heat}/{lane}" if heat and lane else ""

                    entry_data = {
                        "key": key,
                        "team": t_name,
                        "name": entry.get("name"),
                        "age": entry.get("age"),
                        "evt_num": evt_num,
                        "evt_desc": evt_desc,
                        "time": entry.get("seedTime", "NT"),
                        "hl": hl,
                        "is_relay": is_relay,
                        "athleteId": entry.get("athleteId"),
                    }
                    if is_relay:
                        entry_data["relayAthletes"] = entry.get("relayAthletes", [])
                    flat_entries.append(entry_data)

        name_gender_map = {}
        team_code_map = {}
        for _, row in df_ath.iterrows():
            try:
                first_name = str(row.get("First_name", row.get("First", ""))).strip()
                last_name = str(row.get("Last_name", row.get("Last", ""))).strip()
                sex = str(row.get("Sex", "")).strip()
                full_fl = f"{first_name} {last_name}"
                full_lf = f"{last_name}, {first_name}"
                name_gender_map[full_fl] = "Female" if sex == "F" else "Male" if sex == "M" else sex
                name_gender_map[full_lf] = name_gender_map[full_fl]
                tid = row.get("Team_no")
                if tid in team_map:
                    team_code_map[team_map[tid]["name"]] = team_map[tid]["code"]
            except Exception:
                pass

        grouped = {}
        ind_entries = [e for e in flat_entries if not e["is_relay"]]
        relay_entries = [e for e in flat_entries if e["is_relay"]]

        for item in ind_entries:
            t_name = item["team"]
            if team_filter and team_filter.lower() not in t_name.lower():
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
                if key == "RelayTeams": continue
                if data["events"]:
                    aid = data["events"][0].get("athleteId")
                    if aid: id_lookup[(t_name, aid)] = key

        for item in relay_entries:
            t_name = item["team"]
            if team_filter and team_filter.lower() not in t_name.lower():
                continue
            if t_name not in grouped:
                grouped[t_name] = {}
            if "RelayTeams" not in grouped[t_name]:
                grouped[t_name]["RelayTeams"] = []
            grouped[t_name]["RelayTeams"].append(item)

            relay_athletes = item.get("relayAthletes", [])
            for ath in relay_athletes:
                aid = ath.get("id")
                if not aid: continue
                found_key = id_lookup.get((t_name, aid))
                if not found_key:
                    try:
                        found_key = id_lookup.get((t_name, int(aid)))
                    except Exception: pass

                if found_key:
                    grp = grouped[t_name][found_key]
                else:
                    s_name = f"{ath.get('first', '')} {ath.get('last', '')}".strip()
                    s_age = ath.get("age", 0)
                    new_key = (s_name, s_age, t_name)
                    if new_key not in grouped[t_name]:
                        grouped[t_name][new_key] = {"name": s_name, "age": s_age, "team": t_name, "ind_count": 0, "rel_count": 0, "events": []}
                    grp = grouped[t_name][new_key]
                    id_lookup[(t_name, aid)] = new_key

                grp["events"].append(copy.copy(item))
                grp["rel_count"] += 1

        sorted_teams = sorted(grouped.keys())
        report_groups = []
        for t_name in sorted_teams:
            team_items = []
            real_athletes = [v for k, v in grouped[t_name].items() if k != "RelayTeams"]
            sorted_athletes = sorted(real_athletes, key=lambda x: x["name"])

            seq = 1
            for ath in sorted_athletes:
                gender = name_gender_map.get(ath["name"], "")
                t_code = team_code_map.get(t_name, t_name)
                parts = ath["name"].split(" ")
                display_name = f"{parts[-1]}, " + " ".join(parts[:-1]) if len(parts) >= 2 else ath["name"]
                age_val = ath.get("age") or 0
                h_parts = []
                if seq: h_parts.append(f"{seq} {display_name}")
                if gender: h_parts.append(gender)
                if age_val > 0: h_parts.append(f"Age: {age_val}")
                if t_code: h_parts.append(t_code)
                header_str = " - ".join(h_parts) + f" - Ind/Rel: {ath['ind_count']} / {ath['rel_count']}"

                def sort_key(e):
                    try: return int("".join(filter(str.isdigit, str(e["evt_num"]))))
                    except Exception: return 0

                sorted_events = sorted(ath["events"], key=sort_key)
                sub_rows = []
                for e in sorted_events:
                    desc_text = e["evt_desc"]
                    if e["is_relay"]: desc_text += " (Relay)"
                    sub_rows.append({"idx": f"#{e['evt_num']}", "desc": desc_text, "time": e["time"], "heat_lane": e["hl"]})
                team_items.append({"header": header_str, "sub_items": sub_rows})
                seq += 1

            relay_teams_list = grouped[t_name].get("RelayTeams", [])
            if relay_teams_list:
                team_items.append({"header": "   RELAY TEAMS", "sub_items": []})
                flat_relays = sorted(relay_teams_list, key=lambda x: int("".join(filter(str.isdigit, str(x["evt_num"])))))
                for idx, r in enumerate(flat_relays):
                    rltr = r.get("relayLtr", "")
                    ltr_str = f" - '{rltr}'" if rltr else ""
                    line1_desc = f"{t_name}{ltr_str}        #{r['evt_num']} {r['evt_desc']}"
                    hl_text = f"{r['heat']}/{r['lane']}" if r.get("heat") else ""
                    names_parts = [f"{a.get('last', '').strip()}, {a.get('first', '').strip()}" for a in r.get("relayAthletes", [])]
                    if not names_parts:
                        names_parts = [n.strip() for n in r.get("name", "").split(",")]
                    full_names_str = "; ".join(names_parts)
                    sub_items = [
                        {"idx": str(idx + 1), "desc": line1_desc, "time": r.get("seedTime", r.get("time", "")), "heat_lane": hl_text},
                        {"idx": "", "desc": "         " + full_names_str, "time": "", "heat_lane": ""}
                    ]
                    team_items.append({"header": "", "force_1col": True, "sub_items": sub_items})

            report_groups.append({"header": f"Team Entries - {t_name}", "athletes": team_items})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": report_title or "Entries - All Events", "groups": report_groups}

    def extract_meet_program_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
        columns_on_page: int = 2,
        show_relay_swimmers: bool = True,
    ) -> dict[str, Any]:
        full_data = self.converter.convert()
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        def evt_sort_key(e):
            try:
                num_part = re.search(r"\d+", str(e.get("eventNum", "0")))
                return int(num_part.group()) if num_part else 0
            except Exception: return 0

        all_events.sort(key=evt_sort_key)
        report_groups = []

        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            is_relay = evt.get("isRelay", False)
            entries = evt.get("entries", [])

            if gender_filter or age_group_filter:
                if gender_filter:
                    if gender_filter.lower() not in evt_desc.lower() and "mixed" not in evt_desc.lower():
                        continue
                if age_group_filter:
                    if age_group_filter.lower() not in evt_desc.lower():
                        continue

            if team_filter:
                entries = [e for e in entries if team_filter.lower() in e.get("team", "").lower()]

            if not entries: continue

            header = f"Event {evt_num}  {evt_desc}"
            heats = {}
            for entry in entries:
                h = entry.get("heat", 0)
                if h not in heats: heats[h] = []
                heats[h].append(entry)

            sorted_heats = sorted(heats.keys())
            heat_items = []
            for h in sorted_heats:
                heat_header = f"Heat {h} of {sorted_heats[-1]} Finals"
                heat_entries = sorted(heats[h], key=lambda x: x.get("lane", 0))
                sub_items = []
                for entry in heat_entries:
                    lane = entry.get("lane", "")
                    seed_time = entry.get("seedTime", "NT")
                    if is_relay:
                        names = []
                        if show_relay_swimmers:
                            if "relayAthletes" in entry:
                                names = [f"{a.get('last', '').strip()}, {a.get('first', '').strip()}" for a in entry["relayAthletes"]]
                            else:
                                names = [n.strip() for n in entry.get("name", "").split(",")]
                        sub_items.append({"lane": str(lane), "team": entry.get("team", ""), "relay_ltr": entry.get("relayLtr", ""), "time": seed_time, "swimmers": names, "is_relay": True})
                    else:
                        name = entry.get("name", "")
                        if "," not in name:
                            parts = name.split(" ")
                            name = f"{parts[-1]}, " + " ".join(parts[:-1]) if len(parts) >= 2 else name
                        sub_items.append({"lane": str(lane), "name": name, "age": str(entry.get("age", "")), "team": entry.get("team", ""), "time": seed_time, "is_relay": False})
                heat_items.append({"header": heat_header, "sub_items": sub_items})
            report_groups.append({"header": header, "heats": heat_items})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": report_title or "Meet Program", "groups": report_groups, "columns_on_page": columns_on_page, "show_relay_swimmers": show_relay_swimmers}

    def extract_psych_sheet_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
    ) -> dict[str, Any]:
        full_data = self.converter.convert()
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        all_events.sort(key=lambda e: self._safe_int(e.get("eventNum", 0)))
        report_groups = []
        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            entries = evt.get("entries", [])

            if gender_filter or age_group_filter:
                if gender_filter:
                    if gender_filter.lower() not in evt_desc.lower() and "mixed" not in evt_desc.lower():
                        continue
                if age_group_filter and age_group_filter.lower() not in evt_desc.lower():
                    continue

            if team_filter:
                entries = [e for e in entries if team_filter.lower() in e.get("team", "").lower()]

            if not entries: continue

            def time_sort_key(ent):
                t = ent.get("seedTime", "NT")
                if t == "NT": return 999999.0
                try:
                    parts = t.split(":")
                    if len(parts) == 2: return float(parts[0]) * 60 + float(parts[1])
                    return float(parts[0])
                except Exception: return 999999.0

            sorted_entries = sorted(entries, key=time_sort_key)
            sub_items = [{"name": e.get("name", ""), "team": e.get("team", ""), "age": str(e.get("age", "")), "time": e.get("seedTime", "NT")} for e in sorted_entries]
            report_groups.append({"header": f"Event {evt_num}  {evt_desc}", "sections": [{"sub_items": sub_items}]})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": report_title or "Psych Sheet", "groups": report_groups}

    def extract_timer_sheets_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
    ) -> dict[str, Any]:
        full_data = self.converter.convert()
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        all_events.sort(key=lambda e: self._safe_int(e.get("eventNum", 0)))
        report_groups = []
        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            entries = evt.get("entries", [])
            is_relay = evt.get("isRelay", False)

            if gender_filter or age_group_filter:
                if gender_filter:
                    if gender_filter.lower() not in evt_desc.lower() and "mixed" not in evt_desc.lower():
                        continue
                if age_group_filter:
                    if age_group_filter.lower() not in evt_desc.lower():
                        continue

            if team_filter:
                entries = [e for e in entries if team_filter.lower() in e.get("team", "").lower()]

            if not entries: continue

            header = f"Event {evt_num}  {evt_desc}"
            heats = {}
            for e in entries:
                h = self._safe_int(e.get("heat", 0))
                if h not in heats: heats[h] = []
                heats[h].append(e)

            sorted_heats = sorted(heats.keys())
            heat_items = []
            for h in sorted_heats:
                heat_entries = sorted(heats[h], key=lambda x: self._safe_int(x.get("lane", 0)))
                sub_items = []
                for entry in heat_entries:
                    item_data = {"lane": str(entry.get("lane", "")), "team": entry.get("team", ""), "time": entry.get("seedTime", "NT"), "is_relay": is_relay}
                    if is_relay:
                        item_data["relay_ltr"] = entry.get("relayLtr", "A")
                        names = [f"{a.get('last', '').strip()}, {a.get('first', '').strip()}" for a in entry.get("relayAthletes", [])]
                        if not names: names = [n.strip() for n in entry.get("name", "").split(",")]
                        item_data["swimmers"] = names
                    else:
                        name = entry.get("name", "")
                        if "," not in name:
                            parts = name.split(" ")
                            name = f"{parts[-1]}, " + " ".join(parts[:-1]) if len(parts) >= 2 else name
                        item_data["name"] = name
                    sub_items.append(item_data)
                heat_items.append({"header": f"Heat {h} of {sorted_heats[-1]} Finals", "sub_items": sub_items})
            report_groups.append({"header": header, "heats": heat_items})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": report_title or "Timer Sheets", "groups": report_groups}

    def extract_results_data(
        self,
        team_filter: str | None = None,
        report_title: str | None = None,
        gender_filter: str | None = None,
        age_group_filter: str | None = None,
    ) -> dict[str, Any]:
        full_data = self.converter.convert()
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        all_events.sort(key=lambda e: self._safe_int(e.get("eventNum", 0)))
        report_groups = []
        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            entries = evt.get("entries", [])

            if gender_filter or age_group_filter:
                if gender_filter:
                    if gender_filter.lower() not in evt_desc.lower() and "mixed" not in evt_desc.lower():
                        continue
                if age_group_filter and age_group_filter.lower() not in evt_desc.lower():
                    continue

            if team_filter:
                entries = [e for e in entries if team_filter.lower() in e.get("team", "").lower()]

            if not entries: continue

            finished = [e for e in entries if (e.get("place") and self._safe_int(e.get("place", 0)) > 0) or (e.get("finalTime") and e.get("finalTime") != "0.00" and e.get("finalTime") != "")]
            sorted_entries = sorted(finished, key=lambda x: self._safe_int(x.get("place", 0)) or 999)
            sub_items = [{"place": str(e.get("place", "")), "name": e.get("name", ""), "team": e.get("team", ""), "age": str(e.get("age", "")), "time": e.get("finalTime", e.get("seedTime", "")), "points": str(e.get("points", "0"))} for e in sorted_entries]
            report_groups.append({"header": f"Event {evt_num}  {evt_desc}", "sections": [{"sub_items": sub_items}]})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": report_title or "Meet Results", "groups": report_groups}

    def _safe_int(self, val, default=0):
        try: return int(float(val))
        except (ValueError, TypeError): return default
