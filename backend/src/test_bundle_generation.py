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


def generate_test_bundle():
    print("Loading sample data...")
    table_data = load_sample_data()
    print(f"Loaded {len(table_data)} tables.")
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)

    output_dir = "src/tmp_test_bundles"
    os.makedirs(output_dir, exist_ok=True)
    bundle_path = os.path.join(output_dir, "lineup_test_bundle.zip")

    genders = ["Girls"]  # Just one for now
    age_groups = ["6 & under"]  # Just one for now

    print(f"Generating bundle to {bundle_path}...")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for gender in genders:
            for age in age_groups:
                title = f"Lineup - {gender} {age}"
                print(f"  Processing: {title}...")

                # Lineup report uses timer sheets extractor logic (heat-based)
                report_data = extractor.extract_timer_sheets_data(
                    report_title=title, gender_filter=gender, age_group_filter=age
                )

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    temp_path = tmp.name

                renderer = WeasyRenderer(temp_path)
                renderer.render_entries(report_data, "lineups.html")

                filename = f"{gender}_{age.replace(' ', '_')}.pdf"
                zip_file.write(temp_path, filename)
                os.remove(temp_path)

    with open(bundle_path, "wb") as f:
        f.write(zip_buffer.getvalue())

    print(f"Success! Bundle generated at {bundle_path}")


if __name__ == "__main__":
    generate_test_bundle()
