import unittest
from unittest.mock import patch
import os
import sys
import pandas as pd

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(os.path.join(os.getcwd(), "MeetManager-Tools/backend/src"))
sys.path.append(parent_dir)

from extract_attendance_data import extract_attendance_data  # noqa: E402


class TestAttendanceExtraction(unittest.TestCase):
    @patch("extract_attendance_data.MmToJsonConverter")
    def test_relay_detection(self, MockConverter):
        # Mock MDB data
        mock_data = {
            "sessions": [
                {
                    "events": [
                        {
                            "eventDesc": "Girls 7-8 100 Yard Medley Relay",
                            "isRelay": True,
                            "entries": [
                                {
                                    "teamCode": "DP",
                                    "relayAthletes": [
                                        {
                                            "athleteId": 101,
                                            "firstName": "Alice",
                                            "lastName": "Smith",
                                        },
                                        {
                                            "athleteId": 102,
                                            "firstName": "Bob",
                                            "lastName": "Jones",
                                        },
                                    ],
                                }
                            ],
                        },
                        {
                            "eventDesc": "Boys 9-10 50 Yard Freestyle",
                            "isRelay": False,
                            "entries": [
                                {
                                    "teamCode": "DP",
                                    "athleteId": 103,
                                    "firstName": "Charlie",
                                    "lastName": "Brown",
                                }
                            ],
                        },
                    ]
                }
            ]
        }

        mock_instance = MockConverter.return_value
        mock_instance.convert.return_value = mock_data

        # Real DataFrames for athletes and teams
        athlete_data = [
            {
                "ath_no": 101,
                "last_name": "Smith",
                "first_name": "Alice",
                "ath_sex": "F",
                "ath_age": 8,
                "team_no": 26,
            },
            {
                "ath_no": 102,
                "last_name": "Jones",
                "first_name": "Bob",
                "ath_sex": "M",
                "ath_age": 8,
                "team_no": 26,
            },
            {
                "ath_no": 103,
                "last_name": "Brown",
                "first_name": "Charlie",
                "ath_sex": "M",
                "ath_age": 9,
                "team_no": 26,
            },
        ]
        athlete_df = pd.DataFrame(athlete_data)

        team_data = [{"team_abbr": "DP", "team_no": 26}]
        team_df = pd.DataFrame(team_data)

        mock_instance.tables = {"athlete": athlete_df, "team": team_df}

        # Run extraction
        results = extract_attendance_data("dummy.mdb", target_team_code="DP")

        # Verify
        athlete_map = {a["ID"]: a for a in results}

        self.assertEqual(athlete_map[101]["Medley Relay"], "X")
        self.assertEqual(athlete_map[102]["Medley Relay"], "X")
        self.assertEqual(athlete_map[103]["Free"], "X")
        self.assertEqual(athlete_map[103]["Medley Relay"], "")


if __name__ == "__main__":
    unittest.main()
