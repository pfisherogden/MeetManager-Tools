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
                    "event_ptr": [1],
                    "team_no": [10],
                    "team_ltr": ["A"],
                    "pre_heat": [1],
                    "pre_lane": [4],
                    "pre_time": [0.0],
                    "fin_heat": [1],
                    "fin_lane": [4],
                    "fin_time": [0.0],
                    "convseed_time": [120.5],
                    "ind_rel": ["R"],
                }
            ),
            "RelayNames": pd.DataFrame(
                {
                    "event_ptr": [1, 1],
                    "team_no": [10, 10],
                    "team_ltr": ["A", "A"],
                    "event_round": ["F", "F"],  # Assuming Final round for simplicity or mocked logic
                    "ath_no": [101, 102],
                    "pos_no": [1, 2],  # Added pos_no for sorting if needed
                }
            ),
            "Athlete": pd.DataFrame(
                [
                    {"ath_no": 101, "first_name": "John", "last_name": "Doe", "ath_age": 14, "team_no": 10},
                    {"ath_no": 102, "first_name": "Jane", "last_name": "Doe", "ath_age": 13, "team_no": 10},
                ]
            ),
            "Team": pd.DataFrame([{"team_no": 10, "team_abbr": "TST", "team_short": "Test Team"}]),
            "Event": pd.DataFrame(
                {
                    "event_no": [1],
                    "event_ptr": [1],
                    "ind_rel": ["R"],
                    "event_gender": ["M"],
                    "event_dist": [200],
                    "event_stroke": ["A"],  # Free
                    "low_age": [0],
                    "high_age": [109],
                    "num_prelanes": [6],
                    "num_finlanes": [6],
                    "event_rounds": [1],  # Final only
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
