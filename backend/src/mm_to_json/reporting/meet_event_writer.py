import logging
import zipfile
from datetime import datetime
from typing import Any

# Credits:
# File format specifications (EV3/HYV) derived from research of:
# - SwimComm/hytek-parser (MIT License)
# - swimstandards/swimsnap (The Unlicense)

logger = logging.getLogger(__name__)


class MeetEventWriter:
    """
    Generates .ev3 and .hyv files from Meet Manager data for import into Team Manager / TeamUnify.
    """

    # Stroke mappings from Meet Manager (Letter) to Hy-Tek (Integer)
    STROKE_MAP = {
        "A": "1",  # Freestyle
        "B": "2",  # Backstroke
        "C": "3",  # Breaststroke
        "D": "4",  # Butterfly
        "E": "5",  # Individual Medley
        "F": "6",  # Freestyle Relay
        "G": "7",  # Medley Relay
    }

    def __init__(
        self,
        meet_info: dict[str, Any],
        sessions: list[dict[str, Any]],
        events: list[dict[str, Any]],
        scoring: list[dict[str, Any]],
    ):
        self.meet_info = meet_info
        self.sessions = sessions
        self.events = events
        self.scoring = scoring

    def _format_date(self, date_val: Any) -> str:
        """Converts millisecond timestamps or ISO strings to MM/DD/YYYY."""
        if not date_val:
            return ""
        try:
            if isinstance(date_val, (int, float)):
                dt = datetime.fromtimestamp(date_val / 1000)
            else:
                dt = datetime.strptime(str(date_val).split(" ")[0], "%Y-%m-%d")
            return dt.strftime("%m/%d/%Y")
        except Exception as e:
            logger.warning(f"Could not format date {date_val}: {e}")
            return str(date_val)

    def _generate_ev3_header(self) -> str:
        """Generates the EV3 meet header record."""
        # Reference: Meet Name(0);Location(1);Start(2);End(3);Age-Up(4);Course(5);0(6);0(7);0(8);Software(9);League(10);7.0Gb(11)...
        fields = [""] * 35
        fields[0] = str(self.meet_info.get("Meet_name1", ""))
        fields[1] = str(self.meet_info.get("Meet_location", ""))
        fields[2] = self._format_date(self.meet_info.get("Meet_start"))
        fields[3] = self._format_date(self.meet_info.get("Meet_end"))
        fields[4] = self._format_date(self.meet_info.get("Calc_date"))
        fields[5] = "YO"  # Yards
        fields[6] = "0"
        fields[7] = "0"
        fields[8] = "0"
        fields[9] = "Created by Hy-Tek's MEET MANAGER"
        fields[10] = "Tri-Valley Swim Lg. C"
        fields[11] = "7.0Gb"
        fields[12] = datetime.now().strftime("%m/%d/%Y")
        fields[13] = str(self.meet_info.get("entrymax_total", "3"))
        fields[15] = "0"

        # Field 16 seems to be a fixed date in manual exports (06/01/2025)
        # We'll use 6/1 of the previous year based on meet start
        try:
            m_start = datetime.fromtimestamp(self.meet_info["Meet_start"] / 1000)
            fields[16] = f"06/01/{m_start.year - 1}"
        except Exception:
            fields[16] = "06/01/2025"

        fields[17] = "0"
        fields[18] = str(self.meet_info.get("indmaxscorers_perteam", "4"))
        fields[19] = str(self.meet_info.get("relmaxscorers_perteam", "3"))  # Manual had 3
        fields[20] = str(self.meet_info.get("indmax_perath", "2"))  # Manual had 2
        fields[21] = str(self.meet_info.get("relmax_perath", "1"))  # Manual had 1
        fields[22] = "A"
        fields[23] = self._format_date(self.meet_info.get("entry_deadline"))
        fields[24] = str(self.meet_info.get("Meet_addr1", ""))
        fields[26] = str(self.meet_info.get("Meet_city", "Pleasanton"))
        fields[27] = str(self.meet_info.get("Meet_state", "CA"))
        fields[28] = str(self.meet_info.get("Meet_zip", "94566"))
        fields[29] = "USA"
        fields[30] = str(self.meet_info.get("Meet_hostlsc", "CC"))
        fields[31] = "N"
        fields[32] = "N"
        fields[33] = fields[16]  # Matches field 16
        fields[34] = "0000l"  # Checksum placeholder

        return ";".join(fields) + "*>"

    def _generate_ev3_event_record(self, event: dict[str, Any], sess_order: int) -> str:
        """Generates an EV3 event record."""
        # 30 fields
        fields = [""] * 30
        fields[0] = str(event.get("Event_no", "0"))
        fields[1] = str(event.get("Event_no", "0"))
        fields[2] = "F"  # Final
        fields[3] = str(event.get("Session", "1"))
        fields[4] = str(event.get("Ind_rel", "I"))
        fields[5] = str(event.get("Event_sex", "X"))
        fields[6] = str(event.get("Low_age", "0"))
        fields[7] = str(event.get("High_Age", "18"))

        # Ensure distance is integer
        dist = event.get("Event_dist", 0)
        try:
            fields[8] = str(int(float(dist)))
        except Exception:
            fields[8] = str(dist)

        fields[9] = str(event.get("Event_stroke", "A"))
        fields[10] = "0"
        fields[13] = "N"  # Not locked
        fields[14] = "0"

        fields[21] = str(event.get("Session", "1"))
        fields[22] = str(sess_order)
        fields[23] = "1"

        # Time mapping
        start_time = "09:00AM"
        if int(event.get("Session", 1)) > 1:
            # Simple heuristic for multi-session start times
            times = ["", "09:00AM", "09:36AM", "10:12AM", "10:48AM", "11:24AM", "12:00PM", "01:00PM"]
            s_idx = int(event.get("Session", 1))
            if s_idx < len(times):
                start_time = times[s_idx]

        fields[24] = start_time
        fields[25] = "Y"  # Yards
        fields[26] = "0"
        fields[27] = "0"
        fields[28] = "0"

        # Relay size (4 for relay, 0 for individual)
        fields[29] = "4" if fields[4] == "R" else "0"

        return ";".join(fields) + "*>"

    def _generate_hyv_header(self) -> str:
        """Generates the HYV meet header record."""
        # 11 fields
        fields = [""] * 11
        fields[0] = str(self.meet_info.get("Meet_name1", ""))
        fields[1] = self._format_date(self.meet_info.get("Meet_start"))
        fields[2] = self._format_date(self.meet_info.get("Meet_end"))
        fields[3] = self._format_date(self.meet_info.get("Calc_date"))
        fields[4] = "Y"  # Yards
        fields[5] = str(self.meet_info.get("Meet_location", ""))
        fields[7] = "Hy-Tek Sports Software"
        fields[8] = "7.0Gb"
        fields[9] = "CN"
        fields[10] = "0000l"  # Checksum placeholder

        return ";".join(fields)

    def _generate_hyv_event_record(self, event: dict[str, Any]) -> str:
        """Generates an HYV event record."""
        # 18 fields
        fields = [""] * 18
        fields[0] = str(event.get("Event_no", "0"))
        fields[1] = "F"  # Rnd

        sex = str(event.get("Event_sex", "X"))
        if sex == "G":
            sex = "F"
        if sex == "B":
            sex = "M"
        fields[2] = sex

        fields[3] = str(event.get("Ind_rel", "I"))
        fields[4] = str(event.get("Low_age", "0"))
        fields[5] = str(event.get("High_Age", "18"))

        dist = event.get("Event_dist", 0)
        try:
            fields[6] = str(int(float(dist)))
        except Exception:
            fields[6] = str(dist)

        fields[7] = self.STROKE_MAP.get(str(event.get("Event_stroke", "A")), "1")
        fields[11] = "0"

        return ";".join(fields)

    def write_to_zip(self, output_zip_path: str):
        """Generates the EV3 and HYV files and packages them into a ZIP."""
        ev3_content = [self._generate_ev3_header()]
        hyv_content = [self._generate_hyv_header()]

        # Group events by session for order
        events_by_session: dict[int, list[dict[str, Any]]] = {}
        for event in self.events:
            s_id = int(event.get("Session", 1))
            if s_id not in events_by_session:
                events_by_session[s_id] = []
            events_by_session[s_id].append(event)

        for s_id in sorted(events_by_session.keys()):
            session_events = events_by_session[s_id]
            # Sort by event number within session
            session_events.sort(key=lambda x: int(x.get("Event_no", 0)))
            for i, event in enumerate(session_events, 1):
                ev3_content.append(self._generate_ev3_event_record(event, sess_order=i))
                hyv_content.append(self._generate_hyv_event_record(event))

        meet_name = self.meet_info.get("Meet_name1", "Meet").replace(" ", "_")
        start_date = self._format_date(self.meet_info.get("Meet_start")).replace("/", "")
        base_name = f"Meet Events-{meet_name}-{start_date}-001"

        ev3_filename = f"{base_name}.ev3"
        hyv_filename = f"{base_name}.hyv"

        with zipfile.ZipFile(output_zip_path, "w") as zipf:
            # Ensure windows-style line endings for compatibility
            zipf.writestr(ev3_filename, "\r\n".join(ev3_content) + "\r\n")
            zipf.writestr(hyv_filename, "\r\n".join(hyv_content) + "\r\n")

        logger.info(f"Generated meet events ZIP: {output_zip_path}")
        return output_zip_path
