import csv
import json
import sys

def extract_reports(csv_path, output_json):
    reports = []
    with open(csv_path, 'r', encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert values to correct types (int where possible, otherwise stay string)
            processed_row = {}
            for k, v in row.items():
                if v == "":
                    processed_row[k] = None
                else:
                    try:
                        # Handle float scores or simple ints
                        if "." in v:
                            processed_row[k] = float(v)
                        else:
                            processed_row[k] = int(v)
                    except ValueError:
                        processed_row[k] = v
            reports.append(processed_row)
    
    with open(output_json, 'w') as f:
        json.dump(reports, f, indent=2)
    print(f"Extracted {len(reports)} reports to {output_json}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_reports.py <input_csv> <output_json>")
    else:
        extract_reports(sys.argv[1], sys.argv[2])
