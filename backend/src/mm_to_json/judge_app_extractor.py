from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..mm_to_json import MmToJsonConverter


class JudgeAppExtractor:
    def __init__(self, converter: "MmToJsonConverter"):
        self.converter = converter
        # full_data is hierarchical: sessions -> events -> entries
        self.full_data = self.converter.convert()

    def extract_judge_data(self) -> dict[str, Any]:
        """
        Extracts data in the format expected by mobile-judge-app:
        {
            "events": Event[],
            "heats": Heat[],
            "swimmers": Swimmer[]
        }
        """
        judge_events = []
        judge_heats = []
        judge_swimmers = []

        heat_id_counter = 1
        swimmer_id_counter = 1

        for sess in self.full_data.get("sessions", []):
            for evt in sess.get("events", []):
                event_num = evt.get("eventNum")
                is_relay = evt.get("isRelay", False)

                judge_event = {
                    "id": event_num,
                    "number": event_num,
                    "name": evt.get("eventDesc"),
                    "distance": evt.get("distance", 0),
                    "stroke": evt.get("stroke", ""),
                    "isRelay": is_relay,
                }
                judge_events.append(judge_event)

                heats_map: dict[int, list[dict[str, Any]]] = {}
                for entry in evt.get("entries", []):
                    h_num = entry.get("heat", 0)
                    if h_num not in heats_map:
                        heats_map[h_num] = []
                    heats_map[h_num].append(entry)

                for h_num, entries in heats_map.items():
                    current_heat_id = heat_id_counter
                    heat_id_counter += 1

                    judge_heat = {
                        "id": current_heat_id,
                        "number": h_num,
                        "event_id": event_num,
                        "swimmers": [],
                    }
                    judge_heats.append(judge_heat)

                    for entry in entries:
                        stable_id = entry.get("athleteId") or swimmer_id_counter
                        if not entry.get("athleteId"):
                            swimmer_id_counter += 1

                        members = []
                        if is_relay:
                            if "relayAthletes" in entry:
                                members = [
                                    f"{a.get('firstName', '')} {a.get('lastName', '')}".strip()
                                    for a in entry["relayAthletes"]
                                ]
                            elif "name" in entry and entry.get("name"):
                                members = [n.strip() for n in entry["name"].split(",")]

                        if is_relay and len(members) < 4:
                            members.extend([""] * (4 - len(members)))

                        judge_swimmer = {
                            "id": stable_id,
                            "lane": entry.get("lane", 0),
                            "name": entry.get("name", ""),
                            "team": entry.get("team", ""),
                            "heat_id": current_heat_id,
                            "isRelay": is_relay,
                            "members": members,
                            "relay_dqs": [],
                            "notes": "",
                            "dq_code": "",
                        }
                        judge_swimmers.append(judge_swimmer)

        return {"events": judge_events, "heats": judge_heats, "swimmers": judge_swimmers}
