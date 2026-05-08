
import os
import sys
import logging
import copy
from datetime import datetime, timedelta

# Add backend/src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_src_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "src"))
sys.path.append(backend_src_dir)

from mm_to_json.mm_to_json import MmToJsonConverter
from season_transformer import SeasonTransformer

def test_repro():
    template_path = "/app/season-setup/template_unzip/swmeets7/Summer League Meet Template.mdb"
    if not os.path.exists(template_path):
        print(f"Error: Template not found at {template_path}")
        return

    print(f"Loading template: {template_path}")
    template_conv = MmToJsonConverter(mdb_path=template_path)
    full_template = template_conv.export_full_schema()
    full_template["tables"] = {str(k): v for k, v in full_template["tables"].items()}
    
    def get_val(d, key):
        for k, v in d.items():
            if k.lower() == key.lower(): return v
        return None

    # Test Case 3: Meadows vs DP (Away) (5 lanes)
    print("\n--- Testing Meet 3: Meadows vs DP (Away) (5 lanes) ---")
    current_rows = {tname: copy.deepcopy(t_def["rows"]) for tname, t_def in full_template["tables"].items()}
    transformer = SeasonTransformer(current_rows, table_defs=full_template["tables"])
    
    transformer.purge_data(preserve_team_abbr="DP")
    transformer.ensure_team_exists("DP", "Del Prado Stingrays")
    transformer.ensure_team_exists("SHRK", "Pleasanton Meadows Sharks")
    
    # SHRK is Home, DP is Away
    transformer.update_meet(
        name="Del Prado @ Pleasanton Meadows",
        start_date="2026-06-13",
        lanes=5,
        location="Pleasanton Meadows",
        address="4110 Churchill Dr",
        home_team="SHRK",
        away_team="DP"
    )
    transformer.ensure_std_lanes()
    
    meet = transformer.table_data["Meet"][0]
    shrk_id = transformer.team_ids["SHRK"]
    dp_id = transformer.team_ids["DP"]
    
    assert get_val(meet, "meet_numlanes") == 5
    assert get_val(meet, "team_evenlanes") == shrk_id
    assert get_val(meet, "team_oddlanes") == dp_id
    
    # Check Events
    events = transformer.table_data["Event"]
    assert len(events) > 0
    for e in events:
        assert get_val(e, "Num_finlanes") == 5
        assert get_val(e, "Num_prelanes") == 5
    
    # Check StdLanes
    stdlanes = transformer.table_data["StdLanes"]
    row_5 = next(r for r in stdlanes if get_val(r, "tot_lanes") == 5)
    assert get_val(row_5, "order_01") == 3
    assert get_val(row_5, "order_02") == 4
    assert get_val(row_5, "order_03") == 2
    assert get_val(row_5, "order_04") == 5
    assert get_val(row_5, "order_05") == 1
    
    print("Meet 3 (5 lanes) verification PASSED")

    print("\n✅ All assertions passed in memory!")

if __name__ == "__main__":
    try:
        test_repro()
    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
