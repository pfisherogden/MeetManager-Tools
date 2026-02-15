import io
import os
import sys
import tempfile
import zipfile

# Add backend/src to path
sys.path.append(os.path.dirname(__file__))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer


def load_sample_data():
    # Attempt to find a sample MDB
    data_path = "data/Sample_Data.json"
    if not os.path.exists(data_path):
        data_path = "../data/Sample_Data.json"

    import json

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
        import pandas as pd
        df_team = pd.DataFrame(table_data["Team"])
        if 99 not in df_team["Team_no"].values:
            table_data["Team"].append(t2)
            
    # Add some athletes for the second team
    if "Athlete" in table_data:
        a1 = {
            "Ath_no": 9901, "Team_no": 99, "Last_name": "Swift", "First_name": "Taylor", 
            "Sex": "F", "Ath_age": 8, "Reg_no": "010101TAYLSWIF"
        }
        a2 = {
            "Ath_no": 9902, "Team_no": 99, "Last_name": "Ocean", "First_name": "Frank", 
            "Sex": "M", "Ath_age": 10, "Reg_no": "020202FRAKOCEA"
        }
        table_data["Athlete"].extend([a1, a2])

    # Add a relay event if not present or just add entries to one
    if "Event" in table_data:
        # Check for relay event
        import pandas as pd
        df_evt = pd.DataFrame(table_data["Event"])
        relay_evts = df_evt[df_evt["Ind_rel"] == "R"]
        if relay_evts.empty:
            # Create a mock relay event
            r_evt = {
                "Event_ptr": 999, "Event_no": 99, "Event_gender": "F", "Event_dist": 100,
                "Event_stroke": "R", "Ind_rel": "R", "Low_age": 7, "High_age": 8,
                "Event_sex": "F", "Num_prelanes": 6, "Num_finlanes": 6, "Event_rounds": 1
            }
            table_data["Event"].append(r_evt)
            
            # Add relay entries
            if "Relay" not in table_data: table_data["Relay"] = []
            re1 = {
                "Event_ptr": 999, "Team_no": 99, "Team_ltr": "A", "Score": 12050,
                "Heat1": 1, "Lane1": 3, "Round1": "F"
            }
            table_data["Relay"].append(re1)
            
            # Add relay athletes
            if "Relay_Athletes" not in table_data: table_data["Relay_Athletes"] = []
            for pos in range(1, 5):
                table_data["Relay_Athletes"].append({
                    "Event_ptr": 999, "Team_no": 99, "Team_ltr": "A", 
                    "Ath_no": 9901, "Pos": pos, "Round": "F"
                })

    return table_data

def generate_test_bundle():
    print("Loading sample data...")
    table_data = load_sample_data()
    
    print("Enhancing data with second team and relays...")
    table_data = enhance_data_with_multi_team(table_data)
    
    print(f"Loaded {len(table_data)} tables.")
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)


    


    output_dir = "src/tmp_test_bundles"


    os.makedirs(output_dir, exist_ok=True)


    


    # 1. Line-Up Parents Programs
    # Generates reports per-team for specific age/gender groups
    parents_bundle = os.path.join(output_dir, "parents_lineups.zip")
    print(f"Generating Parents Bundle to {parents_bundle}...")
    with zipfile.ZipFile(parents_bundle, "w", zipfile.ZIP_DEFLATED) as zip_file:
        teams = converter.tables["Team"]["Team_name"].tolist() if "Team" in converter.tables else ["All Teams"]
        for team in teams:
            for gender in ["Girls", "Boys"]:
                for age in ["6 & under", "7-8", "9-10"]:
                    title = f"Line-Up - {team} - {gender} {age}"
                    data = extractor.extract_timer_sheets_data(
                        report_title=title, 
                        gender_filter=gender, 
                        age_group_filter=age,
                        team_filter=team
                    )
                    if data["groups"]: # Only add if there's data for this team/age/gender
                        render_to_zip(zip_file, renderer, data, "lineups.html", f"{team.replace(' ', '_')}_{gender}_{age.replace(' ', '_')}.pdf")





    # 2. Coaches Meet Program


    # All teams/events, 2-column


    coaches_pdf = os.path.join(output_dir, "coaches_program.pdf")


    print(f"Generating Coaches Program to {coaches_pdf}...")


    data = extractor.extract_meet_program_data(report_title="Coaches Meet Program", columns_on_page=2, show_relay_swimmers=True)


    WeasyRenderer(coaches_pdf).render_meet_program(data)





    # 3. Line Up Program for Posting {gender}


    # Separate for girls and boys+mixed, 2-column, include entry times


    for gender in ["Girls", "Boys"]:


        posting_pdf = os.path.join(output_dir, f"posting_program_{gender.lower()}.pdf")


        print(f"Generating Posting Program ({gender}) to {posting_pdf}...")


        data = extractor.extract_meet_program_data(report_title=f"Posting Program - {gender}", gender_filter=gender, columns_on_page=2)


        WeasyRenderer(posting_pdf).render_meet_program(data)





    # 4. Computer Team Meet Program


    # All teams/events, 1-column


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


    from mm_to_json.reporting.weasy_renderer import WeasyRenderer


    renderer = WeasyRenderer


    generate_test_bundle()
