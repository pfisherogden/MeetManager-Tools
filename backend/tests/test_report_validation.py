import os

import pytest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor

try:
    from mm_to_json.reporting.weasy_renderer import WeasyRenderer

    WEASY_AVAILABLE = True
except (ImportError, OSError):
    WEASY_AVAILABLE = False
import json
import tempfile

from bs4 import BeautifulSoup


@pytest.fixture
def champs_cache():
    # File is in backend/tests/test_report_validation.py
    # Try multiple possible locations for the fixture
    search_paths = [
        # Relative to project root (local)
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tests/fixtures/anonymized_champs.json"),
        # Inside Docker data dir
        "/app/data/fixtures_root/anonymized_champs.json",
        # Fallback to backend/tests/fixtures if it was moved there
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures/anonymized_champs.json"),
    ]
    
    fixture_path = None
    for path in search_paths:
        if os.path.exists(path):
            fixture_path = path
            break
            
    if not fixture_path:
        raise FileNotFoundError(f"Could not find anonymized_champs.json in any of: {search_paths}")

    with open(fixture_path) as f:
        cache_raw = json.load(f)
    cache_data = cache_raw.get("data", cache_raw)
    # Normalize to lowercase keys as server.py does
    return {k.lower(): v for k, v in cache_data.items()}


@pytest.mark.skipif(not WEASY_AVAILABLE, reason="WeasyRenderer not available")
def test_meet_program_has_data(champs_cache):
    converter = MmToJsonConverter(table_data=champs_cache)
    extractor = ReportDataExtractor(converter)

    # 1. Extract data
    report_data = extractor.extract_meet_program_data()
    assert len(report_data["groups"]) > 0

    # 2. Render to HTML for verification
    renderer = WeasyRenderer("dummy.pdf")
    html = renderer.render_to_html(report_data)

    # 3. Validate HTML content
    soup = BeautifulSoup(html, "html.parser")
    entry_rows = soup.find_all("tr", class_="entry-row")
    print(f"Meet Program: Found {len(entry_rows)} entries")
    assert len(entry_rows) > 1000  # Champs has many entries

    # Check for team entries (which now use abbreviations)
    # The anonymized data usually has team codes like "TEAM1", "TEAM2" or "DP-TV"
    assert len(entry_rows) > 1000

    # Just verify some team info is present in the table
    teams = [row.find("td", class_="col-team").get_text(strip=True) for row in entry_rows]
    assert any(len(t) > 0 for t in teams)


@pytest.mark.skipif(not WEASY_AVAILABLE, reason="WeasyRenderer not available")
def test_lineups_has_data(champs_cache):
    converter = MmToJsonConverter(table_data=champs_cache)
    extractor = ReportDataExtractor(converter)

    # In anonymized data, we don't know the exact team name easily,
    # so we'll pick the first team that has entries.
    full_data = extractor.extract_meet_program_data()
    first_team = ""
    for g in full_data["groups"]:
        for h in g["heats"]:
            if h["sub_items"]:
                first_team = h["sub_items"][0]["team"]
                break
        if first_team:
            break

    assert first_team, "Should find at least one team in the meet"

    # Test a specific team lineup using the discovered team code
    report_data = extractor.extract_timer_sheets_data(team_filter=first_team)
    assert len(report_data["groups"]) > 0

    renderer = WeasyRenderer("dummy.pdf")
    html = renderer.render_to_html(report_data, "lineups.j2")

    soup = BeautifulSoup(html, "html.parser")
    entry_rows = soup.find_all("tr", class_="entry-row")
    print(f"Lineups ({first_team}): Found {len(entry_rows)} entries")
    assert len(entry_rows) > 0
    assert first_team in html


def test_legacy_pdf_renderer_has_data(champs_cache):
    """Verifies that the legacy PDFRenderer (ReportLab) actually builds data elements."""
    from mm_to_json.reporting.config import ReportConfig
    from mm_to_json.reporting.renderer import PDFRenderer

    converter = MmToJsonConverter(table_data=champs_cache)
    extractor = ReportDataExtractor(converter)
    report_data = extractor.extract_meet_program_data()

    config = ReportConfig(title="Test Program")
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        renderer = PDFRenderer(tmp.name, config)
        # We call the internal _build_elements to verify what's being added to the PDF
        elements = renderer._build_elements(report_data, 500)  # 500 is arbitrary width

        # Check that we have more than just the header (Header usually has title, meet_name, sub_title, and a spacer = 4 elements)
        # If the regression is present, elements will only have these header items.
        print(f"Legacy PDFRenderer: Built {len(elements)} elements")
        assert len(elements) > 10, "PDF elements list too short; items likely missing from report body"

        # Verify that we have some Table elements (where data rows live)
        from reportlab.platypus import Table

        tables = [e for e in elements if isinstance(e, Table)]
        assert len(tables) > 0, "No tables found in PDF elements; missing data rows"
