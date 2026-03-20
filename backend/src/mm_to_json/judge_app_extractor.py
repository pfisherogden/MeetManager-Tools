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

        # Track unique IDs to avoid duplicates if same event/heat appears across sessions (rare but possible in MDB)
        # However, usually we just flatten everything.

        heat_id_counter = 1
        swimmer_id_counter = 1

        for sess in self.full_data.get("sessions", []):
            for evt in sess.get("events", []):
                # 1. Event
                # id in Judge App should be unique. MDB has event_no which is usually enough.
                # But event_no can repeat if there are multiple rounds (Pre/Fin).
                # Hierarchical 'convert' combines rounds? I need to check.
                # Actually converter.convert() is session-based.

                event_num = evt.get("eventNum")
                is_relay = evt.get("isRelay", False)

                judge_event = {
                    "id": event_num,  # Using event number as ID for now
                    "number": event_num,
                    "name": evt.get("eventDesc"),
                    "distance": evt.get("distance", 0),  # Added to Event model in converter if needed
                    "stroke": evt.get("stroke", ""),
                    "isRelay": is_relay,
                }
                judge_events.append(judge_event)

                # Group entries by heat
                heats_map: dict[int, list[dict[str, Any]]] = {}  # heat_num -> entries
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
                        "swimmers": [],  # Will be populated in the app if using DB, but we provide flat swimmers list
                    }
                    judge_heats.append(judge_heat)

                        # Use stable ID from MDB if available (athleteId for individual, relay_no for relays)
                        stable_id = entry.get("athleteId") or swimmer_id_counter
                        if not entry.get("athleteId"):
                            swimmer_id_counter += 1

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
