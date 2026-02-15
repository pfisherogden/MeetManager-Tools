import unittest
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

class TestReportUseCases(unittest.TestCase):
    def setUp(self):
        # 1. Multi-team, Multi-event data (Individual + Relay)
        self.table_data = {
            "Meet": [{"Meet_name1": "Mock Meet", "Meet_location": "Mock Pool", "Meet_start": "2026-02-14", "Meet_end": "2026-02-14", "Meet_class": 1, "Meet_numlanes": 6}],
            "Session": [{"Sess_ptr": 1, "Sess_no": 1, "Sess_name": "S1", "Sess_day": 1, "Sess_starttime": 32400}],
            "Sessitem": [
                {"Sess_ptr": 1, "Event_ptr": 1, "Sess_order": 1, "Sess_rnd": "F"}, # Individual Girls 8&U
                {"Sess_ptr": 1, "Event_ptr": 2, "Sess_order": 2, "Sess_rnd": "F"}, # Individual Boys 10&U
                {"Sess_ptr": 1, "Event_ptr": 3, "Sess_order": 3, "Sess_rnd": "F"}, # Relay Girls 8&U
            ],
            "Event": [
                {
                    "Event_no": 1, "Event_ptr": 1, "Ind_rel": "I", "Event_gender": "F", "Event_sex": "Girls",
                    "Event_dist": 25, "Event_stroke": "A", "Low_age": 7, "High_age": 8, "Num_finlanes": 6, "Event_rounds": 1
                },
                {
                    "Event_no": 2, "Event_ptr": 2, "Ind_rel": "I", "Event_gender": "M", "Event_sex": "Boys",
                    "Event_dist": 50, "Event_stroke": "A", "Low_age": 9, "High_age": 10, "Num_finlanes": 6, "Event_rounds": 1
                },
                {
                    "Event_no": 3, "Event_ptr": 3, "Ind_rel": "R", "Event_gender": "F", "Event_sex": "Girls",
                    "Event_dist": 100, "Event_stroke": "R", "Low_age": 7, "High_age": 8, "Num_finlanes": 6, "Event_rounds": 1
                }
            ],
            "Athlete": [
                {"Ath_no": 1, "First_name": "Alice", "Last_name": "Athlete", "Ath_age": 8, "Team_no": 1, "Sex": "F"},
                {"Ath_no": 2, "First_name": "Bob", "Last_name": "Swimmer", "Ath_age": 10, "Team_no": 2, "Sex": "M"},
            ],
            "Team": [
                {"Team_no": 1, "Team_abbr": "TEAM1", "Team_name": "Team One", "Team_short": "Team One"},
                {"Team_no": 2, "Team_abbr": "TEAM2", "Team_name": "Team Two", "Team_short": "Team Two"}
            ],
            "Entry": [
                {"Event_ptr": 1, "Ath_no": 1, "Fin_heat": 1, "Fin_lane": 1, "ConvSeed_time": 20.5, "Fin_Time": 0.0, "Fin_Stat": ""}, # Alice in Evt 1
                {"Event_ptr": 2, "Ath_no": 2, "Fin_heat": 1, "Fin_lane": 1, "ConvSeed_time": 40.0, "Fin_Time": 0.0, "Fin_Stat": ""}, # Bob in Evt 2
            ],
            "Relay": [
                {"Event_ptr": 3, "Team_no": 1, "Team_ltr": "A", "ConvSeed_time": 80.5, "Fin_heat": 1, "Fin_lane": 1, "Fin_Time": 0.0, "Fin_Stat": ""}
            ],
            "RelayNames": [
                {"Event_ptr": 3, "Team_no": 1, "Team_ltr": "A", "Ath_no": 1, "Pos": 1, "Event_round": "F"}
            ],
            "Divisions": [],
        }
        self.converter = MmToJsonConverter(table_data=self.table_data)
        self.extractor = ReportDataExtractor(self.converter)

    def test_parents_lineup_logic(self):
        """Verify Parents Line-Up: Per-team, gender and age filtered."""
        # Case A: Team One, Girls, 7-8
        data = self.extractor.extract_timer_sheets_data(
            team_filter="Team One", 
            gender_filter="Girls", 
            age_group_filter="7-8"
        )
        
        # Verify only Team One data is present
        for group in data["groups"]:
            for heat in group["heats"]:
                for entry in heat["sub_items"]:
                    self.assertEqual(entry["team"], "Team One")
                    
        # Verify Alice is present (Individual and Relay)
        self.assertEqual(len(data["groups"]), 2) # Evt 1 and Evt 3
        evt1 = data["groups"][0]
        self.assertIn("Event 1", evt1["header"])
        self.assertIn("Heat 1 of 1 Finals", evt1["heats"][0]["header"])
        
        # Case B: Team Two, Boys, 9-10
        data = self.extractor.extract_timer_sheets_data(
            team_filter="Team Two", 
            gender_filter="Boys", 
            age_group_filter="9-10"
        )
        self.assertEqual(len(data["groups"]), 1) # Only Evt 2
        self.assertIn("Swimmer, Bob", data["groups"][0]["heats"][0]["sub_items"][0]["name"])

    def test_coaches_program_logic(self):
        """Verify Coaches Program: All teams, all events, includes relays."""
        data = self.extractor.extract_meet_program_data(
            report_title="Coaches Program",
            columns_on_page=2,
            show_relay_swimmers=True
        )
        
        # Verify both teams are present
        all_teams = set()
        for group in data["groups"]:
            for heat in group["heats"]:
                for entry in heat["sub_items"]:
                    all_teams.add(entry["team"])
        
        self.assertIn("Team One", all_teams)
        self.assertIn("Team Two", all_teams)
        
        # Verify relay inclusion
        relay_event = next(g for g in data["groups"] if "Event 3" in g["header"])
        relay_entry = relay_event["heats"][0]["sub_items"][0]
        self.assertTrue(relay_entry["is_relay"])
        self.assertIn("Athlete, Alice", relay_entry["swimmers"][0])

    def test_board_posting_logic(self):
        """Verify Board Posting: Gender filtered, includes entry times."""
        # Girls only
        data = self.extractor.extract_meet_program_data(gender_filter="Girls")
        for group in data["groups"]:
            self.assertIn("Girls", group["header"])
            for heat in group["heats"]:
                for entry in heat["sub_items"]:
                    self.assertNotEqual(entry["time"], "") # Entry times present
                    
        # Boys (+Mixed implied if present)
        data = self.extractor.extract_meet_program_data(gender_filter="Boys")
        self.assertEqual(len(data["groups"]), 1)
        self.assertIn("Boys", data["groups"][0]["header"])

    def test_computer_team_logic(self):
        """Verify Computer Team: All events, 1-column layout flag."""
        data = self.extractor.extract_meet_program_data(
            report_title="Computer Program",
            columns_on_page=1
        )
        self.assertEqual(data["columns_on_page"], 1)
        self.assertEqual(len(data["groups"]), 3) # All 3 events

if __name__ == "__main__":
    unittest.main()
