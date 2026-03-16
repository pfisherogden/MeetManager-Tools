import os
import sys
import pandas as pd
from mm_to_json.mm_to_json import MmToJsonConverter

def debug_champs():
    mdb_path = 'backend/data/sample_data_champs_2025-aftermeet.mdb'
    converter = MmToJsonConverter(mdb_path)
    data = converter.convert()
    
    print("--- MEET KEYS ---")
    if 'Meet' in data and data['Meet']:
        print(data['Meet'][0].keys())
        print(data['Meet'][0])
    
    print("\n--- TEAM KEYS ---")
    if 'Team' in data and data['Team']:
        print(data['Team'][0].keys())
        print(data['Team'][0])
        
    print("\n--- ATHLETE KEYS ---")
    if 'Athlete' in data and data['Athlete']:
        print(data['Athlete'][0].keys())
        print(data['Athlete'][0])
        
    print("\n--- ENTRY KEYS ---")
    if 'Entry' in data and data['Entry']:
        print(data['Entry'][0].keys())
        print(data['Entry'][0])

if __name__ == "__main__":
    debug_champs()
