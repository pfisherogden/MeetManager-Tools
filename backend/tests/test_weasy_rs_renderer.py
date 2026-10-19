"""Unit and integration tests for the Rust `weasy-rs` PDF rendering engine."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pdfplumber
import pytest

from mm_to_json.mm_to_json import MmToJsonConverter
from mm_to_json.reporting.extractor import ReportDataExtractor
from mm_to_json.reporting.weasy_renderer import WeasyRenderer
from mm_to_json.rust_bridge import (
    is_rust_pdf_enabled,
    rust_render_pdf_bytes,
    rust_render_pdf_to_file,
)


def _sample_mdb_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "web-client" / "tests-e2e" / "Singers23.mdb"


def test_rust_pdf_engine_env_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify MM_PDF_ENGINE environment variable toggles between Rust and WeasyPrint."""
    monkeypatch.delenv("MM_PDF_ENGINE", raising=False)
    monkeypatch.delenv("MM_ENGINE", raising=False)
    monkeypatch.delenv("MM_DISABLE_RUST", raising=False)
    assert is_rust_pdf_enabled() is True

    monkeypatch.setenv("MM_PDF_ENGINE", "weasyprint")
    assert is_rust_pdf_enabled() is False

    monkeypatch.setenv("MM_PDF_ENGINE", "rust")
    assert is_rust_pdf_enabled() is True


def test_weasy_rs_drop_in_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify standalone `weasy_rs.HTML` drop-in API for bytes, Path, and BytesIO."""
    from weasy_rs import HTML

    monkeypatch.setenv("MM_ENGINE", "rust")
    monkeypatch.setenv("MM_PDF_ENGINE", "rust")
    monkeypatch.delenv("MM_DISABLE_RUST", raising=False)

    html_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page { size: letter; margin: 0.5in; margin-top: 1.25in; }
            #header { position: running(header); border-bottom: 1pt solid #000; }
            .content-container { column-count: 2; column-gap: 30pt; column-rule: 1pt solid #ddd; }
        </style>
    </head>
    <body>
        <div id="header">Meet Program Header - Page <span class="page-counter"></span></div>
        <div class="content-container">
            <div>Event 1 Girls 100 Yard Medley Relay</div>
        </div>
    </body>
    </html>
    """
    pdf_bytes = HTML(string=html_str).write_pdf()
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.4")

    out_pdf = tmp_path / "drop_in.pdf"
    HTML(string=html_str).write_pdf(out_pdf)
    assert out_pdf.exists()
    assert out_pdf.read_bytes() == pdf_bytes

    buf = io.BytesIO()
    HTML(string=html_str).write_pdf(buf)
    assert buf.getvalue() == pdf_bytes

    bridge_bytes = rust_render_pdf_bytes(html_str)
    assert bridge_bytes == pdf_bytes

    out_pdf2 = tmp_path / "bridge.pdf"
    assert rust_render_pdf_to_file(html_str, out_pdf2) is True
    assert out_pdf2.read_bytes() == pdf_bytes


def test_weasy_renderer_all_report_types_with_rust(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify WeasyRenderer produces valid multi-page PDFs with matching text for all report types."""
    mdb_path = _sample_mdb_path()
    if not mdb_path.exists():
        pytest.skip("Sample MDB not found")

    monkeypatch.setenv("MM_ENGINE", "rust")
    monkeypatch.setenv("MM_PDF_ENGINE", "rust")
    monkeypatch.delenv("MM_DISABLE_RUST", raising=False)
    conv = MmToJsonConverter(mdb_path=str(mdb_path))
    full_data = conv.convert()
    ext = ReportDataExtractor(conv, full_data=full_data)

    reports: list[tuple[str, str, dict[str, Any], str]] = [
        (
            "meet_program",
            "meet_program.j2",
            ext.extract_meet_program_data(report_title="Meet Program", columns_on_page=2, show_relay_swimmers=True),
            "Event",
        ),
        (
            "judge_sheets",
            "meet_program.j2",
            ext.extract_meet_program_data(
                report_title="S&T Judge Sheets",
                columns_on_page=2,
                show_dq_lines=True,
                show_relay_swimmers=True,
            ),
            "S&T Judge",
        ),
        (
            "psych_sheet",
            "psych_sheet.j2",
            ext.extract_psych_sheet_data(report_title="Psych Sheet - 2 Column"),
            "Event",
        ),
        (
            "entries_hytek",
            "entries_hytek.j2",
            ext.extract_meet_entries_data(report_title="Meet Entries"),
            "Entries",
        ),
        (
            "entries_club",
            "entries_club.j2",
            ext.extract_meet_entries_data(report_title="Club Entries"),
            "Entries",
        ),
        (
            "lineups",
            "lineups.j2",
            ext.extract_meet_entries_data(report_title="Meet Lineups"),
            "Lineups",
        ),
        (
            "results",
            "results.j2",
            ext.extract_results_data(report_title="Meet Results"),
            "Results",
        ),
        (
            "timer_sheets",
            "timer_sheets.j2",
            ext.extract_lane_timer_sheets_data(report_title="Lane Timer Sheets"),
            "Lane",
        ),
    ]

    for name, template_name, data, expected_keyword in reports:
        pdf_path = tmp_path / f"{name}.pdf"
        renderer = WeasyRenderer(str(pdf_path))
        if template_name == "meet_program.j2":
            renderer.render_meet_program(data)
        else:
            renderer.render_entries(data, template_name)

        assert pdf_path.exists(), f"{name} PDF was not created"
        assert pdf_path.stat().st_size > 1000, f"{name} PDF is unexpectedly small"

        with pdfplumber.open(str(pdf_path)) as pdf:
            assert len(pdf.pages) >= 1
            page1_text = pdf.pages[0].extract_text() or ""
            assert expected_keyword in page1_text, f"Missing {expected_keyword!r} in {name}"
            assert "Page 1" in page1_text
