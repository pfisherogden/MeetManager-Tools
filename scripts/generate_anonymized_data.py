import csv
import io
import os
import subprocess
import sys
import json
import random

# Add backend/src to path
sys.path.append(os.path.join(os.getcwd(), "backend/src"))

from mm_to_json.mm_to_json import MmToJsonConverter

# Faked data lists
FIRST_NAMES = ["Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Henry", "Ivy", "Jack", "Katie", "Leo", "Mia", "Noah", "Olivia", "Peter", "Quinn", "Ryan", "Sophia", "Thomas"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
TEAM_NAMES = ["Blue Dolphins", "Red Sharks", "Green Turtles", "Golden Otters", "Silver Orcas", "Purple Penguins", "Orange Rays", "White Whales"]
TEAM_CODES = ["DOLP", "SHRK", "TURT", "OTTR", "ORCA", "PENG", "RAYS", "WHAL"]

def load_mdb(db_path):
    print(f"Exporting tables from {db_path} using mdb-export...")
    try:
        tables = subprocess.check_output(["mdb-tables", "-1", db_path]).decode("utf-8").splitlines()
    except subprocess.CalledProcessError as e:
        print(f"Error listing tables: {e}")
        return {}

    data = {}
    for t in tables:
        if not t.strip():
            continue
        try:
            csv_out = subprocess.check_output(["mdb-export", db_path, t]).decode("utf-8")
            data[t] = list(csv.DictReader(io.StringIO(csv_out)))
        except Exception as e:
            print(f"Skipping table {t}: {e}")
    return data

def anonymize_data():
    data_path = "backend/data/sample_data_champs_2025-aftermeet.mdb"
    if not os.path.exists(data_path):
        print(f"Error: {data_path} not found.")
        return

    print(f"Loading real data from {data_path}...")
    raw_data = load_mdb(data_path)
    
    # Identify tables to anonymize
    # Athlete: first_name, last_name, preferred_name, reg_no, birth_date
    # Team: team_name, team_abbr, team_city
    
    print("Anonymizing Teams...")
    team_id_map = {}
    teams = raw_data.get("Team", [])
    for idx, t in enumerate(teams):
        original_name = t.get("team_name")
        new_name = TEAM_NAMES[idx % len(TEAM_NAMES)] + f" {idx // len(TEAM_NAMES) + 1}" if idx >= len(TEAM_NAMES) else TEAM_NAMES[idx]
        new_code = TEAM_CODES[idx % len(TEAM_CODES)] + str(idx)
        
        t["team_name"] = new_name
        t["team_abbr"] = new_code
        t["team_city"] = "SwimCity"
        t["team_statenew"] = "CA"
        
    print("Anonymizing Athletes...")
    athletes = raw_data.get("Athlete", [])
    for a in athletes:
        a["last_name"] = random.choice(LAST_NAMES)
        a["first_name"] = random.choice(FIRST_NAMES)
        a["preferred_name"] = a["first_name"]
        a["reg_no"] = "ANON" + str(random.randint(100000, 999999))
        # Keep birth year/age similar for group logic consistency but randomize day/month
        original_dob = a.get("birth_date", "2010-01-01")
        if original_dob:
            year = original_dob.split("-")[0] if "-" in original_dob else "2010"
            a["birth_date"] = f"{year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

    # Output anonymized JSON fixture
    output_path = "tests/fixtures/anonymized_champs.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w") as f:
        json.dump(raw_data, f, indent=2)
    
    print(f"Anonymized data saved to {output_path}")
    print("Verification: First 3 anonymized athletes:")
    for a in athletes[:3]:
        print(f"  {a['first_name']} {a['last_name']} ({a['birth_date']})")

if __name__ == "__main__":
    anonymize_data()
