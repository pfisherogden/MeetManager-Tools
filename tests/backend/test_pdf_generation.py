import os
import sys
import json
import pytest
import pdfplumber

# Add backend/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../backend/src")))

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.renderer import PDFRenderer
from mm_to_json.reporting.config import ReportConfig, ReportLayout

FIXTURES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../fixtures/anonymized_meets"))

def get_anonymized_fixtures():
    fixtures = []
    if os.path.exists(FIXTURES_DIR):
        for f in os.listdir(FIXTURES_DIR):
            if f.endswith(".json"):
                fixtures.append(os.path.join(FIXTURES_DIR, f))
    return fixtures

@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_meet_entries_pdf_generation(fixture_path, tmp_path):
    with open(fixture_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    # 1. Extract Data
    entries_data = extractor.extract_meet_entries_data()
    
    # 2. Render PDF
    output_pdf = str(tmp_path / "test_entries.pdf")
    config = ReportConfig(
        title="Meet Entries Report",
        layout=ReportLayout(columns_on_page=1)
    )
    renderer = PDFRenderer(output_pdf, config)
    renderer.render(entries_data)
    
    assert os.path.exists(output_pdf)
    assert os.path.getsize(output_pdf) > 0
    
    # 3. Verify content
    with pdfplumber.open(output_pdf) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
            
        # Check for meet name
        meet_name = entries_data.get("meet_name")
        if meet_name and len(meet_name) > 2:
            assert meet_name in text

@pytest.mark.parametrize("fixture_path", get_anonymized_fixtures())
def test_meet_program_pdf_generation(fixture_path, tmp_path):
    with open(fixture_path, "r") as f:
        fixture_wrapper = json.load(f)
    
    table_data = fixture_wrapper["data"]
    converter = MmToJsonConverter(table_data=table_data)
    extractor = ReportDataExtractor(converter)
    
    # 1. Extract Data
    program_data = extractor.extract_meet_program_data()
    
    # 2. Render PDF (2-column)
    output_pdf = str(tmp_path / "test_program.pdf")
    config = ReportConfig(
        title="Meet Program",
        layout=ReportLayout(columns_on_page=2)
    )
    renderer = PDFRenderer(output_pdf, config)
    renderer.render(program_data)
    
    assert os.path.exists(output_pdf)
    assert os.path.getsize(output_pdf) > 0
    
    # 3. Verify content
    with pdfplumber.open(output_pdf) as pdf:
        text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
            
        meet_name = program_data.get("meet_name")
        if meet_name and len(meet_name) > 2:
            assert meet_name in text
