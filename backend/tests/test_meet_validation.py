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


def test_no_event_entry_count_warnings():
    """Test that events with zero or few entries do not trigger any warnings or findings."""
    cache = {
        "athlete": [],
        "team": [],
        "event": [
            {
                "event_ptr": 10,
                "event_no": 1,
                "event_sex": "M",
                "low_age": 0,
                "high_age": 0,
                "event_relay": 0,
            },
        ],
        "entry": [],
        "relay": [],
    }

    findings = validate_meet_data(cache)
    event_findings = [f for f in findings if f.category == "Events"]
    assert len(event_findings) == 0


def test_unscored_backup_timers():
    """Test that unscored entries do not report 0 backup timers, but scored entries with no times do."""
    cache = {
        "athlete": [
            {"ath_no": 1, "first_name": "John", "last_name": "Doe", "ath_age": 10, "ath_sex": "M", "team_no": 100}
        ],
        "team": [{"team_no": 100, "team_name": "Del Prado", "team_lsc": "DP"}],
        "event": [{"event_ptr": 10, "event_no": 1, "event_sex": "M", "low_age": 9, "high_age": 10, "event_relay": 0}],
        "entry": [
            # 1. Unscored entry: time=0, place=0, status=empty -> NO warning
            {
                "ath_no": 1,
                "event_ptr": 10,
                "fin_time": 0.0,
                "fin_place": 0,
                "fin_stat": "",
                "fin_heat": 1,
                "fin_lane": 2,
            },
            # 2. Scored entry with NS: time=0, place=0, status="NS" -> WARNING/INFO
            {
                "ath_no": 1,
                "event_ptr": 10,
                "fin_time": 0.0,
                "fin_place": 0,
                "fin_stat": "NS",
                "fin_heat": 1,
                "fin_lane": 3,
            },
            # 3. Scored entry with place: time=0, place=3, status=empty -> WARNING/INFO
            {
                "ath_no": 1,
                "event_ptr": 10,
                "fin_time": 0.0,
                "fin_place": 3,
                "fin_stat": "",
                "fin_heat": 1,
                "fin_lane": 4,
            },
        ],
    }

    findings = validate_meet_data(cache)
    backup_findings = [f for f in findings if f.category == "0 Backup Timers"]

    # We expect exactly 2 findings: one for the entry with NS, and one for the entry with a place
    assert len(backup_findings) == 2


def test_rules_limits_with_relays():
    """Test that relay entries are correctly parsed using ind_rel='R' and subject to Rule 12 limits."""
    cache = {
        "athlete": [
            {"ath_no": 1, "first_name": "John", "last_name": "Doe", "ath_age": 10, "ath_sex": "M", "team_no": 100}
        ],
        "team": [{"team_no": 100, "team_name": "Del Prado", "team_lsc": "DP"}],
        "event": [
            # 3 individual events
            {"event_ptr": 10, "event_no": 1, "event_sex": "M", "low_age": 9, "high_age": 10, "ind_rel": "I"},
            {"event_ptr": 11, "event_no": 2, "event_sex": "M", "low_age": 9, "high_age": 10, "ind_rel": "I"},
            {"event_ptr": 12, "event_no": 3, "event_sex": "M", "low_age": 9, "high_age": 10, "ind_rel": "I"},
            # 3 relay events
            {"event_ptr": 20, "event_no": 101, "event_sex": "M", "low_age": 9, "high_age": 10, "ind_rel": "R"},
            {"event_ptr": 21, "event_no": 102, "event_sex": "M", "low_age": 9, "high_age": 10, "ind_rel": "R"},
            {"event_ptr": 22, "event_no": 103, "event_sex": "M", "low_age": 9, "high_age": 10, "ind_rel": "R"},
        ],
        "entry": [
            {"ath_no": 1, "event_ptr": 10},
            {"ath_no": 1, "event_ptr": 11},
            {"ath_no": 1, "event_ptr": 12},
        ],
        "relay": [
            {"event_ptr": 20, "relay_no": 1, "team_no": 100, "team_ltr": "A"},
            {"event_ptr": 21, "relay_no": 2, "team_no": 100, "team_ltr": "A"},
            {"event_ptr": 22, "relay_no": 3, "team_no": 100, "team_ltr": "A"},
        ],
        "relaynames": [
            {"event_ptr": 20, "team_no": 100, "team_ltr": "A", "ath_no": 1, "relay_no": 1, "event_round": "F"},
            {"event_ptr": 21, "team_no": 100, "team_ltr": "A", "ath_no": 1, "relay_no": 2, "event_round": "F"},
            {"event_ptr": 22, "team_no": 100, "team_ltr": "A", "ath_no": 1, "relay_no": 3, "event_round": "F"},
        ],
    }

    # Case 1: 3 individual events + 1 relay event (4 total) -> should be fine (no warnings)
    cache_case1 = cache.copy()
    cache_case1["relay"] = cache["relay"][:1]
    cache_case1["relaynames"] = cache["relaynames"][:1]
    findings1 = validate_meet_data(cache_case1)
    limit_findings1 = [f for f in findings1 if f.category == "Rules Limit"]
    assert len(limit_findings1) == 0

    # Case 2: 3 individual events + 2 relay events (5 total) -> exceeds total (max 4), but relays is ok (2)
    cache_case2 = cache.copy()
    cache_case2["relay"] = cache["relay"][:2]
    cache_case2["relaynames"] = cache["relaynames"][:2]
    findings2 = validate_meet_data(cache_case2)
    limit_findings2 = [f for f in findings2 if f.category == "Rules Limit"]
    assert len(limit_findings2) == 1
    assert "exceeds total entry limits" in limit_findings2[0].message

    # Case 3: 3 individual events + 3 relay events (6 total) -> exceeds relay limits (3 > 2) and total limits
    findings3 = validate_meet_data(cache)
    limit_findings3 = [f for f in findings3 if f.category == "Rules Limit"]
    # Should have relay warning + total warning
    assert len(limit_findings3) == 2
    categories_msgs = [f.message for f in limit_findings3]
    assert any("exceeds relay limits" in m for m in categories_msgs)
    assert any("exceeds total entry limits" in m for m in categories_msgs)
