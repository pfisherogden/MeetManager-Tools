from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..mm_to_json import MmToJsonConverter


class ReportDataExtractor:
    def __init__(self, converter: "MmToJsonConverter"):
        self.converter = converter

    def extract_meet_entries_data(self, team_filter: str | None = None) -> dict[str, Any]:
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
            initial = str(row.get("Initial", "")).strip()  # Middle Initial
            sex = str(row.get("Sex", "")).strip()
            age = row.get("Ath_age")

            # Filter by team if requested
            t_info = team_map.get(t_id)
            if team_filter:
                # Check against code or name
                if not t_info:
                    continue
                if team_filter.lower() not in [t_info["code"].lower(), t_info["name"].lower()]:
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

        # 4. Iterate Events and Entries to link to Athletes
        full_data = self.converter.convert()

        flat_entries = []

        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                evt_num = evt.get("eventNum")
                evt_desc = evt.get("eventDesc")
                is_relay = evt.get("isRelay", False)

                for entry in evt.get("entries", []):
                    # Group Key: Name + Age + Team
                    t_name = entry.get("team", "")
                    key = (entry.get("name"), entry.get("age"), t_name)

                    # Heat/Lane formatting
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

        # Build name map to help resolving relay names and gender/code
        name_gender_map = {}
        team_code_map = {}  # Team Name -> Team Code

        for _, row in df_ath.iterrows():
            try:
                first_name = str(row.get("First_name", row.get("First", ""))).strip()
                last_name = str(row.get("Last_name", row.get("Last", ""))).strip()
                sex = str(row.get("Sex", "")).strip()
                full_fl = f"{first_name} {last_name}"  # First Last
                full_lf = f"{last_name}, {first_name}"  # Last, First

                name_gender_map[full_fl] = "Female" if sex == "F" else "Male" if sex == "M" else sex
                name_gender_map[full_lf] = name_gender_map[full_fl]

                tid = row.get("Team_no", row.get("Team1"))
                if tid in team_map:
                    tname = team_map[tid]["name"]
                    tcode = team_map[tid]["code"]
                    team_code_map[tname] = tcode
            except Exception:
                pass

        # Grouping Logic
        grouped: dict[str, dict[Any, Any]] = {}

        # Split into Individuals and Relays for processing order
        ind_entries = [e for e in flat_entries if not e["is_relay"]]
        relay_entries = [e for e in flat_entries if e["is_relay"]]

        # 1. Process Individual Entries first to establish athlete base
        for item in ind_entries:
            t_name = item["team"]
            if team_filter and team_filter.lower() not in t_name.lower():
                continue

            key = item["key"]  # (Name, Age, Team)

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

        # 2. Build Lookup Map for existing athletes in this team
        # (Team, AthleteID) -> Key
        id_lookup = {}

        for t_name, athletes in grouped.items():
            for key, data in athletes.items():
                if key == "RelayTeams":
                    continue
                if data["events"]:
                    first_evt = data["events"][0]
                    aid = first_evt.get("athleteId")
                    if aid:
                        id_lookup[(t_name, aid)] = key

        # 3. Process Relay Entries using detailed athlete lists
        for item in relay_entries:
            t_name = item["team"]
            if team_filter and team_filter.lower() not in t_name.lower():
                continue

            # Add to RelayTeams list for the section
            if t_name not in grouped:
                grouped[t_name] = {}
            if "RelayTeams" not in grouped[t_name]:
                grouped[t_name]["RelayTeams"] = []
            grouped[t_name]["RelayTeams"].append(item)

            # Attribute to individuals using relayAthletes list
            relay_athletes = item.get("relayAthletes", [])

            for ath in relay_athletes:
                aid = ath.get("id")
                if not aid:
                    continue

                # Look up existing
                found_key = id_lookup.get((t_name, aid))

                if not found_key:
                    try:
                        found_key = id_lookup.get((t_name, int(aid)))
                    except Exception:
                        pass

                if found_key:
                    grp = grouped[t_name][found_key]
                else:
                    # New athlete (Relay only)
                    s_name = f"{ath.get('first', '')} {ath.get('last', '')}".strip()
                    s_age = ath.get("age", 0)
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

                # Add event (clone)
                import copy

                evt_clone = copy.copy(item)
                grp["events"].append(evt_clone)
                grp["rel_count"] += 1

        sorted_teams = sorted(grouped.keys())
        report_groups = []
        for t_name in sorted_teams:
            team_items: list[dict[str, Any]] = []

            # Sort Athletes by Name
            real_athletes = [v for k, v in grouped[t_name].items() if k != "RelayTeams"]
            sorted_athletes = sorted(real_athletes, key=lambda x: x["name"])

            seq = 1
            for ath in sorted_athletes:
                gender = name_gender_map.get(ath["name"], "")
                t_code = team_code_map.get(t_name, t_name)

                # Reformat name to "Last, First"
                parts = ath["name"].split(" ")
                if len(parts) >= 2:
                    display_name = f"{parts[-1]}, " + " ".join(parts[:-1])
                else:
                    display_name = ath["name"]

                age_val = ath.get("age") or 0
                parts = []
                if seq:
                    parts.append(f"{seq} {display_name}")
                if gender:
                    parts.append(gender)
                if age_val > 0:
                    parts.append(f"Age: {age_val}")
                if t_code:
                    parts.append(t_code)

                header_str = " - ".join(parts) + f" - Ind/Rel: {ath['ind_count']} / {ath['rel_count']}"

                def sort_key(e):
                    try:
                        import re

                        num_part = re.search(r"\d+", str(e["evt_num"]))
                        return int(num_part.group()) if num_part else 0
                    except Exception:
                        return 0

                sorted_events = sorted(ath["events"], key=sort_key)

                sub_rows = []
                for e in sorted_events:
                    desc_text = e["evt_desc"]
                    if e["is_relay"]:
                        desc_text += " (Relay)"
                    sub_rows.append(
                        {"idx": f"#{e['evt_num']}", "desc": desc_text, "time": e["time"], "heat_lane": e["hl"]}
                    )

                team_items.append({"header": header_str, "sub_items": sub_rows})
                seq += 1

            # Process Relay Teams
            relay_teams_list = grouped[t_name].get("RelayTeams", [])
            if relay_teams_list:
                team_items.append({"header": "   RELAY TEAMS", "sub_items": []})
                flat_relays = sorted(
                    relay_teams_list, key=lambda x: int("".join(filter(str.isdigit, str(x["evt_num"]))))
                )

                current_relay_seq = 1
                for r in flat_relays:
                    rltr = r.get("relayLtr", "")
                    ltr_str = f" - '{rltr}'" if rltr else ""
                    line1_desc = f"{t_name}{ltr_str}        #{r['evt_num']} {r['evt_desc']}"
                    hl_text = f"{r['heat']}/{r['lane']}" if r.get("heat") else ""

                    names_parts = []
                    if "relayAthletes" in r:
                        for ath in r["relayAthletes"]:
                            fn = ath.get("first", "").strip()
                            ln = ath.get("last", "").strip()
                            names_parts.append(f"{ln}, {fn}")
                    else:
                        names_list = [n.strip() for n in r["name"].split(",")]
                        for n in names_list:
                            parts = n.split(" ")
                            if len(parts) >= 2:
                                names_parts.append(f"{parts[-1]}, " + " ".join(parts[:-1]))
                            else:
                                names_parts.append(n)

                    full_names_str = "; ".join(names_parts)
                    sub_items = [
                        {
                            "idx": str(current_relay_seq),
                            "desc": line1_desc,
                            "time": r.get("seedTime", r.get("time", "")),
                            "heat_lane": hl_text,
                        },
                        {"idx": "", "desc": "         " + full_names_str, "time": "", "heat_lane": ""},
                    ]
                    team_items.append({"header": "", "force_1col": True, "sub_items": sub_items})
                    current_relay_seq += 1

            report_groups.append({"header": f"Team Entries - {t_name}", "items": team_items})

        return {
            "meet_name": full_data.get("meetName", ""),
            "sub_title": "Entries - All Events",
            "groups": report_groups,
        }

    def extract_meet_program_data(self, team_filter: str | None = None) -> dict[str, Any]:
        """
        Extracts data for the Meet Program report.
        """
        full_data = self.converter.convert()
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        def evt_sort_key(e):
            try:
                import re

                num_part = re.search(r"\d+", str(e.get("eventNum", "0")))
                return int(num_part.group()) if num_part else 0
            except Exception:
                return 0

        all_events.sort(key=evt_sort_key)

        report_groups = []
        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            is_relay = evt.get("isRelay", False)
            entries = evt.get("entries", [])

            header = f"Event {evt_num}  {evt_desc}"
            heats: dict[int, list[dict[str, Any]]] = {}
            for entry in entries:
                h = entry.get("heat", 0)
                if h not in heats:
                    heats[h] = []
                heats[h].append(entry)

            heat_items = []
            for h in sorted(heats.keys()):
                heat_header = f"Heat {h} of {max(heats.keys())} Finals"
                heat_entries = sorted(heats[h], key=lambda x: x.get("lane", 0))

                sub_items = []
                for entry in heat_entries:
                    lane = entry.get("lane", "")
                    seed_time = entry.get("seedTime", "NT")

                    if is_relay:
                        t_name = entry.get("team", "")
                        r_ltr = entry.get("relayLtr", "")
                        names = []
                        if "relayAthletes" in entry:
                            for ath in entry["relayAthletes"]:
                                names.append(f"{ath.get('last', '').strip()}, {ath.get('first', '').strip()}")
                        else:
                            names = [n.strip() for n in entry.get("name", "").split(",")]

                        sub_items.append(
                            {
                                "lane": str(lane),
                                "team": t_name,
                                "relay_ltr": r_ltr,
                                "time": seed_time,
                                "swimmers": names,
                                "is_relay": True,
                            }
                        )
                    else:
                        name = entry.get("name", "")
                        if "," not in name:
                            parts = name.split(" ")
                            if len(parts) >= 2:
                                name = f"{parts[-1]}, " + " ".join(parts[:-1])

                        sub_items.append(
                            {
                                "lane": str(lane),
                                "name": name,
                                "age": str(entry.get("age", "")),
                                "team": entry.get("team", ""),
                                "time": seed_time,
                                "is_relay": False,
                            }
                        )
                heat_items.append({"header": heat_header, "sub_items": sub_items})
            report_groups.append({"header": header, "items": heat_items})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": "Meet Program", "groups": report_groups}

    def extract_psych_sheet_data(self) -> dict[str, Any]:
        """
        Extracts data for the Psych Sheet report.
        Groups -> Event Header -> Entries (Sorted by Time)
        """
        full_data = self.converter.convert()
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        def evt_sort_key(e):
            try:
                import re

                num_part = re.search(r"\d+", str(e.get("eventNum", "0")))
                return int(num_part.group()) if num_part else 0
            except Exception:
                return 0

        all_events.sort(key=evt_sort_key)

        report_groups = []
        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            entries = evt.get("entries", [])

            def time_sort_key(en):
                t = en.get("seedTime", "NT")
                if t == "NT":
                    return "99:99.99"
                return t

            sorted_entries = sorted(entries, key=time_sort_key)

            sub_items = []
            for i, entry in enumerate(sorted_entries):
                name = entry.get("name", "")
                if "," not in name:
                    parts = name.split(" ")
                    if len(parts) >= 2:
                        name = f"{parts[-1]}, " + " ".join(parts[:-1])

                sub_items.append(
                    {
                        "rank": str(i + 1),
                        "name": name,
                        "age": str(entry.get("age", "")),
                        "team": entry.get("team", ""),
                        "time": entry.get("seedTime", "NT"),
                    }
                )

            report_groups.append({"header": f"Event {evt_num}  {evt_desc}", "items": [{"sub_items": sub_items}]})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": "Psych Sheet", "groups": report_groups}

    def extract_timer_sheets_data(self) -> dict[str, Any]:
        """
        Extracts data for Timer Sheets.
        """
        full_data = self.converter.convert()
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        def evt_sort_key(e):
            try:
                import re

                num_part = re.search(r"\d+", str(e.get("eventNum", "0")))
                return int(num_part.group()) if num_part else 0
            except Exception:
                return 0

        all_events.sort(key=evt_sort_key)

        report_groups = []
        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            entries = evt.get("entries", [])

            heats: dict[int, list[dict[str, Any]]] = {}
            for entry in entries:
                h = entry.get("heat", 0)
                if h not in heats:
                    heats[h] = []
                heats[h].append(entry)

            for h_num in sorted(heats.keys()):
                heat_entries = sorted(heats[h_num], key=lambda x: x.get("lane", 0))
                header = f"Event {evt_num}: {evt_desc} - Heat {h_num}"

                sub_items = []
                for entry in heat_entries:
                    name = entry.get("name", "")
                    if "," not in name:
                        parts = name.split(" ")
                        if len(parts) >= 2:
                            name = f"{parts[-1]}, " + " ".join(parts[:-1])

                    sub_items.append(
                        {
                            "lane": str(entry.get("lane", "")),
                            "name": name,
                            "team": entry.get("team", ""),
                            "seed": entry.get("seedTime", "NT"),
                        }
                    )
                report_groups.append({"header": header, "items": [{"sub_items": sub_items}]})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": "Timer Sheets", "groups": report_groups}

    def extract_results_data(self) -> dict[str, Any]:
        """
        Extracts data for Meet Results.
        """
        full_data = self.converter.convert()
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        def evt_sort_key(e):
            try:
                import re

                num_part = re.search(r"\d+", str(e.get("eventNum", "0")))
                return int(num_part.group()) if num_part else 0
            except Exception:
                return 0

        all_events.sort(key=evt_sort_key)

        report_groups = []
        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            entries = evt.get("entries", [])

            def results_sort_key(en):
                t = en.get("psTime", "NT")
                if t == "NT" or t == "DQ":
                    return "99:99.99"
                return t

            sorted_entries = sorted(entries, key=results_sort_key)

            sub_items = []
            for i, entry in enumerate(sorted_entries):
                name = entry.get("name", "")
                if "," not in name:
                    parts = name.split(" ")
                    if len(parts) >= 2:
                        name = f"{parts[-1]}, " + " ".join(parts[:-1])

                final_time = entry.get("psTime", "NT")
                place = str(i + 1) if final_time != "NT" else ""

                sub_items.append(
                    {
                        "place": place,
                        "name": name,
                        "age": str(entry.get("age", "")),
                        "team": entry.get("team", ""),
                        "seed": entry.get("seedTime", "NT"),
                        "time": final_time,
                    }
                )
            report_groups.append({"header": f"Event {evt_num}  {evt_desc}", "items": [{"sub_items": sub_items}]})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": "Results", "groups": report_groups}
