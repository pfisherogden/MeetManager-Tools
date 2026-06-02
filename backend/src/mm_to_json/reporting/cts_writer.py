import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class CTSScoreboardWriter:
    """
    Generates Colorado Time Systems (CTS) Scoreboard files (.scb) for Wahoo Results
     and an events CSV for the Dolphin timing system.
    """

    def __init__(self, meet_info: dict[str, Any], events: list[dict[str, Any]]):
        self.meet_info = meet_info
        self.events = events

    def generate_all(self, output_dir: str):
        """Generates all .scb files and the events.csv file in the target directory."""
        os.makedirs(output_dir, exist_ok=True)

        # 1. Generate events.csv (for Dolphin UI)
        self.generate_dolphin_events(os.path.join(output_dir, "events.csv"))

        # 2. Generate E{num:03}.scb for each event (for Wahoo Results)
        for event in self.events:
            event_num = event.get("eventNum", 0)
            filename = f"E{int(event_num):03}.scb"
            self.generate_event_scb(event, os.path.join(output_dir, filename))

    def generate_dolphin_events(self, output_path: str):
        """Generates the events.csv file expected by Dolphin UI."""
        lines = []
        # Format: event_num,description,heats,1,A
        for event in self.events:
            num = event.get("eventNum", 0)
            desc = event.get("eventDesc", "").upper()

            # Count heats
            entries = event.get("entries", [])
            max_heat = 0
            for entry in entries:
                max_heat = max(max_heat, entry.get("heat", 0))

            lines.append(f"{num},{desc},{max_heat},1,A")

        with open(output_path, "w", encoding="cp1252") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Generated {output_path}")

    def generate_event_scb(self, event: dict[str, Any], output_path: str):
        """Generates a single .scb file for an event."""
        num = event.get("eventNum", 0)
        desc = event.get("eventDesc", "").upper()
        entries = event.get("entries", [])

        # First line: #<num> <description>
        lines = [f"#{num} {desc}"]

        # Group entries by heat
        heats: dict[int, dict[int, dict[str, Any]]] = {}
        max_heat = 0
        for entry in entries:
            h = entry.get("heat", 0)
            if h <= 0:
                continue
            max_heat = max(max_heat, h)
            if h not in heats:
                heats[h] = {}
            heats[h][entry.get("lane", 0)] = entry

        # CTS SCB format requires exactly 10 lines per heat
        for h in range(1, max_heat + 1):
            heat_entries = heats.get(h, {})
            for lane in range(1, 11):
                entry = heat_entries.get(lane)
                if entry:
                    # Format: Swimmer Name (20 chars) + "--" + Team (16 chars)
                    name = entry.get("name", "")[:20].ljust(20)
                    team = entry.get("teamCode", "")[:16].ljust(16)
                    lines.append(f"{name}--{team}")
                else:
                    # Blank lane
                    lines.append(" " * 38)

        with open(output_path, "w", encoding="cp1252") as f:
            f.write("\n".join(lines) + "\n")
        # No info log here to avoid cluttering, we'll log at the end
