from typing import Any

from ..mm_to_json import MmToJsonConverter


class ReportDataExtractor:
    def __init__(self, converter: MmToJsonConverter):
        self.converter = converter

    def extract_meet_entries_data(self, team_filter: str = None) -> dict[str, Any]:
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
        # We can use the converter's convert() method to get the hierarchical events,
        # then flatten back to athletes.
        full_data = self.converter.convert()

        # We need to map formatted entries back to athletes.
        # But convert() loses some raw data (like athlete ID).
        # Better to iterate raw ENTRY table?
        # Creating a map of Event_ptr -> EventDesc/No

        for sess in full_data.get("sessions", []):
            for _evt in sess.get("events", []):
                # We need the Event_ptr to link raw entries.
                # convert() puts entries inside.
                # Let's use the 'entries' list from convert() as it has seedTime formatted
                # But it doesn't have athlete ID easily.
                # Actually earlier I saw add_individual_entries does a look up by ID.
                # Let's rely on the convert() output for now, but we need to match name/age/team to ath_map?
                # That is risky.

                # Robust approach:
                # Use raw ENTRY table + self.converter.get_heat_lane_time logic.
                pass

        # Let's use the raw tables to be precise.
        df_entry = self.converter.tables.get("Entry", None)
        df_event = self.converter.tables.get("Event", None)

        if df_entry is None or df_event is None:
            return {"groups": []}

        # Build Event Info Map
        # Pointer -> {Num, Desc}
        for _, row in df_event.iterrows():
            row.get("Event_ptr")
            num = str(row.get("Event_no"))
            ltr = row.get("Event_ltr", "")
            if ltr:
                num += ltr

            int(row.get("Event_dist", 0))
            row.get("Event_stroke", "S")  # 'A'='Free'?? Need map
            # MmToJsonConverter has stroke_map but it's internal logic
            # Let's construct a description
            # Actually, reusing converter.get_event_name is safer
            # But that requires an object.

            # Simple map
            # This map might be wrong for this DB.
            # Let's peek at MmToJson using view_code? No time.
            # Let's rely on the converter's `convert()` output for Event definitions
            # and map via `eventNum`?
            # Data from `convert()` is: sessions -> events -> entries
            pass

        # HYBRID APPROACH
        # Use `convert()` to get the nice event descriptions and processed entries.
        # But we need to group by Athlete.
        # The entries in `convert()` output have: name, age, team, seedTime, heat, lane.
        # We can iterate these and group by (Team, Name, Age).

        flat_entries = []

        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                evt_num = evt.get("eventNum")
                evt_desc = evt.get("eventDesc")
                is_relay = evt.get("isRelay", False)

                for entry in evt.get("entries", []):
                    # Filter by team if needed
                    t_name = entry.get("team", "")
                    # This is the team NAME from helper, might not match filter if filter is Code.
                    # But if we pass team_filter to extract, we can check.

                    # Group Key: Name + Age + Team
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

        # Map: Team -> AthleteKey -> Dict
        # Special key "RelayTeams" for list of relay entries
        grouped = {}

        # New approach: Iterate and distribute
        # We need `team_filter` checking early
        pass  # Replaced by logic in chunk 1 (see replacement below)

        # actually removing the old loop completely to avoid duplicates
        # The chunk 1 replaces the loop logic

        # We need Gender and Team Code.
        # We can try to look up in `ath_map` by name/age match?
        # Dictionary fuzzy match...
        # Let's try to enhance `ath_map` lookup.

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
        grouped = {}

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
                # We need to find the ID stored in the first event?
                # The group key doesn't store ID. But events do.
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
                    # print(f"DEBUG: Skipping athlete {ath} - No ID")
                    continue

                # Look up existing
                found_key = id_lookup.get((t_name, aid))

                if not found_key:
                    # Check with int conversion?
                    try:
                        found_key = id_lookup.get((t_name, int(aid)))
                    except Exception:
                        pass

                if found_key:
                    grp = grouped[t_name][found_key]
                else:
                    # New athlete (Relay only)
                    # Use actual data from athlete object!
                    s_name = f"{ath.get('first', '')} {ath.get('last', '')}".strip()
                    s_age = ath.get("age", 0)

                    # Create key (Name, Age, Team) - standard key format
                    new_key = (s_name, s_age, t_name)

                    # Check if key exists (unlikely if ID didn't match, unless ID missing)
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
                    # Add to lookup
                    id_lookup[(t_name, aid)] = new_key

                # Add event (clone)
                import copy

                evt_clone = copy.copy(item)
                # Ensure we don't duplicate events if swimmer is in multiple relays?
                # No, we want to list all relays they are in.

                grp["events"].append(evt_clone)
                grp["rel_count"] += 1

        sorted_teams = sorted(grouped.keys())
        report_groups = []
        for t_name in sorted_teams:
            team_items = []

            # Sort Athletes by Name
            # Exclude special "RelayTeams" key
            real_athletes = [v for k, v in grouped[t_name].items() if k != "RelayTeams"]
            sorted_athletes = sorted(real_athletes, key=lambda x: x["name"])

            seq = 1
            for ath in sorted_athletes:
                # Patch Gender/Code
                # Try exact match or partial
                # Our entry name is "First Last". Map key is "First Last".
                gender = name_gender_map.get(ath["name"], "")
                t_code = team_code_map.get(t_name, t_name)  # Fallback to name

                # Reformat name to "Last, First" for report
                # Split "First Last" -> "Last, First"
                parts = ath["name"].split(" ")
                if len(parts) >= 2:
                    display_name = f"{parts[-1]}, " + " ".join(parts[:-1])
                else:
                    display_name = ath["name"]

                # Format Header with conditional separators
                age_val = ath.get("age") or 0

                # Filter empty strings to avoid extra dashes
                parts = []
                if seq:
                    parts.append(f"{seq} {display_name}")
                if gender:
                    parts.append(gender)
                if age_val > 0:
                    parts.append(f"Age: {age_val}")
                if t_code:
                    parts.append(t_code)

                # Join with " - "
                main_header = " - ".join(parts)
                header_str = f"{main_header} - Ind/Rel: {ath['ind_count']} / {ath['rel_count']}"

                # Sub-items (Events) for the grid
                # Need to be sorted by Event Num
                # Event Num is string "31", "3", etc. Need int sort.
                def sort_key(e):
                    try:
                        return int("".join(filter(str.isdigit, str(e["evt_num"]))))
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
                # Add divider/section header
                team_items.append({"header": "   RELAY TEAMS", "sub_items": []})

                # Separate list logic
                flat_relays = []
                current_relay_seq = 1
                for item in relay_teams_list:
                    flat_relays.append(item)

                flat_relays.sort(key=lambda x: int("".join(filter(str.isdigit, str(x["evt_num"])))))

                for _i, r in enumerate(flat_relays):
                    # Match Relay Letter from Team Name or relayLtr
                    rltr = r.get("relayLm", "")  # Try legacy first? No, relayLtr is better.
                    if not rltr:
                        rltr = r.get("relayLtr", "")

                    ltr_str = f" - '{rltr}'" if rltr else ""

                    # Construct Description: "TeamName - 'Ltr'   #EvtNum EventDesc"
                    # Need Team Name? It's t_name from loop variable
                    # Use fixed width spacing or just string concatenation?
                    # Renderer table handles wrapping.
                    # Format: "TeamName - 'A'                       #4 Event..."
                    # Use non-breaking spaces? Or just spaces?
                    # Let's use spaces.
                    # Actually, `t_name` is available.

                    # First line content
                    line1_desc = f"{t_name}{ltr_str}        #{r['evt_num']} {r['evt_desc']}"

                    # H/L
                    hl_text = ""
                    if r.get("heat"):
                        hl_text = f"{r['heat']}/{r['lane']}"

                    # Names formatting (Last, First; Last, First)
                    formatted_lines = []
                    names_parts = []

                    if "relayAthletes" in r:
                        for ath in r["relayAthletes"]:
                            fn = ath.get("first", "").strip()
                            ln = ath.get("last", "").strip()
                            names_parts.append(f"{ln}, {fn}")
                    else:
                        # Fallback
                        names_list = [n.strip() for n in r["name"].split(",")]
                        for n in names_list:
                            parts = n.split(" ")
                            if len(parts) >= 2:
                                names_parts.append(f"{parts[-1]}, " + " ".join(parts[:-1]))
                            else:
                                names_parts.append(n)

                    full_names_str = "; ".join(names_parts)
                    formatted_lines.append(full_names_str)

                    # Prepare Sub-Items for Table (2 lines)
                    sub_items = []

                    # Row 1: Seq | Team - 'Ltr' ... | Time | H/L
                    # Using columns: idx, desc, time, heat_lane
                    # Use enumerate in loop

                    sub_items.append(
                        {
                            "idx": str(current_relay_seq),
                            "desc": line1_desc,
                            "time": r.get("seedTime", r.get("time", "")),
                            "heat_lane": hl_text,
                        }
                    )

                    # Row 2: Empty | Names | Empty | Empty
                    # Indent names?
                    # Just put in desc column.
                    sub_items.append(
                        {
                            "idx": "",
                            "desc": "         " + full_names_str,  # Indent with spaces
                            "time": "",
                            "heat_lane": "",
                        }
                    )

                    team_items.append(
                        {
                            "header": "",  # Empty header, using table for content
                            "force_1col": True,
                            "sub_items": sub_items,
                        }
                    )
                    current_relay_seq += 1

            report_groups.append({"header": f"Team Entries - {t_name}", "items": team_items})

        return {
            "meet_name": full_data.get("meetName", ""),
            "sub_title": "Entries - All Events",
            "groups": report_groups,
        }

    def extract_meet_program_data(self, team_filter: str = None) -> dict[str, Any]:
        """
        Extracts data for the Meet Program report.

        The data is structured as follows:
        Groups -> Event Header -> Heats -> Entries (Lanes)

        Args:
            team_filter (str): Optional team name or code to filter by. (Not fully implemented yet for program)

        Returns:
            dict: Structured data ready for the PDFRenderer.
        """
        # 1. Convert MDB data to hierarchical JSON structure
        full_data = self.converter.convert()

        # 2. Collect all events from across all sessions
        all_events = []
        for sess in full_data.get("sessions", []):
            for evt in sess.get("events", []):
                all_events.append(evt)

        # 3. Sort events numerically (handling alphanumeric event numbers like "1A")
        def evt_sort_key(e):
            try:
                import re

                num_part = re.search(r"\d+", str(e.get("eventNum", "0")))
                val = int(num_part.group()) if num_part else 0
                return val
            except Exception:
                return 0

        all_events.sort(key=evt_sort_key)

        report_groups = []

        # 4. Process each event into report groups
        for evt in all_events:
            evt_num = evt.get("eventNum")
            evt_desc = evt.get("eventDesc")
            is_relay = evt.get("isRelay", False)
            entries = evt.get("entries", [])

            # Format the visual Event Header
            header = f"Event {evt_num}  {evt_desc}"

            # 5. Group entries by heat number
            heats = {}
            for entry in entries:
                h = entry.get("heat", 0)
                if h not in heats:
                    heats[h] = []
                heats[h].append(entry)

            sorted_heats = sorted(heats.keys())

            heat_items = []
            # 6. Process each heat
            for h in sorted_heats:
                heat_header = f"Heat {h} of {sorted_heats[-1]} Finals"
                heat_entries = sorted(heats[h], key=lambda x: x.get("lane", 0))

                sub_items = []
                # 7. Format each entry (Relay vs Individual)
                for entry in heat_entries:
                    lane = entry.get("lane", "")
                    seed_time = entry.get("seedTime", "NT")

                    if is_relay:
                        # Relay entries include a list of structured swimmers
                        t_name = entry.get("team", "")
                        r_ltr = entry.get("relayLtr", "")

                        names = []
                        if "relayAthletes" in entry:
                            # Preferred: use full athlete objects for accurate Last, First formatting
                            for ath in entry["relayAthletes"]:
                                fn = ath.get("first", "").strip()
                                ln = ath.get("last", "").strip()
                                names.append(f"{ln}, {fn}")
                        else:
                            # Fallback: parse from single string name
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
                        # Individual entries include standard fields
                        name = entry.get("name", "")
                        age = entry.get("age", "")
                        team = entry.get("team", "")

                        # Ensure consistently formatted name: "Last, First"
                        if "," not in name:
                            parts = name.split(" ")
                            if len(parts) >= 2:
                                name = f"{parts[-1]}, " + " ".join(parts[:-1])

                        sub_items.append(
                            {
                                "lane": str(lane),
                                "name": name,
                                "age": str(age),
                                "team": team,
                                "time": seed_time,
                                "is_relay": False,
                            }
                        )

                heat_items.append({"header": heat_header, "sub_items": sub_items})

            report_groups.append({"header": header, "items": heat_items})

        return {"meet_name": full_data.get("meetName", ""), "sub_title": "Meet Program", "groups": report_groups}
