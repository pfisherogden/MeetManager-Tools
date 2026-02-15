import io
import os
import sys
import tempfile
import zipfile
import pandas as pd
import json
import re

# Add backend/src to path
sys.path.append(os.path.dirname(__file__))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer

def load_sample_data():
    data_path = "data/Sample_Data.json"
    if not os.path.exists(data_path):
        data_path = "../data/Sample_Data.json"
    with open(data_path) as f:
        return json.load(f)

def enhance_data_with_multi_team(table_data):
    # Add a second team
    if "Team" in table_data:
        t2 = {
            "Team_no": 99,
            "Team_name": "Shark Aquatics",
            "Team_abbr": "SHRK",
            "Team_short": "Sharks",
            "Team_lsc": "PC"
        }
        table_data["Team"].append(t2)
            
    # Add some athletes for the second team
    if "Athlete" in table_data:
        a1 = {"Ath_no": 9901, "Team_no": 99, "Last_name": "Swift", "First_name": "Taylor", "Sex": "F", "Ath_age": 8}
        a2 = {"Ath_no": 9902, "Team_no": 99, "Last_name": "Ocean", "First_name": "Frank", "Sex": "M", "Ath_age": 10}
        table_data["Athlete"].extend([a1, a2])

    # Add entries for the second team to existing or new events
    if "Entry" in table_data:
        # Taylor (Team 99) to Event 1
        e1 = {"Event_ptr": 1, "Ath_no": 9901, "Fin_heat": 1, "Fin_lane": 3, "ConvSeed_time": 22.0, "Fin_Time": 0.0, "Fin_Stat": "", "Round1": "F"}
        # Frank (Team 99) to Event 2
        e2 = {"Event_ptr": 2, "Ath_no": 9902, "Fin_heat": 1, "Fin_lane": 4, "ConvSeed_time": 45.0, "Fin_Time": 0.0, "Fin_Stat": "", "Round1": "F"}
        table_data["Entry"].extend([e1, e2])

    # Ensure Meet info is robust
    if "Meet" in table_data:
        m = table_data["Meet"][0]
        m["Meet_class"] = 1
        m["Meet_numlanes"] = 6

    # Add a relay event
    if "Event" in table_data:
        r_evt = {
            "Event_ptr": 9999, "Event_no": 99, "Ind_rel": "R", "Event_gender": "F", "Event_dist": 100,
            "Event_stroke": "R", "Low_age": 7, "High_age": 8, "Event_sex": "Girls",
            "Num_prelanes": 6, "Num_finlanes": 6, "Event_rounds": 1
        }
        # Add a Mixed event
        m_evt = {
            "Event_ptr": 8888, "Event_no": 88, "Ind_rel": "I", "Event_gender": "X", "Event_dist": 50,
            "Event_stroke": "A", "Low_age": 9, "High_age": 10, "Event_sex": "Mixed",
            "Num_prelanes": 6, "Num_finlanes": 6, "Event_rounds": 1
        }
        table_data["Event"].extend([r_evt, m_evt])
        
        # Relay entry - use multiple column names just in case
        if "Relay" not in table_data: table_data["Relay"] = []
        table_data["Relay"].append({
            "Event_ptr": 9999, "Team_no": 99, "Team_ltr": "A", "ConvSeed_time": 85.0,
            "Fin_heat": 1, "Fin_lane": 1, "Fin_Time": 0.0, "Fin_Stat": "", "Round1": "F",
            "Heat1": 1, "Lane1": 1 # Some schemas use this
        })
        
        # Mixed entry (Taylor and Frank)
        table_data["Entry"].append({"Event_ptr": 8888, "Ath_no": 9901, "Fin_heat": 1, "Fin_lane": 1, "ConvSeed_time": 35.0, "Round1": "F"})
        table_data["Entry"].append({"Event_ptr": 8888, "Ath_no": 9902, "Fin_heat": 1, "Fin_lane": 2, "ConvSeed_time": 38.0, "Round1": "F"})

        # Relay athletes
        if "RelayNames" not in table_data: table_data["RelayNames"] = []
        for pos in range(1, 5):
            table_data["RelayNames"].append({
                "Event_ptr": 9999, "Team_no": 99, "Team_ltr": "A", "Ath_no": 9901, "Pos": pos, "Event_round": "F"
            })

    return table_data

def generate_test_bundle():
    print("Loading sample data...")
    table_data = load_sample_data()
    print("Enhancing data...")
    table_data = enhance_data_with_multi_team(table_data)
    
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    full_data = converter.convert()
    
    # Debug info
    found_teams = set()
    found_ages = set()
    for sess in full_data.get("sessions", []):
        for evt in sess.get("events", []):
            desc = evt.get("eventDesc", "")
            # Heuristic extract age: "8 & under", "7-8", etc.
            match = re.search(r"(\d+ & under|\d+-\d+|\d+ & over|Open)", desc)
            if match: found_ages.add(match.group(1))
            for ent in evt.get("entries", []):
                found_teams.add(ent.get("team"))
    
    print(f"Found Teams: {found_teams}")
    print(f"Found Ages: {found_ages}")
    
    output_dir = "src/tmp_test_bundles"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Line-Up Parents Programs
    parents_bundle_path = os.path.join(output_dir, "parents_lineups.zip")
    print(f"Generating Parents Bundle to {parents_bundle_path}...")
    with zipfile.ZipFile(parents_bundle_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for team in found_teams:
            if not team: continue
            for gender in ["Girls", "Boys"]:
                for age in ["6 & under", "7-8", "9-10", "11-12", "13-14", "15-18"]:
                    title = f"Line-Up - {team} - {gender} {age}"
                    data = extractor.extract_timer_sheets_data(
                        report_title=title, 
                        gender_filter=gender, 
                        age_group_filter=age,
                        team_filter=team
                    )
                    if data["groups"]: 
                        filename = f"{team.replace(' ', '_')}_{gender}_{age.replace(' ', '_')}.pdf"
                        render_to_zip(zip_file, WeasyRenderer, data, "lineups.html", filename)

    # 2. Coaches Meet Program
    coaches_pdf = os.path.join(output_dir, "coaches_program.pdf")
    print(f"Generating Coaches Program to {coaches_pdf}...")
    data = extractor.extract_meet_program_data(report_title="Coaches Meet Program", columns_on_page=2, show_relay_swimmers=True)
    WeasyRenderer(coaches_pdf).render_meet_program(data)

    # 3. Line Up Program for Posting {gender}
    for gender in ["Girls", "Boys"]:
        posting_pdf = os.path.join(output_dir, f"posting_program_{gender.lower()}.pdf")
        print(f"Generating Posting Program ({gender}) to {posting_pdf}...")
        data = extractor.extract_meet_program_data(report_title=f"Posting Program - {gender}", gender_filter=gender, columns_on_page=2)
        WeasyRenderer(posting_pdf).render_meet_program(data)

    # 4. Computer Team Meet Program
    computer_pdf = os.path.join(output_dir, "computer_team_program.pdf")
    print(f"Generating Computer Team Program to {computer_pdf}...")
    data = extractor.extract_meet_program_data(report_title="Computer Team Program", columns_on_page=1, show_relay_swimmers=True)
    WeasyRenderer(computer_pdf).render_meet_program(data)

    print(f"Success! Examples generated in {output_dir}")

def render_to_zip(zip_file, renderer_class, data, template, filename):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        temp_path = tmp.name
    renderer = renderer_class(temp_path)
    renderer.render_entries(data, template)
    zip_file.write(temp_path, filename)
    os.remove(temp_path)

if __name__ == "__main__":
    generate_test_bundle()
