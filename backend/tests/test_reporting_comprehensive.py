import unittest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


class TestReportingComprehensive(unittest.TestCase):
    def setUp(self):
        # Mocking the MmToJsonConverter with minimal data for all tables
        self.table_data = {
            "Meet": [
                {
                    "Meet_name1": "Test Meet",
                    "Meet_location": "Test Pool",
                    "Meet_start": "2026-02-13",
                    "Meet_end": "2026-02-13",
                }
            ],
            "Session": [
                {"Sess_ptr": 1, "Sess_no": 1, "Sess_name": "Session 1", "Sess_day": 1, "Sess_starttime": 32400}
            ],
            "Sessitem": [{"Sess_ptr": 1, "Event_ptr": 1, "Sess_order": 1, "Sess_rnd": "F"}],
            "Event": [
                {
                    "Event_no": 1,
                    "Event_ptr": 1,
                    "Ind_rel": "I",
                    "Event_gender": "M",
                    "Event_sex": "Boys",
                    "Event_dist": 50,
                    "Event_stroke": "A",
                    "Low_age": 11,
                    "High_age": 12,
                    "Num_finlanes": 6,
                    "Event_rounds": 1,
                }
            ],
            "Athlete": [
                {"Ath_no": 1, "First_name": "Alice", "Last_name": "Athlete", "Ath_age": 11, "Team_no": 1, "Sex": "F"},
                {"Ath_no": 2, "First_name": "Bob", "Last_name": "Swimmer", "Ath_age": 12, "Team_no": 1, "Sex": "M"},
            ],
            "Team": [{"Team_no": 1, "Team_abbr": "TST", "Team_name": "Test Team"}],
            "Entry": [
                {
                    "Event_ptr": 1,
                    "Ath_no": 1,
                    "Fin_heat": 1,
                    "Fin_lane": 1,
                    "ConvSeed_time": 30.5,
                    "Fin_Time": 29.5,
                    "Fin_Stat": "",
                    "Fin_place": 1,
                },
                {
                    "Event_ptr": 1,
                    "Ath_no": 2,
                    "Fin_heat": 1,
                    "Fin_lane": 2,
                    "ConvSeed_time": 32.0,
                    "Fin_Time": 31.0,
                    "Fin_Stat": "",
                    "Fin_place": 2,
                },
            ],
            "Relay": [],
            "RelayNames": [],
            "Divisions": [],
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
        self.assertIn("Heat 1", group["header"])
        entries = group["sections"][0]["sub_items"]
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
