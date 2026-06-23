import os
import sys

import pytest

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

try:
    try:
        from meetmanager.v1 import meet_manager_pb2 as pb2
    except ImportError:
        import meet_manager_pb2 as pb2

    from meet_validation import validate_meet_data
except ImportError:
    pytest.skip("Skipping because protos not generated", allow_module_level=True)


def test_validate_meet_logic():
    """Test that validate_meet_data catches rule limits, gender/age mismatches, and empty teams/events."""
    cache = {
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

    findings = validate_meet_data(cache)

    # We expect:
    # 1. Del Prado missing LSC code (WARNING)
    # 2. Swimmer 2 has invalid gender 'X' (CRITICAL)
    # 3. Swimmer 2 is associated with a missing team 999 (CRITICAL)
    # 4. Parker (Male) entered in Female event (WARNING)
    # 5. Parker (age 10) entered in 15-18 event (WARNING)
    # 6. Parker exceeds TVSL entry limit with 5 entries (WARNING)
    # 7. Event 2 has 1 entry (under-populated INFO)

    severities = [f.severity for f in findings]
    categories = [f.category for f in findings]

    assert pb2.VALIDATION_SEVERITY_CRITICAL in severities
    assert pb2.VALIDATION_SEVERITY_WARNING in severities

    assert "Teams" in categories
    assert "Athletes" in categories
    assert "Entries" in categories
    assert "Rules Limit" in categories


def test_new_validation_rules():
    """Test that ValidateMeet catches DQ points, backup timer count warnings, scratched times, duplicates, and wild times."""
    cache = {
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

    findings = validate_meet_data(cache)
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


def test_exhibition_swims_limits():
    """Test that exhibition swims are not counted against the athlete entries limits."""
    cache = {
        "athlete": [
            {
                "ath_no": 1,
                "first_name": "Parker",
                "last_name": "Dreisbach",
                "ath_age": 10,
                "ath_sex": "M",
                "team_no": 100,
            },
        ],
        "team": [
            {"team_no": 100, "team_name": "Del Prado", "team_lsc": "DP"},
        ],
        "event": [
            {"event_ptr": 10, "event_no": 1, "event_sex": "M", "low_age": 0, "high_age": 0, "event_relay": 0},
            {"event_ptr": 20, "event_no": 2, "event_sex": "M", "low_age": 0, "high_age": 0, "event_relay": 0},
            {"event_ptr": 30, "event_no": 3, "event_sex": "M", "low_age": 0, "high_age": 0, "event_relay": 0},
            {"event_ptr": 40, "event_no": 4, "event_sex": "M", "low_age": 0, "high_age": 0, "event_relay": 0},
            {"event_ptr": 50, "event_no": 5, "event_sex": "M", "low_age": 0, "high_age": 0, "event_relay": 0},
        ],
        "entry": [
            # 5 entries total, but 3 are exhibition (marked in pre_exh or fin_exh)
            {"ath_no": 1, "event_ptr": 10, "pre_exh": "x"},
            {"ath_no": 1, "event_ptr": 20, "fin_exh": "E"},
            {"ath_no": 1, "event_ptr": 30},
            {"ath_no": 1, "event_ptr": 40},
            {"ath_no": 1, "event_ptr": 50, "pre_exh": "X"},
        ],
    }

    findings = validate_meet_data(cache)
    categories = [f.category for f in findings]

    # Parker only has 2 non-exhibition swims (Events 30 and 40), so he should not exceed limit warnings
    assert "Rules Limit" not in categories


def test_relay_event_count_no_warning():
    """Test that a relay event with entries does not trigger the 0 entries warning."""
    cache = {
        "athlete": [],
        "team": [],
        "event": [
            # Relay event
            {
                "event_ptr": 10,
                "event_no": 1,
                "event_sex": "M",
                "low_age": 0,
                "high_age": 0,
                "event_relay": 1,
            },
        ],
        "entry": [],
        "relay": [
            # Relay entry in event 10
            {
                "event_ptr": 10,
                "team_no": 100,
                "relay_no": 1,
            }
        ],
    }

    findings = validate_meet_data(cache)
    # The relay event has 1 entry, so it should trigger the underpopulated (INFO) warning instead of 0 entries (WARNING)
    warning_findings = [f for f in findings if f.category == "Events" and f.severity == pb2.VALIDATION_SEVERITY_WARNING]
    info_findings = [f for f in findings if f.category == "Events" and f.severity == pb2.VALIDATION_SEVERITY_INFO]

    assert len(warning_findings) == 0
    assert len(info_findings) == 1
    assert "under-populated" in info_findings[0].message
