import json
import os
import sys
from typing import Any, Dict, List

# Add backend/src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from mm_to_json.mdb_writer import add_memorized_report, open_db

# Default template for a report row (100 columns)
DEFAULT_REPORT = {
    "Mem_Name": "Unnamed Report",
    "Mem_Type": 4,  # Program
    "Num_Columns": 1,
    "Sort_Order": 0,
    "Date_Time": 2,
    "ID_Type": 0,
    "Top_HowMany": 0,
    "Num_RelayNames": 4,
    "Show_StartTimes": 0,
    "Incl_Records": 1,
    "Incl_TimeStds": 0,
    "Incl_QualTimes": 0,
    "Incl_EvtComments": 0,
    "Line_ForResults": 0,
    "Incl_NoEntries": 0,
    "Incl_PriorResults": 0,
    "Incl_Rnd1Alt": 0,
    "Incl_EmptyLanes": 0,
    "Show_SeedTimes": 1,
    "Sep_ABFinal": 0,
    "OneEvent_PerPage": 0,
    "Ref_Format": 0,
    "OneHeat_PerPage": 0,
    "Dbl_Space": 0,
    "Show_Ranks": 0,
    "MultiAge_Split": 0,
    "Incl_QualifiedAlts": 0,
    "ScrAltExhSpec_Filters": 0,
    "Incl_Scratches": 0,
    "Ignore_Psych": 0,
    "Sess_Row": 1,
    "Evt_Gender": 0,
    "Evt_LowAge": 0,
    "Evt_HighAge": 0,
    "Team_Abbr": "--",
    "Evt_Round": 0,
    "Evt_IndivOrRelay": 0,
    "Report_Type": 0,
    "Sort_OrderAthAge": 0,
    "Incl_AthNoEntries": 0,
    "Incl_AthNoEntries4Col": 0,
    "AddApost_ClassYear": 0,
    "Incl_CompNo": 0,
    "Incl_CompNo4Col": 0,
    "AddrSort_ByTeam": 0,
    "AddrSort_ByZip": 0,
    "Incl_ScrInEntryCount": 0,
    "Incl_AltInEntryCount": 0,
    "Incl_BirthDate": 0,
    "Incl_TeamAddr": 0,
    "Incl_Coaches": 0,
    "AthUseAbbr_ForTeam": 0,
    "Div_Abbr": "",
    "Report_Format": 0,
    "Incl_HeatLane": 0,
    "Add_LineSpace": 0,
    "Incl_RegID": 0,
    "Show_CheckIn": 0,
    "NumAth_PerPage": 0,
    "Splits_Choice": 0,
    "Results_ByHeat": 0,
    "Page_Break": 0,
    "Incl_SpecPts": 0,
    "Incl_TimeTrials": 0,
    "Incl_NoShows": 0,
    "Incl_TeamPts": 0,
    "Low_Lane": 1,
    "High_Lane": 10,
    "Score_Female": 0,
    "Score_Male": 0,
    "Score_Combined": 0,
    "Score_CombinedBoth": 0,
    "BAG_CATS": 0,
    "Flat_HTML": 0,
    "DotMatrix_LabelChoice": "",
    "Laser_LabelChoice": "",
    "Incl_TeamScore": 0,
    "Incl_FemaleTeamScore": 0,
    "Incl_MaleTeamScore": 0,
    "CombineDivisions_ForTeamPoints": 0,
    "Incl_DQCodes": 0,
    "Incl_ReactionTimes": 0,
    "Incl_Backups": 0,
    "UseLaser_Label": 0,
    "UseDQTimesfor_CombinedEvents": 0,
    "Incl_EntryTimes": 0,
    "Incl_PriorResultsSplits": 0,
    "Incl_LogosinFooter": 0,
    "LaneTimer_Pads": 0,
    "UseBestTimes_AllRounds": 0,
    "Qual_Club": 0,
    "QualClub_Scorers": 0,
    "PtBreakOut_HighPt": 0,
    "RTF_export": 0,
    "Results_ByHeatInclLane": 0,
    "NoShows_Only": 0,
    "Scratches_Only": 0,
    "DQs_Only": 0,
    "Combined_BothMustScore": 0
}

AGE_GROUPS = {
    "6&U": (0, 6),
    "7-8": (7, 8),
    "9-10": (9, 10),
    "11-12": (11, 12),
    "13-14": (13, 14),
    "15-18": (15, 18),
    "Open": (0, 18)
}

def create_preset_reports(team_abbr: str = "DP") -> List[Dict[str, Any]]:
    presets = []
    
    # 1. Lineup Reports (one for each age group)
    for name, (low, high) in AGE_GROUPS.items():
        if name == "Open": continue
        report = DEFAULT_REPORT.copy()
        report.update({
            "Mem_Name": f"Lineup: {name}",
            "Mem_Type": 4, # Program
            "Team_Abbr": team_abbr,
            "Evt_LowAge": low,
            "Evt_HighAge": high,
            "Num_Columns": 1,
            "Show_SeedTimes": 0,
            "Incl_Records": 0
        })
        presets.append(report)

    # 2. Timer Sheets (DPST standard: 6 events break)
    report = DEFAULT_REPORT.copy()
    report.update({
        "Mem_Name": "Timer Sheets (6/pg)",
        "Mem_Type": 6, # Lane Sheets
        "Add_LineSpace": 1,
        "Num_RelayNames": 4,
        "Show_SeedTimes": 1
    })
    presets.append(report)

    # 3. Meet Program (Triple Column - Complete)
    report = DEFAULT_REPORT.copy()
    report.update({
        "Mem_Name": "Program: Complete (3-col)",
        "Mem_Type": 4,
        "Num_Columns": 3,
        "Show_SeedTimes": 1,
        "Incl_Records": 1
    })
    presets.append(report)

    # 4. Results (Coach)
    report = DEFAULT_REPORT.copy()
    report.update({
        "Mem_Name": "Results: Coach",
        "Mem_Type": 7,
        "Incl_Scratches": 1,
        "Incl_NoShows": 1,
        "Incl_DQCodes": 1,
        "Show_SeedTimes": 1,
        "Incl_Records": 1
    })
    presets.append(report)

    return presets

def apply_reports(mdb_path: str, reports_json: str = None, team_abbr: str = "DP"):
    print(f"Opening {mdb_path}...")
    db = open_db(mdb_path)
    
    try:
        # Clear existing reports if any? 
        # For verification, maybe we want to keep them.
        # table = db.getTable("MemorizedReports")
        # for row in table:
        #     table.deleteRow(row)
        
        reports_to_add = []
        if reports_json and os.path.exists(reports_json):
            with open(reports_json, 'r') as f:
                reports_to_add = json.load(f)
        else:
            reports_to_add = create_preset_reports(team_abbr)

        print(f"Injecting {len(reports_to_add)} reports...")
        for report in reports_to_add:
            # Filter report keys to match table columns (some might be extra from JSON processing)
            # Actually our DEFAULT_REPORT has exactly 100.
            # We must ensure Mem_Ptr is NOT in the dict as it is auto-increment
            report_data = {k: v for k, v in report.items() if k != "Mem_Ptr"}
            add_memorized_report(db, **report_data)
            print(f"  Added: {report['Mem_Name']}")

    finally:
        db.close()
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_memorized_reports.py <mdb_path> [reports_json]")
    else:
        path = sys.argv[1]
        json_path = sys.argv[2] if len(sys.argv) > 2 else None
        apply_reports(path, json_path)
