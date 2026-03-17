import unittest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor


class TestReportUseCases(unittest.TestCase):
    def setUp(self):
        # 1. Multi-team, Multi-event data (Individual + Relay)
        self.table_data = {
            "meet": [
                {
                    "meet_name1": "Mock Meet",
                    "meet_location": "Mock Pool",
                    "meet_start": "2026-02-14",
                    "meet_end": "2026-02-14",
                    "meet_class": 1,
                    "meet_numlanes": 6,
                }
            ],
            "session": [{"sess_ptr": 1, "sess_no": 1, "sess_name": "S1", "sess_day": 1, "sess_starttime": 32400}],
            "sessitem": [
                {"sess_ptr": 1, "event_ptr": 1, "sess_order": 1, "sess_rnd": "F"},  # 6&U
                {"sess_ptr": 1, "event_ptr": 2, "sess_order": 2, "sess_rnd": "F"},  # 15-18 (testing 15-16 map)
                {"sess_ptr": 1, "event_ptr": 3, "sess_order": 3, "sess_rnd": "F"},  # Relay
            ],
            "event": [
                {
                    "event_no": 1,
                    "event_ptr": 1,
                    "ind_rel": "I",
                    "event_gender": "F",
                    "event_sex": "Girls",
                    "event_dist": 25,
                    "event_stroke": "A",
                    "low_age": 0,
                    "high_age": 0,
                    "num_finlanes": 6,
                    "event_rounds": 1,
                },
                {
                    "event_no": 2,
                    "event_ptr": 2,
                    "ind_rel": "I",
                    "event_gender": "M",
                    "event_sex": "Boys",
                    "event_dist": 50,
                    "event_stroke": "A",
                    "low_age": 15,
                    "high_age": 16,
                    "num_finlanes": 6,
                    "event_rounds": 1,
                },
                {
                    "event_no": 3,
                    "event_ptr": 3,
                    "ind_rel": "R",
                    "event_gender": "F",
                    "event_sex": "Girls",
                    "event_dist": 100,
                    "event_stroke": "R",
                    "low_age": 7,
                    "high_age": 8,
                    "num_finlanes": 6,
                    "event_rounds": 1,
                },
            ],
            "athlete": [
                {"ath_no": 1, "first_name": "Alice", "last_name": "Athlete", "ath_age": 6, "team_no": 1, "sex": "F"},
                {"ath_no": 2, "first_name": "Bob", "last_name": "Swimmer", "ath_age": 17, "team_no": 2, "sex": "M"},
            ],
            "team": [
                {"team_no": 1, "team_abbr": "TEAM1", "team_name": "Team One", "team_short": "Team One"},
                {"team_no": 2, "team_abbr": "TEAM2", "team_name": "Team Two", "team_short": "Team Two"},
            ],
            "entry": [
                {
                    "event_ptr": 1,
                    "ath_no": 1,
                    "fin_heat": 1,
                    "fin_lane": 1,
                    "convseed_time": 20.5,
                    "fin_time": 0.0,
                    "fin_stat": "",
                },
                {
                    "event_ptr": 2,
                    "ath_no": 2,
                    "fin_heat": 1,
                    "fin_lane": 1,
                    "convseed_time": 40.0,
                    "fin_time": 0.0,
                    "fin_stat": "",
                },
            ],
            "relay": [
                {
                    "event_ptr": 3,
                    "team_no": 1,
                    "team_ltr": "A",
                    "convseed_time": 80.5,
                    "fin_heat": 1,
                    "fin_lane": 1,
                    "fin_time": 0.0,
                    "fin_stat": "",
                }
            ],
            "relaynames": [{"event_ptr": 3, "team_no": 1, "team_ltr": "A", "ath_no": 1, "pos": 1, "event_round": "F"}],
            "relay_athletes": [],  # Ignored if RelayNames is present
            "divisions": [],
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
