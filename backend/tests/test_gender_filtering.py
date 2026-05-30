
import unittest
from unittest.mock import MagicMock
from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

class TestGenderFiltering(unittest.TestCase):
    def setUp(self):
        # Mock the converter to return a fixed hydrated data structure
        self.mock_full_data = {
            "meetName": "Test Meet",
            "sessions": [
                {
                    "session_num": 1,
                    "name": "All",
                    "events": [
                        {
                            "eventNum": 1,
                            "event_ptr": 1,
                            "gender": "F",
                            "eventDesc": "Girls 50 Free",
                            "isRelay": False,
                            "entries": [{"name": "Jane", "ath_no": 1, "team": "DP", "athleteSex": "F"}]
                        },
                        {
                            "eventNum": 2,
                            "event_ptr": 2,
                            "gender": "M",
                            "eventDesc": "Boys 50 Free",
                            "isRelay": False,
                            "entries": [{"name": "John", "ath_no": 2, "team": "DP", "athleteSex": "M"}]
                        },
                        {
                            "eventNum": 3,
                            "event_ptr": 3,
                            "gender": "X",
                            "eventDesc": "Mixed Relay",
                            "isRelay": True,
                            "entries": [{"name": "Mixed Team", "relayLtr": "A", "team": "DP"}]
                        }
                    ]
                }
            ]
        }
        self.converter = MagicMock(spec=MmToJsonConverter)
        # extractor calls self.converter.convert()
        self.converter.convert.return_value = self.mock_full_data
        
        self.extractor = ReportDataExtractor(self.converter)

    def test_girls_filter_strict(self):
        # Girls filter should ONLY show event 1
        data = self.extractor.extract_meet_program_data(gender_filter="Girls")
        event_nums = [g["header"].split()[1] for g in data["groups"]]
        self.assertEqual(event_nums, ["1"])

    def test_boys_filter_includes_mixed(self):
        # Boys filter should show event 2 AND event 3 (Mixed)
        data = self.extractor.extract_meet_program_data(gender_filter="Boys")
        event_nums = [g["header"].split()[1] for g in data["groups"]]
        self.assertEqual(event_nums, ["2", "3"])

    def test_mixed_filter_all(self):
        # Mixed/None filter should show everything
        data = self.extractor.extract_meet_program_data(gender_filter="Mixed")
        event_nums = [g["header"].split()[1] for g in data["groups"]]
        self.assertEqual(event_nums, ["1", "2", "3"])

if __name__ == "__main__":
    unittest.main()
