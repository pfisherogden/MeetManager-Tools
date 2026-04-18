import copy
import datetime
import os
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class PlaywrightRenderer:
    """High-performance PDF renderer using Playwright (Chromium)."""

    def __init__(self, output_path: str):
        self.output_path = output_path
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir), autoescape=select_autoescape(["html", "xml"])
        )

    def _render_html(self, data: dict[str, Any], template_name: str) -> str:
        template = self.env.get_template(template_name)

        # Load CSS
        css_path = os.path.join(self.template_dir, "report_style.css")
        with open(css_path) as f:
            css_content = f.read()

        # Add metadata
        render_data = copy.copy(data)
        render_data["css_content"] = css_content
        import pytz

        tz = pytz.timezone("America/Los_Angeles")
        render_data["generation_time"] = datetime.datetime.now(tz).strftime("%I:%M %p %Y/%m/%d")

        return template.render(**render_data)

    def _write_pdf(self, html_content: str):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Launch browser (headless)
            browser = p.chromium.launch()
            page = browser.new_page()

            # Set content and wait for it to be ready
            page.set_content(html_content, wait_until="networkidle")

            # Generate PDF
            page.pdf(
                path=self.output_path,
                format="Letter",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=False,
                margin={"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"},
            )

            browser.close()

    def render_meet_program(self, data: dict[str, Any]):
        html_out = self._render_html(data, "meet_program.j2")
        self._write_pdf(html_out)
        return html_out

    def render_entries(self, data: dict[str, Any], template_name: str):
        html_out = self._render_html(data, template_name)
        self._write_pdf(html_out)
        return html_out

    def render_to_html(self, data: dict[str, Any], template_name: str = "meet_program.j2") -> str:
        """Returns the raw HTML for Web UI integration."""
        return self._render_html(data, template_name)
