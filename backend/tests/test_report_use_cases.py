import unittest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


class TestReportUseCases(unittest.TestCase):
    def setUp(self):
        # 1. Multi-team, Multi-event data (Individual + Relay)
        self.table_data = {
            "Meet": [
                {
                    "Meet_name1": "Mock Meet",
                    "Meet_location": "Mock Pool",
                    "Meet_start": "2026-02-14",
                    "Meet_end": "2026-02-14",
                    "Meet_class": 1,
                    "Meet_numlanes": 6,
                }
            ],
            "Session": [{"Sess_ptr": 1, "Sess_no": 1, "Sess_name": "S1", "Sess_day": 1, "Sess_starttime": 32400}],
            "Sessitem": [
                {"Sess_ptr": 1, "Event_ptr": 1, "Sess_order": 1, "Sess_rnd": "F"},  # 6&U
                {"Sess_ptr": 1, "Event_ptr": 2, "Sess_order": 2, "Sess_rnd": "F"},  # 15-18 (testing 15-16 map)
                {"Sess_ptr": 1, "Event_ptr": 3, "Sess_order": 3, "Sess_rnd": "F"},  # Relay
            ],
            "Event": [
                {
                    "Event_no": 1,
                    "Event_ptr": 1,
                    "Ind_rel": "I",
                    "Event_gender": "F",
                    "Event_sex": "Girls",
                    "Event_dist": 25,
                    "Event_stroke": "A",
                    "Low_age": 0,
                    "High_age": 0,
                    "Num_finlanes": 6,
                    "Event_rounds": 1,
                },
                {
                    "Event_no": 2,
                    "Event_ptr": 2,
                    "Ind_rel": "I",
                    "Event_gender": "M",
                    "Event_sex": "Boys",
                    "Event_dist": 50,
                    "Event_stroke": "A",
                    "Low_age": 15,
                    "High_age": 16,
                    "Num_finlanes": 6,
                    "Event_rounds": 1,
                },
                {
                    "Event_no": 3,
                    "Event_ptr": 3,
                    "Ind_rel": "R",
                    "Event_gender": "F",
                    "Event_sex": "Girls",
                    "Event_dist": 100,
                    "Event_stroke": "R",
                    "Low_age": 7,
                    "High_age": 8,
                    "Num_finlanes": 6,
                    "Event_rounds": 1,
                },
            ],
            "Athlete": [
                {"Ath_no": 1, "First_name": "Alice", "Last_name": "Athlete", "Ath_age": 6, "Team_no": 1, "Sex": "F"},
                {"Ath_no": 2, "First_name": "Bob", "Last_name": "Swimmer", "Ath_age": 17, "Team_no": 2, "Sex": "M"},
            ],
            "Team": [
                {"Team_no": 1, "Team_abbr": "TEAM1", "Team_name": "Team One", "Team_short": "Team One"},
                {"Team_no": 2, "Team_abbr": "TEAM2", "Team_name": "Team Two", "Team_short": "Team Two"},
            ],
            "Entry": [
                {
                    "Event_ptr": 1,
                    "Ath_no": 1,
                    "Fin_heat": 1,
                    "Fin_lane": 1,
                    "ConvSeed_time": 20.5,
                    "Fin_Time": 0.0,
                    "Fin_Stat": "",
                },
                {
                    "Event_ptr": 2,
                    "Ath_no": 2,
                    "Fin_heat": 1,
                    "Fin_lane": 1,
                    "ConvSeed_time": 40.0,
                    "Fin_Time": 0.0,
                    "Fin_Stat": "",
                },
            ],
            "Relay": [
                {
                    "Event_ptr": 3,
                    "Team_no": 1,
                    "Team_ltr": "A",
                    "ConvSeed_time": 80.5,
                    "Fin_heat": 1,
                    "Fin_lane": 1,
                    "Fin_Time": 0.0,
                    "Fin_Stat": "",
                }
            ],
            "RelayNames": [{"Event_ptr": 3, "Team_no": 1, "Team_ltr": "A", "Ath_no": 1, "Pos": 1, "Event_round": "F"}],
            "Relay_Athletes": [],  # Ignored if RelayNames is present
            "Divisions": [],
        }
        self.converter = MmToJsonConverter(table_data=self.table_data)
        self.extractor = ReportDataExtractor(self.converter)

    def test_parents_lineup_logic(self):
        """Verify Parents Line-Up: Per-team, gender and age filtered."""
        # Check 6 & under fix (from 0-0)
        data = self.extractor.extract_timer_sheets_data(
            team_filter="Team One", gender_filter="Girls", age_group_filter="6 & under"
        )
        self.assertEqual(len(data["groups"]), 1)
        self.assertIn("6 & under", data["groups"][0]["header"])

    def test_coaches_program_logic(self):
        """Verify Coaches Program: All teams, all events, includes relays."""
        data = self.extractor.extract_meet_program_data(
            report_title="Coaches Program", columns_on_page=2, show_relay_swimmers=True
        )
        # Check 15-18 fix (from 15-16)
        evt2 = next(g for g in data["groups"] if "Event 2" in g["header"])
        self.assertIn("15-18", evt2["header"])

        # Verify relay inclusion
        relay_event = next(g for g in data["groups"] if "Event 3" in g["header"])
        relay_entry = relay_event["heats"][0]["sub_items"][0]
        self.assertTrue(relay_entry["is_relay"])
        self.assertIn("Athlete, Alice", relay_entry["swimmers"][0])


if __name__ == "__main__":
    unittest.main()
