import logging
import zipfile
from datetime import datetime
from typing import Any

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
        # Reference: Meet Name;Location;Start;End;Age-Up;Course;...
        fields = [""] * 36
        fields[0] = str(self.meet_info.get("Meet_name1", ""))
        fields[1] = str(self.meet_info.get("Meet_location", ""))
        fields[2] = self._format_date(self.meet_info.get("Meet_start"))
        fields[3] = self._format_date(self.meet_info.get("Meet_end"))
        fields[4] = self._format_date(self.meet_info.get("Calc_date"))
        fields[5] = "YO"  # Yards
        fields[10] = "Tri-Valley Swim Lg. C"
        fields[11] = "8.0Gb"  # Version identifier
        fields[12] = datetime.now().strftime("%m/%d/%Y")
        fields[16] = self._format_date(self.meet_info.get("Meet_start"))
        fields[18] = str(self.meet_info.get("indmax_perath", "3"))
        fields[19] = str(self.meet_info.get("relmax_perath", "2"))
        fields[20] = str(self.meet_info.get("entrymax_total", "4"))
        fields[21] = "1"  # ???
        fields[22] = "A"  # Standard
        fields[26] = str(self.meet_info.get("Meet_city", "Pleasanton"))
        fields[27] = str(self.meet_info.get("Meet_state", "CA"))
        fields[28] = str(self.meet_info.get("Meet_zip", "94566"))
        fields[29] = "USA"
        fields[30] = str(self.meet_info.get("Meet_hostlsc", "CC"))
        fields[33] = self._format_date(self.meet_info.get("Meet_start"))

        return ";".join(fields) + "*>"

    def _generate_ev3_event_record(self, event: dict[str, Any], sess_order: int) -> str:
        """Generates an EV3 event record."""
        fields = [""] * 30
        fields[0] = str(event.get("Event_no", "0"))
        fields[1] = str(event.get("Event_no", "0"))
        fields[2] = "F"  # Final
        fields[3] = str(event.get("Session", "1"))
        fields[4] = str(event.get("Ind_rel", "I"))
        fields[5] = str(event.get("Event_sex", "X"))
        fields[6] = str(event.get("Low_age", "0"))
        fields[7] = str(event.get("High_Age", "18"))
        fields[8] = str(event.get("Event_dist", "0"))
        fields[9] = str(event.get("Event_stroke", "A"))
        fields[13] = "N"  # Not locked
        fields[21] = str(sess_order)
        fields[22] = "1"  # ???
        fields[23] = "08:00AM"  # Default start
        fields[24] = "Y"  # Yards
        fields[28] = "0"

        return ";".join(fields) + "*>"

    def _generate_hyv_header(self) -> str:
        """Generates the HYV meet header record."""
        fields = [""] * 12
        fields[0] = str(self.meet_info.get("Meet_name1", ""))
        fields[1] = self._format_date(self.meet_info.get("Meet_start"))
        fields[2] = self._format_date(self.meet_info.get("Meet_end"))
        fields[3] = self._format_date(self.meet_info.get("Calc_date"))
        fields[4] = "Y"  # Yards
        fields[5] = str(self.meet_info.get("Meet_location", ""))
        fields[7] = "Hy-Tek Sports Software"
        fields[8] = "8.0Gb"
        fields[9] = "CN"

        return ";".join(fields)

    def _generate_hyv_event_record(self, event: dict[str, Any]) -> str:
        """Generates an HYV event record."""
        fields = [""] * 18
        fields[0] = str(event.get("Event_no", "0"))
        fields[1] = "F"  # Rnd
        fields[2] = str(event.get("Event_sex", "X"))
        if fields[2] == "G":
            fields[2] = "F"  # Girls -> Female in HYV?
        if fields[2] == "B":
            fields[2] = "M"  # Boys -> Male in HYV?

        fields[3] = str(event.get("Ind_rel", "I"))
        fields[4] = str(event.get("Low_age", "0"))
        fields[5] = str(event.get("High_Age", "18"))
        fields[6] = str(event.get("Event_dist", "0"))
        fields[7] = self.STROKE_MAP.get(str(event.get("Event_stroke", "A")), "1")

        return ";".join(fields)

    def write_to_zip(self, output_zip_path: str):
        """Generates the EV3 and HYV files and packages them into a ZIP."""
        ev3_content = [self._generate_ev3_header()]
        hyv_content = [self._generate_hyv_header()]

        # Group events by session for order
        events_by_session = {}
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
            zipf.writestr(ev3_filename, "\n".join(ev3_content) + "\n")
            zipf.writestr(hyv_filename, "\n".join(hyv_content) + "\n")

        logger.info(f"Generated meet events ZIP: {output_zip_path}")
        return output_zip_path
