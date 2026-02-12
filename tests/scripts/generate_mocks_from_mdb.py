import os
import sys
import json
import pandas as pd
from faker import Faker

# Add backend/src to path for mm_to_json imports
sys.path.append(os.path.join(os.getcwd(), "backend", "src"))

from mm_to_json.mm_to_json import MmToJsonConverter

fake = Faker()

def anonymize_athlete_table(df, schema_type):
    if df.empty:
        return df
    
    # Helper to find column name regardless of case
    def find_col(possible_names):
        for name in possible_names:
            for col in df.columns:
                if col.lower() == name.lower():
                    return col
        return None

    sex_col = find_col(["Sex", "Ath_Sex"])
    first_col = find_col(["First", "First_name", "FirstName"])
    last_col = find_col(["Last", "Last_name", "LastName"])
    birth_col = find_col(["Birth", "Birth_date", "BirthDate", "DOB"])
    
    # Clear other PII
    pii_cols = ["Home_addr1", "Home_addr2", "Home_city", "Home_prov", "Home_statenew", 
                "Home_zip", "Home_cntry", "Home_daytele", "Home_evetele", "Home_faxtele", 
                "Home_email", "Home_celltele", "Home_emergcontact", "Home_emergtele",
                "Pref_name", "Reg_no", "Regn", "Picture_bmp"]

    for col in df.columns:
        if any(p.lower() in col.lower() for p in pii_cols):
            df[col] = None

    for idx in df.index:
        gender = "U"
        if sex_col:
            gender = str(df.at[idx, sex_col]).upper()
        
        if first_col:
            if gender == "F":
                df.at[idx, first_col] = fake.first_name_female()
            elif gender == "M":
                df.at[idx, first_col] = fake.first_name_male()
            else:
                df.at[idx, first_col] = fake.first_name()
        
        if last_col:
            df.at[idx, last_col] = fake.last_name()
            
        if birth_col:
            # Note: Jackcess might handle objects, but mdb-tools gives strings.
            # We'll stick to string format for now as it's just for mock data.
            try:
                dob = fake.date_of_birth(minimum_age=5, maximum_age=18)
                df.at[idx, birth_col] = dob.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass

    return df

def normalize_table_columns(df, table_name):
    """Normalize column names to what mm_to_json expects."""
    rename_map = {
        "Ath_Sex": "Sex",
        "Ath_Sex_BS": "Sex",
        "Birth_date": "Birth",
        "BirthDate": "Birth",
        "MName": "Meet_name",
        "TName": "Team_name",
        "TCode": "Team_abbr",
    }
    # Case insensitive rename
    new_columns = {}
    for col in df.columns:
        for old, new in rename_map.items():
            if col.lower() == old.lower():
                new_columns[col] = new
    
    if new_columns:
        df = df.rename(columns=new_columns)
    return df

def load_via_mdb_tools(mdb_path):
    """Fallback to mdb-tools if Jackcess fails."""
    import subprocess
    import io
    
    print(f"Attempting to load {mdb_path} via mdb-tools...")
    try:
        # Use mdb-tables -1 to get table list
        tables = subprocess.check_output(["mdb-tables", "-1", mdb_path]).decode().splitlines()
        data = {}
        target_tables = ["Meet", "Team", "Athlete", "Event", "Session", "Sessitem", "Entry", "Relay", "RelayNames", "Divisions",
                         "MEET", "TEAM", "ATHLETE", "MTEVENT", "SESSIONS", "SESSITEM", "ENTRY", "RELAY", "RELAYNAMES", "DIVISIONS"]
        
        for table in tables:
            # Match against target tables case-insensitively
            if any(table.upper() == t.upper() for t in target_tables):
                print(f"  Exporting table: {table}")
                csv_data = subprocess.check_output(["mdb-export", mdb_path, table]).decode()
                # Use pandas to read the CSV data
                df = pd.read_csv(io.StringIO(csv_data))
                # Normalize columns
                df = normalize_table_columns(df, table)
                data[table] = df
        return data
    except Exception as e:
        print(f"Error loading via mdb-tools: {e}")
        return None

def generate_anonymized_fixture(mdb_path, output_dir):
    print(f"Processing {mdb_path}...")
    basename = os.path.basename(mdb_path)
    output_name = os.path.splitext(basename)[0] + ".json"
    output_path = os.path.join(output_dir, output_name)
    
    converter = None
    
    # On macOS, try mdb-tools FIRST as Jackcess often hangs
    if sys.platform == "darwin":
        print("macOS detected, trying mdb-tools first...")
        table_data = load_via_mdb_tools(mdb_path)
        if table_data:
            converter = MmToJsonConverter(table_data=table_data)
        else:
            print("mdb-tools failed, falling back to Jackcess...")

    if not converter:
        try:
            print("Trying MmToJsonConverter with Jackcess...")
            converter = MmToJsonConverter(mdb_path=mdb_path)
        except Exception as e:
            print(f"Jackcess failed: {e}")
            table_data = load_via_mdb_tools(mdb_path)
            if table_data:
                converter = MmToJsonConverter(table_data=table_data)
    
    if not converter:
        print(f"Failed to load {mdb_path} via any method.")
        return

    try:
        # Anonymize Athlete table
        if "Athlete" in converter.tables:
            converter.tables["Athlete"] = anonymize_athlete_table(converter.tables["Athlete"], converter.schema_type)
        
        # Export raw data as JSON
        fixture_data = converter.export_raw()
        
        # Also include some metadata for testing
        fixture_wrapper = {
            "metadata": {
                "source_mdb": basename,
                "anonymized": True,
                "schema_type": converter.schema_type
            },
            "data": fixture_data
        }
        
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(fixture_wrapper, f, indent=2, default=str)
            
        print(f"Generated fixture: {output_path}")
        
    except Exception as e:
        print(f"Error processing data for {mdb_path}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    mdb_files = [
        "tmp/2024-06-22 BH @ DP Meet2-MeetMgr.mdb",
        "tmp/sample_data_champs_2025-aftermeet.mdb"
    ]
    
    output_directory = "tests/fixtures/anonymized_meets"
    
    for mdb in mdb_files:
        full_path = os.path.join(os.getcwd(), mdb)
        if os.path.exists(full_path):
            generate_anonymized_fixture(full_path, output_directory)
        else:
            print(f"Skipping {mdb} - File not found")
