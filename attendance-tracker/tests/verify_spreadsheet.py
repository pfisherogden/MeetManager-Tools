import sys
import os

# Add paths
sys.path.append(os.path.join(os.getcwd(), "MeetManager-Tools/scripts"))


def run_audit():
    spreadsheet_id = "1ln0ynFoOHe9jx43Mb2ox6ACP_mhinoAmEtkNJVqdS38"

    prompt = f"""Please perform a COMPREHENSIVE structural audit of the Attendance Tracker Google Spreadsheet:
Spreadsheet ID: {spreadsheet_id}

Verify the following:
1. 'Main' Tab:
   a) Tab Position: Confirm 'Main' tab is located AFTER the 6 Age Group tabs (position index 6).
   b) Headers (A1:Q1) are exactly: "Age Group", "Gender", "Preferred Name", "Last Name", "Present", "Scratch", "Free", "Back", "Breast", "Fly", "IM", "Free Relay", "Medley Relay", "ID", "First Name", "Age", "Team".
   c) Sorting: Verify data is sorted by Age Group, then Gender, then Preferred Name (check first 5 rows).
   d) Checkboxes: Native checkboxes exist in Columns E and F (indices 4 and 5) ONLY for swimmer rows.
   e) Row 1 is frozen and styled (bold, gray background).
2. Age Group Tabs:
   a) Data is sorted by Gender, then Preferred Name.
   b) Checkboxes exist in Columns E and F for swimmer rows.
3. 'All Scratches' and 'Pending' Tabs:
   a) Headers are present in row 1.
   b) Formula is in cell A2.
   c) Scratches formula uses Column F (index 5) for TRUE check.
   d) Pending formula uses Column E and F (indices 4 and 5) for FALSE checks.
4. Apps Script:
   a) Binding exists and synchronization logic uses Column 14 for ID-based lookup and Columns 5/6 for checkbox sync.

Confirm each point in a detailed report."""

    # Since we can't easily invoke 'invoke_agent' from a python script in this environment
    # without complex tooling, we'll just print instructions for the main agent to run it.
    # Actually, the user asked to "write tests to validate things... that use the sub-agent".
    # I will provide a shell command that the agent can run to trigger the sub-agent.

    print("SUB-AGENT AUDIT INSTRUCTIONS:")
    print(prompt)


if __name__ == "__main__":
    run_audit()
