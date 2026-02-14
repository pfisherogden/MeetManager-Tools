import logging
from typing import Any

from .reporting.extractor import ReportDataExtractor
from .reporting.renderer import PDFRenderer
from .reporting.report_definitions import (
    MEET_ENTRIES_CONFIG,
    MEET_PROGRAM_CONFIG,
    PSYCH_SHEET_CONFIG,
    RESULTS_REPORT_CONFIG,
    TIMER_SHEETS_CONFIG,
)

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, converter, title=None):
        # We now take the CONVERTER itself to use the extractor
        self.converter = converter
        self.extractor = ReportDataExtractor(converter)
        self.custom_title = title

    def generate_psych_sheet(self, output_path):
        logger.info(f"Generating Psych Sheet to {output_path}")
        data = self.extractor.extract_psych_sheet_data()
        config = PSYCH_SHEET_CONFIG
        if self.custom_title:
            config.title = self.custom_title
        renderer = PDFRenderer(output_path, config)
        renderer.render(data)

    def generate_meet_entries(self, output_path, team_filter=None):
        logger.info(f"Generating Meet Entries to {output_path} (Filter: {team_filter})")
        data = self.extractor.extract_meet_entries_data(team_filter=team_filter)
        config = MEET_ENTRIES_CONFIG
        if self.custom_title:
            config.title = self.custom_title
        renderer = PDFRenderer(output_path, config)
        renderer.render(data)

    def generate_meet_program(self, output_path):
        logger.info(f"Generating Meet Program to {output_path}")
        data = self.extractor.extract_meet_program_data()
        config = MEET_PROGRAM_CONFIG
        if self.custom_title:
            config.title = self.custom_title
        renderer = PDFRenderer(output_path, config)
        renderer.render(data)

    def generate_timer_sheets(self, output_path):
        logger.info(f"Generating Timer Sheets to {output_path}")
        data = self.extractor.extract_timer_sheets_data()
        config = TIMER_SHEETS_CONFIG
        if self.custom_title:
            config.title = self.custom_title
        renderer = PDFRenderer(output_path, config)
        renderer.render(data)

    def generate_meet_results(self, output_path):
        logger.info(f"Generating Meet Results to {output_path}")
        data = self.extractor.extract_results_data()
        config = RESULTS_REPORT_CONFIG
        if self.custom_title:
            config.title = self.custom_title
        renderer = PDFRenderer(output_path, config)
        renderer.render(data)

    # Legacy method names if needed
    def generate_lineup_sheets(self, output_path):
        self.generate_meet_program(output_path)
