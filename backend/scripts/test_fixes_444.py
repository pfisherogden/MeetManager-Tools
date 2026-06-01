import os
import sys
import pandas as pd
from typing import Any

# Add paths
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_dir, "../src"))

from mm_to_json.mm_to_json import MmToJsonConverter

def test_short_name():
    mdb_path = "/Users/pfo/Developer/tmp/DP_at_FAST_before_meet.mdb"
    print(f"Loading {mdb_path}...")
    conv = MmToJsonConverter(mdb_path)
    
    # Check Gabriella (Ath_no 2068)
    ath = conv.get_athlete_by_number(2068)
    print(f"Athlete 2068: {ath['firstName']} {ath['lastName']}")
    assert ath['firstName'] == "Ella"
    
    # Check Jaxon (Ath_no 2153)
    ath = conv.get_athlete_by_number(2153)
    print(f"Athlete 2153: {ath['firstName']} {ath['lastName']}")
    assert ath['firstName'] == "Jax"
    
    print("Short name test passed!")

def test_time_formatting():
    mdb_path = "/Users/pfo/Developer/tmp/DP_at_FAST_before_meet.mdb"
    conv = MmToJsonConverter(mdb_path)
    
    # Test num_to_string
    assert conv.num_to_string(1.5732) == "1.57"
    assert conv.num_to_string(117.320) == "117.32"
    
    # Test time_to_min_sec
    assert conv.time_to_min_sec("117.320") == "1:57.32"
    assert conv.time_to_min_sec("29.690") == "29.69"
    
    print("Time formatting test passed!")

if __name__ == "__main__":
    test_short_name()
    test_time_formatting()
