import json


def normalize(val):
    return str(val).strip().lower()


def compare():
    with open("ground_truth.json", "r") as f:
        ground_truth = json.load(f)

    with open("spreadsheet_data.json", "r") as f:
        ss_raw = json.load(f)

    ss_values = ss_raw.get("values", [])
    headers = ss_values[0]  # noqa: F841

    ss_list = []
    for row in ss_values[1:]:
        if not row or len(row) < 4:
            continue
        ss_list.append(
            {
                "Age Group": row[0],
                "Gender": row[1],
                "Preferred Name": row[2],
                "Last Name": row[3],
                "Medley Relay": row[6] if len(row) > 6 else "",
                "Free Relay": row[7] if len(row) > 7 else "",
                "Free": row[8] if len(row) > 8 else "",
                "Back": row[9] if len(row) > 9 else "",
                "Breast": row[10] if len(row) > 10 else "",
                "Fly": row[11] if len(row) > 11 else "",
                "IM": row[12] if len(row) > 12 else "",
                "ID": row[13] if len(row) > 13 else "",
            }
        )

    gt_list = ground_truth

    # Match by fuzzy name
    matched_gt = set()
    matched_ss = set()

    discrepancies = []

    for i, ss in enumerate(ss_list):
        for j, gt in enumerate(gt_list):
            if j in matched_gt:
                continue

            # Match criteria: Last name exact, First word of Preferred Name exact, Gender exact
            ss_first = normalize(ss["Preferred Name"]).split()[0]
            gt_first = normalize(gt["Preferred Name"]).split()[0]

            if (
                normalize(ss["Last Name"]) == normalize(gt["Last Name"])
                and ss_first == gt_first
                and normalize(ss["Gender"]) == normalize(gt["Gender"])
            ):
                matched_gt.add(j)
                matched_ss.add(i)

                # Check for event differences
                event_cols = [
                    "Medley Relay",
                    "Free Relay",
                    "Free",
                    "Back",
                    "Breast",
                    "Fly",
                    "IM",
                ]
                diffs = []
                for col in event_cols:
                    g = "X" if normalize(gt.get(col, "")) in ["x", "true"] else ""
                    s = "X" if normalize(ss.get(col, "")) in ["x", "true"] else ""
                    if g != s:
                        diffs.append(f"{col}: MDB='{g}' vs SS='{s}'")

                if diffs:
                    discrepancies.append(
                        {
                            "Type": "Event Registration Change",
                            "Swimmer": f"{ss['Preferred Name']} {ss['Last Name']}",
                            "AgeGroup": ss["Age Group"],
                            "Details": diffs,
                        }
                    )
                break

    # Unmatched
    for i, ss in enumerate(ss_list):
        if i not in matched_ss:
            discrepancies.append(
                {
                    "Type": "Swimmer in Spreadsheet NOT in MDB",
                    "Swimmer": f"{ss['Preferred Name']} {ss['Last Name']}",
                    "AgeGroup": ss["Age Group"],
                    "Details": [f"ID: {ss['ID']}"],
                }
            )

    for j, gt in enumerate(gt_list):
        if j not in matched_gt:
            discrepancies.append(
                {
                    "Type": "Swimmer in MDB NOT in Spreadsheet",
                    "Swimmer": f"{gt['Preferred Name']} {gt['Last Name']}",
                    "AgeGroup": gt["Age Group"],
                    "Details": [f"MDB ID: {gt['ID']}"],
                }
            )

    print(json.dumps(discrepancies, indent=2))


if __name__ == "__main__":
    compare()
