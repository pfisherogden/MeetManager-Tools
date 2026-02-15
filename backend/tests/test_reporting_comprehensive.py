import unittest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


class TestReportingComprehensive(unittest.TestCase):
    def setUp(self):
        # Mocking the MmToJsonConverter with minimal data for all tables
        self.table_data = {
            "meet": [
                {
                    "meet_name1": "Test Meet",
                    "meet_location": "Test Pool",
                    "meet_start": "2026-02-13",
                    "meet_end": "2026-02-13",
                }
            ],
            "session": [
                {"sess_ptr": 1, "sess_no": 1, "sess_name": "Session 1", "sess_day": 1, "sess_starttime": 32400}
            ],
            "sessitem": [{"sess_ptr": 1, "event_ptr": 1, "sess_order": 1, "sess_rnd": "F"}],
            "event": [
                {
                    "event_no": 1,
                    "event_ptr": 1,
                    "ind_rel": "I",
                    "event_gender": "M",
                    "event_sex": "Boys",
                    "event_dist": 50,
                    "event_stroke": "A",
                    "low_age": 11,
                    "high_age": 12,
                    "num_finlanes": 6,
                    "event_rounds": 1,
                }
            ],
            "athlete": [
                {"ath_no": 1, "first_name": "Alice", "last_name": "Athlete", "ath_age": 11, "team_no": 1, "sex": "F"},
                {"ath_no": 2, "first_name": "Bob", "last_name": "Swimmer", "ath_age": 12, "team_no": 1, "sex": "M"},
            ],
            "team": [{"team_no": 1, "team_abbr": "TST", "team_name": "Test Team"}],
            "entry": [
                {
                    "event_ptr": 1,
                    "ath_no": 1,
                    "fin_heat": 1,
                    "fin_lane": 1,
                    "convseed_time": 30.5,
                    "fin_time": 29.5,
                    "fin_stat": "",
                    "fin_place": 1,
                },
                {
                    "event_ptr": 1,
                    "ath_no": 2,
                    "fin_heat": 1,
                    "fin_lane": 2,
                    "convseed_time": 32.0,
                    "fin_time": 31.0,
                    "fin_stat": "",
                    "fin_place": 2,
                },
            ],
            "relay": [],
            "relaynames": [],
            "divisions": [],
        }
        self.converter = MmToJsonConverter(table_data=self.table_data)
        self.extractor = ReportDataExtractor(self.converter)

    def test_extract_psych_sheet_data(self):
        data = self.extractor.extract_psych_sheet_data()
        self.assertEqual(data["meet_name"], "Test Meet")
        self.assertEqual(len(data["groups"]), 1)
        group = data["groups"][0]
        self.assertIn("Event 1", group["header"])
        entries = group["sections"][0]["sub_items"]
        self.assertEqual(len(entries), 2)
        # Sorted by seed time: 30.5 should be first
        self.assertEqual(entries[0]["time"], "30.50")
        self.assertEqual(entries[1]["time"], "32.00")

    def test_extract_timer_sheets_data(self):
        data = self.extractor.extract_timer_sheets_data()
        self.assertEqual(len(data["groups"]), 1)
        group = data["groups"][0]
        # Timer sheets structure: group -> heats -> list of heat objects with header
        self.assertTrue(len(group["heats"]) > 0)
        heat = group["heats"][0]
        self.assertIn("Heat 1", heat["header"])
        entries = heat["sub_items"]
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["lane"], "1")
        self.assertEqual(entries[1]["lane"], "2")

    def test_extract_results_data(self):
        data = self.extractor.extract_results_data()
        self.assertEqual(len(data["groups"]), 1)
        group = data["groups"][0]
        entries = group["sections"][0]["sub_items"]
        self.assertEqual(len(entries), 2)
        # Sorted by results time: 29.50 should be first
        self.assertEqual(entries[0]["time"], "29.50")
        self.assertEqual(entries[0]["place"], "1")
        self.assertEqual(entries[1]["time"], "31.00")
        self.assertEqual(entries[1]["place"], "2")


if __name__ == "__main__":
    unittest.main()
