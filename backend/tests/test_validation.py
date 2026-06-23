import os
import sys
from unittest.mock import patch

import pytest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    try:
        from meetmanager.v1 import meet_manager_pb2 as pb2
    except ImportError:
        import meet_manager_pb2 as pb2

    from server import MeetManagerService
except ImportError:
    pytest.skip("Skipping because protos not generated", allow_module_level=True)


def test_validate_meet_logic():
    """Test that ValidateMeet catches rule limits, gender/age mismatches, and empty teams/events."""
    service = MeetManagerService()

    # Mock tables
    service._data_cache = {
        "athlete": [
            {
                "ath_no": 1,
                "first_name": "Parker",
                "last_name": "Dreisbach",
                "ath_age": 10,
                "ath_sex": "M",
                "team_no": 100,
            },
            {
                "ath_no": 2,
                "first_name": "Invalid",
                "last_name": "Swimmer",
                "ath_age": 15,
                "ath_sex": "X",  # Invalid Gender
                "team_no": 999,  # Missing Team Link
            },
        ],
        "team": [
            {"team_no": 100, "team_name": "Del Prado", "team_lsc": ""},  # Missing LSC Code
        ],
        "event": [
            {
                "event_ptr": 10,
                "event_no": 1,
                "event_sex": "F",  # Women only event
                "low_age": 15,
                "high_age": 18,
                "event_relay": 0,
            },
            {
                "event_ptr": 20,
                "event_no": 2,
                "event_sex": "M",
                "low_age": 0,
                "high_age": 0,
                "event_relay": 0,
            },
            {
                "event_ptr": 30,
                "event_no": 3,
                "event_sex": "M",
                "low_age": 0,
                "high_age": 0,
                "event_relay": 0,
            },
            {
                "event_ptr": 40,
                "event_no": 4,
                "event_sex": "M",
                "low_age": 0,
                "high_age": 0,
                "event_relay": 0,
            },
            {
                "event_ptr": 50,
                "event_no": 5,
                "event_sex": "M",
                "low_age": 0,
                "high_age": 0,
                "event_relay": 0,
            },
        ],
        "entry": [
            {
                "ath_no": 1,
                "event_ptr": 10,
            },  # Parker (10, Male) swimming in Event 1 (15-18, Female) (Violations: Gender & Age)
            {"ath_no": 1, "event_ptr": 20},
            {"ath_no": 1, "event_ptr": 30},
            {"ath_no": 1, "event_ptr": 40},
            {"ath_no": 1, "event_ptr": 50},  # Parker entered in 5 events (Rules limits)
        ],
    }

    # Patch _load_user_data to return our manual cache/config
    def mock_load_user_data(context):
        return service._data_cache, {}

    with patch.object(service, "_load_user_data", side_effect=mock_load_user_data):
        response = service.ValidateMeet(None, None)
        assert response.success

        findings = response.findings
        # We expect:
        # 1. Del Prado missing LSC code (WARNING)
        # 2. Swimmer 2 has invalid gender 'X' (CRITICAL)
        # 3. Swimmer 2 is associated with a missing team 999 (CRITICAL)
        # 4. Parker (Male) entered in Female event (WARNING)
        # 5. Parker (age 10) entered in 15-18 event (WARNING)
        # 6. Parker exceeds TVSL entry limit with 5 entries (WARNING)
        # 7. Event 2 has 0 entries (WARNING/empty)

        severities = [f.severity for f in findings]
        categories = [f.category for f in findings]

        # Verify severities exist
        assert pb2.VALIDATION_SEVERITY_CRITICAL in severities
        assert pb2.VALIDATION_SEVERITY_WARNING in severities

        # Verify categories
        assert "Teams" in categories
        assert "Athletes" in categories
        assert "Entries" in categories
        assert "Rules Limit" in categories
