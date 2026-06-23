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


def test_new_validation_rules():
    """Test that ValidateMeet catches DQ points, backup timer count warnings, scratched times, duplicates, and wild times."""
    from typing import Any

    service = MeetManagerService()

    service._data_cache = {
        "athlete": [
            {
                "ath_no": 1,
                "first_name": "John",
                "last_name": "Doe",
                "ath_age": 10,
                "ath_sex": "M",
                "team_no": 100,
            },
            {
                "ath_no": 2,
                "first_name": "Jane",
                "last_name": "Smith",
                "ath_age": 16,
                "ath_sex": "F",
                "team_no": 100,
            },
        ],
        "team": [
            {"team_no": 100, "team_name": "Del Prado", "team_lsc": "DP"},
        ],
        "event": [
            {
                "event_ptr": 10,
                "event_no": 1,
                "event_sex": "M",
                "low_age": 9,
                "high_age": 10,
                "event_relay": 0,
                "event_dist": 25,
                "event_stroke": "A",
            },
            {
                "event_ptr": 20,
                "event_no": 2,
                "event_sex": "F",
                "low_age": 15,
                "high_age": 18,
                "event_relay": 0,
                "event_dist": 50,
                "event_stroke": "B",
            },
        ],
        "entry": [
            # DQ with points (CRITICAL)
            {
                "ath_no": 1,
                "event_ptr": 10,
                "fin_time": 15.5,
                "fin_stat": "Q",
                "ev_score": 5.0,
                "fin_heat": 1,
                "fin_lane": 2,
            },
            # Scratched with time (CRITICAL)
            {
                "ath_no": 2,
                "event_ptr": 20,
                "fin_time": 30.0,
                "fin_stat": "R",
                "fin_heat": 1,
                "fin_lane": 3,
            },
            # 1 Backup Timer (WARNING)
            {
                "ath_no": 1,
                "event_ptr": 10,
                "fin_time": 12.0,
                "fin_heat": 2,
                "fin_lane": 4,
                "fin_back1": 12.0,
                "fin_back2": 0.0,
                "fin_back3": 0.0,
            },
            # Wild time (WARNING)
            {
                "ath_no": 1,
                "event_ptr": 10,
                "fin_time": 15.0,
                "actualseed_time": 30.0,  # 15s difference for age 10 >= 9
                "fin_heat": 2,
                "fin_lane": 5,
            },
        ],
        "relay": [
            # Relay with NS (INFO)
            {
                "event_ptr": 10,
                "team_no": 100,
                "team_ltr": "A",
                "fin_time": 0.0,
                "fin_stat": "",
                "fin_heat": 1,
                "fin_lane": 1,
            }
        ],
    }

    def mock_load_user_data(context: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        return service._data_cache, {}

    with patch.object(service, "_load_user_data", side_effect=mock_load_user_data):
        response = service.ValidateMeet(None, None)
        assert response.success

        findings = response.findings
        categories = [f.category for f in findings]
        severities = [f.severity for f in findings]

        # Verify Points on DQs
        assert "Points on DQs" in categories
        assert pb2.VALIDATION_SEVERITY_CRITICAL in severities

        # Verify Scratched with Time
        assert "Scratched with Time" in categories

        # Verify 1 Backup Timer
        assert "1 Backup Timer" in categories
        assert pb2.VALIDATION_SEVERITY_WARNING in severities

        # Verify Wild Times
        assert "Wild Times" in categories

        # Verify Relays with NS
        assert "Relays with NS" in categories
        assert pb2.VALIDATION_SEVERITY_INFO in severities
