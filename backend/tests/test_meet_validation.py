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
                "fin_place": 1,
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

    # Case 4: 3 individual events + 3 relay events, but one relay has pos_no = 5 (alternate)
    # This should act like 3 individual + 2 relay events (5 total) -> exceeds total, but relay count is ok (2)
    cache_case4 = cache.copy()
    cache_case4["relaynames"] = [
        {"event_ptr": 20, "team_no": 100, "team_ltr": "A", "ath_no": 1, "relay_no": 1, "event_round": "F", "pos_no": 1},
        {"event_ptr": 21, "team_no": 100, "team_ltr": "A", "ath_no": 1, "relay_no": 2, "event_round": "F", "pos_no": 2},
        {
            "event_ptr": 22,
            "team_no": 100,
            "team_ltr": "A",
            "ath_no": 1,
            "relay_no": 3,
            "event_round": "F",
            "pos_no": 5,
        },  # Alternate!
    ]
    findings4 = validate_meet_data(cache_case4)
    limit_findings4 = [f for f in findings4 if f.category == "Rules Limit"]
    assert len(limit_findings4) == 1
    assert "exceeds total entry limits" in limit_findings4[0].message


def test_relays_with_ns_scored_logic():
    """Verify that unscored relays are not flagged by the 'Relays with NS' validation check."""
    cache = {
        "athlete": [],
        "team": [{"team_no": 100, "team_name": "Del Prado", "team_lsc": "DP"}],
        "event": [
            {"event_ptr": 72, "event_no": 72, "event_sex": "M", "low_age": 9, "high_age": 10, "ind_rel": "R"},
        ],
        "entry": [],
        "relay": [
            # 1. Unscored relay (should be ignored)
            {
                "event_ptr": 72,
                "relay_no": 1,
                "team_no": 100,
                "team_ltr": "A",
                "fin_heat": 1,
                "fin_lane": 4,
                "fin_time": 0.0,
                "fin_stat": "",
                "fin_place": 0,
            },
            # 2. Scored relay but with NS/No Time (should be flagged)
            {
                "event_ptr": 72,
                "relay_no": 2,
                "team_no": 100,
                "team_ltr": "B",
                "fin_heat": 1,
                "fin_lane": 5,
                "fin_time": 0.0,
                "fin_stat": "NS",
                "fin_place": 0,
            },
            # 3. Scored relay with a place but missing time (should be flagged)
            {
                "event_ptr": 72,
                "relay_no": 3,
                "team_no": 100,
                "team_ltr": "C",
                "fin_heat": 1,
                "fin_lane": 6,
                "fin_time": 0.0,
                "fin_stat": "",
                "fin_place": 3,
            },
        ],
        "relaynames": [],
    }

    findings = validate_meet_data(cache)
    relay_findings = [f for f in findings if f.category == "Relays with NS"]

    # We expect exactly 2 findings (B and C), since A is unscored
    assert len(relay_findings) == 2
    messages = [f.message for f in relay_findings]
    assert any("Team Del Prado 'B'" in m for m in messages)
    assert any("Team Del Prado 'C'" in m for m in messages)
    assert not any("Team Del Prado 'A'" in m for m in messages)


def test_ns_scratch_with_times():
    """Verify that swimmers with NS/Scratch/DQ-7 and a valid time in another event are flagged."""
    cache = {
        "athlete": [
            {"ath_no": 1, "first_name": "Alice", "last_name": "Smith", "ath_age": 10, "ath_sex": "F", "team_no": 100},
            {"ath_no": 2, "first_name": "Bob", "last_name": "Jones", "ath_age": 12, "ath_sex": "M", "team_no": 100},
        ],
        "team": [{"team_no": 100, "team_name": "Del Prado", "team_lsc": "DP"}],
        "event": [
            {"event_ptr": 10, "event_no": 1, "event_sex": "F", "low_age": 9, "high_age": 10, "ind_rel": "I"},
            {"event_ptr": 11, "event_no": 2, "event_sex": "F", "low_age": 9, "high_age": 10, "ind_rel": "I"},
            {"event_ptr": 12, "event_no": 3, "event_sex": "F", "low_age": 9, "high_age": 10, "ind_rel": "I"},
            {"event_ptr": 13, "event_no": 4, "event_sex": "F", "low_age": 9, "high_age": 10, "ind_rel": "I"},
        ],
        "entry": [
            # Alice: Event 10 has a valid time, Event 11 is NS
            {"ath_no": 1, "event_ptr": 10, "fin_time": 30.5, "fin_stat": "", "fin_heat": 1, "fin_lane": 3},
            {"ath_no": 1, "event_ptr": 11, "fin_time": 0.0, "fin_stat": "NS", "fin_heat": 1, "fin_lane": 4},
            # Bob: Event 12 has a valid time, Event 13 is DQ with code 7P (Declared False Start)
            {"ath_no": 2, "event_ptr": 12, "fin_time": 28.2, "fin_stat": "", "fin_heat": 1, "fin_lane": 2},
            {
                "ath_no": 2,
                "event_ptr": 13,
                "fin_time": 0.0,
                "fin_stat": "Q",
                "fin_dqcode": "7P",
                "fin_heat": 1,
                "fin_lane": 5,
            },
        ],
        "relay": [],
        "relaynames": [],
    }

    findings = validate_meet_data(cache)
    ns_scratch_findings = [f for f in findings if f.category == "NS/Scratch with Times"]
    assert len(ns_scratch_findings) == 2
    assert all(f.severity == pb2.VALIDATION_SEVERITY_WARNING for f in ns_scratch_findings)

    messages = [f.message for f in ns_scratch_findings]
    assert any("Alice Smith" in m and "NS/Scratch/DQ-7" in m for m in messages)
    assert any("Bob Jones" in m and "NS/Scratch/DQ-7" in m for m in messages)


def test_team_splashes_limit():
    """Verify that team splashes limit checks count correctly and trigger warning when > 420."""
    # Under limit: 420 splashes (400 individual + 5 relays = 420)
    cache_under = {
        "athlete": [
            {"ath_no": i, "first_name": f"Swimmer{i}", "last_name": "Test", "ath_age": 10, "ath_sex": "F", "team_no": 1}
            for i in range(1, 401)
        ],
        "team": [{"team_no": 1, "team_name": "Stingrays", "team_lsc": "SR"}],
        "event": [{"event_ptr": 1, "event_no": 1, "event_sex": "F", "low_age": 0, "high_age": 0, "ind_rel": "I"}],
        "entry": [
            {"ath_no": i, "event_ptr": 1, "fin_time": 0.0, "fin_stat": "", "fin_heat": 1, "fin_lane": 1}
            for i in range(1, 401)
        ],
        "relay": [{"team_ptr": 1, "event_ptr": 2, "fin_stat": ""} for _ in range(5)],
        "relaynames": [],
    }

    findings = validate_meet_data(cache_under)
    splashes_findings = [f for f in findings if f.category == "Splashes Limit"]
    assert len(splashes_findings) == 0

    # Over limit: 421 splashes (401 individual + 5 relays = 421)
    cache_over = {
        "athlete": [
            {"ath_no": i, "first_name": f"Swimmer{i}", "last_name": "Test", "ath_age": 10, "ath_sex": "F", "team_no": 1}
            for i in range(1, 402)
        ],
        "team": [{"team_no": 1, "team_name": "Stingrays", "team_lsc": "SR"}],
        "event": [{"event_ptr": 1, "event_no": 1, "event_sex": "F", "low_age": 0, "high_age": 0, "ind_rel": "I"}],
        "entry": [
            {"ath_no": i, "event_ptr": 1, "fin_time": 0.0, "fin_stat": "", "fin_heat": 1, "fin_lane": 1}
            for i in range(1, 402)
        ],
        "relay": [{"team_ptr": 1, "event_ptr": 2, "fin_stat": ""} for _ in range(5)],
        "relaynames": [],
    }

    findings = validate_meet_data(cache_over)
    splashes_findings = [f for f in findings if f.category == "Splashes Limit"]
    assert len(splashes_findings) == 1
    assert splashes_findings[0].severity == pb2.VALIDATION_SEVERITY_WARNING
    assert "exceeds splashes limit" in splashes_findings[0].message
    assert "421" in splashes_findings[0].message

    # Scratches excluded: 401 entries total but 2 individual scratched, 1 relay scratched
    # 401 individual (2 scratched) + 5 relays (1 scratched) = 399 + 4 * 4 = 415 splashes (under limit)
    entry_with_scratches = []
    for i in range(1, 402):
        if i == 1:
            entry_with_scratches.append(
                {"ath_no": i, "event_ptr": 1, "fin_time": 0.0, "fin_stat": "R", "fin_heat": 1, "fin_lane": 1}
            )
        elif i == 2:
            entry_with_scratches.append(
                {
                    "ath_no": i,
                    "event_ptr": 1,
                    "fin_time": 0.0,
                    "fin_stat": "",
                    "scr_stat": 1,
                    "fin_heat": 1,
                    "fin_lane": 1,
                }
            )
        else:
            entry_with_scratches.append(
                {"ath_no": i, "event_ptr": 1, "fin_time": 0.0, "fin_stat": "", "fin_heat": 1, "fin_lane": 1}
            )

    relays_with_scratch = [{"team_ptr": 1, "event_ptr": 2, "fin_stat": ""} for _ in range(4)]
    relays_with_scratch.append({"team_ptr": 1, "event_ptr": 2, "fin_stat": "R"})

    cache_scratches = {
        "athlete": [
            {"ath_no": i, "first_name": f"Swimmer{i}", "last_name": "Test", "ath_age": 10, "ath_sex": "F", "team_no": 1}
            for i in range(1, 402)
        ],
        "team": [{"team_no": 1, "team_name": "Stingrays", "team_lsc": "SR"}],
        "event": [{"event_ptr": 1, "event_no": 1, "event_sex": "F", "low_age": 0, "high_age": 0, "ind_rel": "I"}],
        "entry": entry_with_scratches,
        "relay": relays_with_scratch,
        "relaynames": [],
    }

    findings = validate_meet_data(cache_scratches)
    splashes_findings = [f for f in findings if f.category == "Splashes Limit"]
    assert len(splashes_findings) == 0


def test_ns_scratch_with_dq_times():
    """Verify that swimmers with regular DQs (time > 0) are counted as present for NS/Scratch checks."""
    cache = {
        "athlete": [
            {"ath_no": 1, "first_name": "Alice", "last_name": "Smith", "ath_age": 10, "ath_sex": "F", "team_no": 100},
            {"ath_no": 2, "first_name": "Bob", "last_name": "Jones", "ath_age": 12, "ath_sex": "M", "team_no": 100},
        ],
        "team": [{"team_no": 100, "team_name": "Del Prado", "team_lsc": "DP"}],
        "event": [
            {"event_ptr": 10, "event_no": 1, "event_sex": "F", "low_age": 9, "high_age": 10, "ind_rel": "I"},
            {"event_ptr": 11, "event_no": 2, "event_sex": "F", "low_age": 9, "high_age": 10, "ind_rel": "I"},
        ],
        "entry": [
            # Alice: Event 10 has a regular stroke DQ (3P) with time 30.5, Event 11 is NS.
            # This should trigger the warning because she has a recorded time (swam).
            {
                "ath_no": 1,
                "event_ptr": 10,
                "fin_time": 30.5,
                "fin_stat": "Q",
                "fin_dqcode": "3P",
                "fin_heat": 1,
                "fin_lane": 3,
            },
            {"ath_no": 1, "event_ptr": 11, "fin_time": 0.0, "fin_stat": "NS", "fin_heat": 1, "fin_lane": 4},
            # Bob: Event 10 has a DFS DQ (7P) with time 0.0 (no swim), Event 11 is NS.
            # This should NOT trigger because Bob has no recorded times (did not swim).
            {
                "ath_no": 2,
                "event_ptr": 10,
                "fin_time": 0.0,
                "fin_stat": "Q",
                "fin_dqcode": "7P",
                "fin_heat": 1,
                "fin_lane": 2,
            },
            {"ath_no": 2, "event_ptr": 11, "fin_time": 0.0, "fin_stat": "NS", "fin_heat": 1, "fin_lane": 5},
        ],
        "relay": [],
        "relaynames": [],
    }

    findings = validate_meet_data(cache)
    ns_scratch_findings = [f for f in findings if f.category == "NS/Scratch with Times"]

    # Alice should be flagged, Bob should not
    assert len(ns_scratch_findings) == 1
    assert ns_scratch_findings[0].affected_id == "1"
    assert "Alice Smith" in ns_scratch_findings[0].message
