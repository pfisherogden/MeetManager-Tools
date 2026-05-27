import os
import sys

# Add scripts to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../scripts/season_setup"))

from season_transformer import SeasonTransformer


def test_scoring_champs():
    table_data = {"Scoring": [{"score_place": i, "ind_score": 0.0, "rel_score": 0.0} for i in range(1, 17)]}
    transformer = SeasonTransformer(table_data)
    transformer.setup_scoring_and_seeding(is_champs=True)

    scoring = table_data["Scoring"]
    # Individual: 12 places (20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5)
    assert scoring[0]["ind_score"] == 20.0
    assert scoring[11]["ind_score"] == 5.0
    assert scoring[12]["ind_score"] == 0.0

    # Relays: 8 places (40, 34, 32, 30, 28, 26, 24, 22)
    assert scoring[0]["rel_score"] == 40.0
    assert scoring[4]["rel_score"] == 28.0
    assert scoring[7]["rel_score"] == 22.0
    assert scoring[8]["rel_score"] == 0.0


def test_lane_settings_robust():
    table_data = {"MTEVENT": [{"MtEvent": 1, "Num_prelanes": 6, "Num_finlanes": 6, "Std_lanes": " "}]}
    transformer = SeasonTransformer(table_data)
    transformer.update_event_lanes(lanes=8)

    event = table_data["MTEVENT"][0]
    assert event["Num_prelanes"] == 8
    assert event["Num_finlanes"] == 8
    assert event["Std_lanes"] == "A"


def test_std_lanes_robust():
    table_data = {}  # Empty
    transformer = SeasonTransformer(table_data)
    transformer.ensure_std_lanes()

    std_lanes = transformer.table_data["StdLanes"]
    assert len(std_lanes) == 12

    # Check 6 lanes order: 3, 4, 2, 5, 1, 6
    row6 = next(r for r in std_lanes if r["Lanes"] == 6)
    assert row6["Order1"] == 3
    assert row6["Order2"] == 4
    assert row6["Order6"] == 6
    # Check fallback names too
    assert row6["order_01"] == 3


def test_sessions_linking():
    table_data = {
        "MTEVENT": [
            {"MtEvent": 1, "Event_no": 1, "Event_stroke": "E", "Ind_rel": "R", "Session": 0},
            {"MtEvent": 2, "Event_no": 2, "Event_stroke": "A", "Ind_rel": "I", "Session": 0},
        ],
        "Session": [],
        "Sessitem": [],
    }
    transformer = SeasonTransformer(table_data)
    transformer.consolidate_sessions(is_champs=True)

    # Check Session creation
    assert len(transformer.table_data["Session"]) == 7

    # Check linking in MTEVENT
    events = transformer.table_data["MTEVENT"]
    assert events[0]["Session"] == 1  # Med Relays
    assert events[1]["Session"] == 2  # Freestyle

    # Check Sessitem
    sessitems = transformer.table_data["Sessitem"]
    assert len(sessitems) == 2
    assert sessitems[0]["Event_ptr"] == 1
    assert sessitems[0]["Sess_ptr"] == 1
    assert sessitems[1]["Event_ptr"] == 2
    assert sessitems[1]["Sess_ptr"] == 2


if __name__ == "__main__":
    # Run tests if called directly
    test_scoring_champs()
    test_lane_settings_robust()
    test_std_lanes_robust()
    test_sessions_linking()
    print("All robust tests passed!")
