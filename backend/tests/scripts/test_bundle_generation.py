import json
import os
import re
import sys
import tempfile
import zipfile

# Add backend/src to path
sys.path.append(os.path.dirname(__file__))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer


def load_anonymized_data():
    # Use absolute path within the container (fixtures_root to avoid shadowing)
    data_path = "/app/data/fixtures_root/anonymized_meets/2024-06-22 BH @ DP Meet2-MeetMgr.json"
    if not os.path.exists(data_path):
        # Fallback for local development if needed
        data_path = "tests/fixtures/anonymized_meets/2024-06-22 BH @ DP Meet2-MeetMgr.json"
    with open(data_path) as f:
        full_json = json.load(f)
        return full_json["data"]


def enhance_data(table_data):
    # Ensure Relay and RelayNames lists exist
    if "Relay" not in table_data:
        table_data["Relay"] = []
    if "RelayNames" not in table_data:
        table_data["RelayNames"] = []

    # 1. Repurpose Event 14 and 16 to be Boys Relays (80 total events)
    for evt in table_data.get("Event", []):
        if evt["Event_no"] == 14:
            evt["Ind_rel"] = "R"
            evt["Event_stroke"] = "A"  # Freestyle Relay
            evt["Event_dist"] = 100
        elif evt["Event_no"] == 16:
            evt["Ind_rel"] = "R"
            evt["Event_stroke"] = "E"  # Medley Relay
            evt["Event_dist"] = 100

    # 2. Add relay entries for these new Boys relays
    for e_ptr in [14, 16]:
        # Add A Relay for Team 20
        table_data["Relay"].append(
            {
                "Event_ptr": e_ptr,
                "Team_no": 20,
                "Team_ltr": "A",
                "ConvSeed_time": 95.0,
                "Fin_heat": 1,
                "Fin_lane": 1,
                "Round1": "F",
            }
        )
        for pos in range(1, 5):
            table_data["RelayNames"].append(
                {
                    "Event_ptr": e_ptr,
                    "Team_no": 20,
                    "Team_ltr": "A",
                    "Ath_no": 1360 + pos,
                    "Pos_no": pos,
                    "Event_round": "F",
                }
            )

    # 3. Add 'B' relay teams for each team (BH=20, DP=21) to Event 1
    for t_no in [20, 21]:
        # Add B Relay entry
        table_data["Relay"].append(
            {
                "Event_ptr": 1,
                "Team_no": t_no,
                "Team_ltr": "B",
                "ConvSeed_time": 185.0,
                "Fin_heat": 1,
                "Fin_lane": 7 if t_no == 20 else 8,
                "Round1": "F",
            }
        )
        # Add 4 swimmers for the B relay
        for pos in range(1, 5):
            ath_no = 1448 + pos if t_no == 20 else 1500 + pos
            table_data["RelayNames"].append(
                {"Event_ptr": 1, "Team_no": t_no, "Team_ltr": "B", "Ath_no": ath_no, "Pos_no": pos, "Event_round": "F"}
            )

    # 4. Limit ALL relays to exactly 4 swimmers
    relay_counts = {}
    new_relay_names = []
    for rn in table_data["RelayNames"]:
        key = (rn["Event_ptr"], rn["Team_no"], rn["Team_ltr"])
        count = relay_counts.get(key, 0)
        if count < 4:
            new_relay_names.append(rn)
            relay_counts[key] = count + 1
    table_data["RelayNames"] = new_relay_names

    # 5. Enforce only one 'A' relay team per team per event
    if "Relay" in table_data:
        seen_a_relays = set()
        unique_relays = []
        for r in table_data["Relay"]:
            e_ptr = r.get("Event_ptr")
            t_no = r.get("Team_no")
            t_ltr = str(r.get("Team_ltr", "A")).upper()
            if t_ltr == "A":
                key = (e_ptr, t_no)
                if key in seen_a_relays:
                    continue
                seen_a_relays.add(key)
            unique_relays.append(r)
        table_data["Relay"] = unique_relays

    # 6. Ensure at least 50% of swimmers have seed times
    if "Entry" in table_data:
        for i, entry in enumerate(table_data["Entry"]):
            if i % 2 == 0:
                entry["ConvSeed_time"] = 25.5 + (i % 10)

    if "Relay" in table_data:
        for i, relay in enumerate(table_data["Relay"]):
            if i % 2 == 0:
                relay["ConvSeed_time"] = 110.0 + (i * 2)

    # 7. Mixed gender event with girl swimmer
    mixed_evts = [e["Event_ptr"] for e in table_data.get("Event", []) if e.get("Event_gender") == "X"]
    if mixed_evts:
        e_ptr = mixed_evts[0]
        if not any(rn["Event_ptr"] == e_ptr and rn["Ath_no"] == 1361 for rn in table_data["RelayNames"]):
            table_data["RelayNames"].append(
                {"Event_ptr": e_ptr, "Team_no": 20, "Team_ltr": "A", "Ath_no": 1361, "Pos_no": 4, "Event_round": "F"}
            )

    return table_data


def generate_test_bundle():
    print("Loading anonymized meet data (80 events)...")
    table_data = load_anonymized_data()
    table_data = enhance_data(table_data)

    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)

    full_data = converter.convert()

    found_teams = set()
    found_ages = set()
    for sess in full_data.get("sessions", []):
        for evt in sess.get("events", []):
            desc = evt.get("eventDesc", "")
            match = re.search(r"(\d+ & under|\d+-\d+|\d+ & over|Open)", desc)
            if match:
                found_ages.add(match.group(1))
            for ent in evt.get("entries", []):
                if ent.get("team"):
                    found_teams.add(ent.get("team"))

    print(f"Found Teams: {found_teams}")
    print(f"Found Ages: {found_ages}")

    output_dir = "src/tmp_test_bundles"
    html_dir = os.path.join(output_dir, "html")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(html_dir, exist_ok=True)

    # a) "Line-Up Parents Programs"
    parents_bundle_path = os.path.join(output_dir, "parents_lineups.zip")
    print(f"Generating Parents Bundle to {parents_bundle_path}...")
    with zipfile.ZipFile(parents_bundle_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for team in found_teams:
            if not team:
                continue
            for gender in ["Girls", "Boys"]:
                for age in ["6 & under", "7-8", "9-10"]:
                    title = f"Line-Up - {team} - {gender} {age}"
                    data = extractor.extract_meet_program_data(
                        report_title=title,
                        gender_filter=gender,
                        age_group_filter=age,
                        team_filter=team,
                        columns_on_page=2,
                    )
                    if data["groups"]:
                        filename_base = f"{team.strip().replace(' ', '_')}_{gender}_{age.replace(' ', '_')}"
                        filename_pdf = f"{filename_base}.pdf"
                        filename_html = f"{filename_base}.html"
                        render_to_zip_and_file(
                            zip_file, WeasyRenderer, data, filename_pdf, os.path.join(html_dir, filename_html)
                        )

    # b) "Coaches Meet Program"
    coaches_pdf = os.path.join(output_dir, "coaches_program.pdf")
    coaches_html = os.path.join(html_dir, "coaches_program.html")
    print(f"Generating Coaches Program to {coaches_pdf}...")
    data = extractor.extract_meet_program_data(
        report_title="Coaches Meet Program", columns_on_page=2, show_relay_swimmers=True
    )
    renderer = WeasyRenderer(coaches_pdf)
    renderer.render_meet_program(data)
    with open(coaches_html, "w") as f:
        f.write(renderer.render_to_html(data))

    # c) "Line Up Program for Posting {gender}"
    for gender in ["Girls", "Boys"]:
        posting_pdf = os.path.join(output_dir, f"posting_program_{gender.lower()}.pdf")
        posting_html = os.path.join(html_dir, f"posting_program_{gender.lower()}.html")
        print(f"Generating Posting Program ({gender}) to {posting_pdf}...")
        data = extractor.extract_meet_program_data(
            report_title=f"Posting Program - {gender}",
            gender_filter=gender,
            columns_on_page=2,
            show_relay_swimmers=True,
        )
        renderer = WeasyRenderer(posting_pdf)
        renderer.render_meet_program(data)
        with open(posting_html, "w") as f:
            f.write(renderer.render_to_html(data))

    # d) "Computer Team Meet Program"
    computer_pdf = os.path.join(output_dir, "computer_team_program.pdf")
    computer_html = os.path.join(html_dir, "computer_team_program.html")
    print(f"Generating Computer Team Program to {computer_pdf}...")
    data = extractor.extract_meet_program_data(
        report_title="Computer Team Program", columns_on_page=1, show_relay_swimmers=True
    )
    renderer = WeasyRenderer(computer_pdf)
    renderer.render_meet_program(data)
    with open(computer_html, "w") as f:
        f.write(renderer.render_to_html(data))

    print(f"Success! Examples generated in {output_dir}")


def render_to_zip_and_file(zip_file, renderer_class, data, filename_pdf, html_path):
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        temp_path = tmp.name
    renderer = renderer_class(temp_path)
    renderer.render_meet_program(data)
    zip_file.write(temp_path, filename_pdf)

    # Save HTML too
    with open(html_path, "w") as f:
        f.write(renderer.render_to_html(data))

    os.remove(temp_path)


if __name__ == "__main__":
    generate_test_bundle()
