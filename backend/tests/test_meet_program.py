import unittest

import pandas as pd

from mm_to_json.mm_to_json import Event, MmToJsonConverter


class TestMeetProgramData(unittest.TestCase):
    def setUp(self):
        # Mocking the MmToJsonConverter to avoid needing a real MDB file for this specific test
        self.converter = MmToJsonConverter(table_data={})
        self.converter.tables = {
            "Relay": pd.DataFrame(
                {
                    "Event_ptr": [1],
                    "Team_no": [10],
                    "Team_ltr": ["A"],
                    "Pre_heat": [1],
                    "Pre_lane": [4],
                    "Pre_Time": [0.0],
                    "Fin_heat": [1],
                    "Fin_lane": [4],
                    "Fin_Time": [0.0],
                    "ConvSeed_time": [120.5],
                    "Ind_rel": ["R"],
                }
            ),
            "RelayNames": pd.DataFrame(
                {
                    "Event_ptr": [1, 1],
                    "Team_no": [10, 10],
                    "Team_ltr": ["A", "A"],
                    "Event_round": ["F", "F"],  # Assuming Final round for simplicity or mocked logic
                    "Ath_no": [101, 102],
                }
            ),
            "Athlete": pd.DataFrame(
                [
                    {"Ath_no": 101, "First_name": "John", "Last_name": "Doe", "Ath_age": 14, "Team_no": 10},
                    {"Ath_no": 102, "First_name": "Jane", "Last_name": "Doe", "Ath_age": 13, "Team_no": 10},
                ]
            ),
            "Team": pd.DataFrame([{"Team_no": 10, "Team_abbr": "TST", "Team_short": "Test Team"}]),
            "Event": pd.DataFrame(
                {
                    "Event_no": [1],
                    "Event_ptr": [1],
                    "Ind_rel": ["R"],
                    "Event_gender": ["M"],
                    "Event_dist": [200],
                    "Event_stroke": ["A"],  # Free
                    "Low_age": [0],
                    "High_age": [109],
                    "Num_prelanes": [6],
                    "Num_finlanes": [6],
                    "Event_rounds": [1],  # Final only
                }
            ),
        }
        self.converter.schema_type = "A"

    def test_relay_swimmers_extraction(self):
        # Mock dependencies
        event = Event(
            event_no=1,
            is_relay=True,
            gender="M",
            gender_desc="Boys",
            min_age=0,
            max_age=109,
            distance=200,
            stroke="Freestyle",
            division="",
            round_ltr="F",
            event_ptr=1,
            num_lanes=6,
        )

        # We need to ensure get_relay_athletes works with our mocked tables
        # The logic in MmToJsonConverter uses self.tables["RelayNames"]

        # Call add_relay_entries
        self.converter.add_relay_entries(event)

        # Verify
        self.assertEqual(len(event.entries), 1)
        entry = event.entries[0]
        self.assertEqual(entry["team"], "Test Team")
        self.assertEqual(entry["relayLtr"], "A")

        # Check relaySwimmers
        self.assertIn("relaySwimmers", entry)
        swimmers = entry["relaySwimmers"]
        self.assertEqual(len(swimmers), 2)
        self.assertEqual(swimmers[0], "J. Doe")
        self.assertEqual(swimmers[1], "J. Doe")


if __name__ == "__main__":
    unittest.main()
