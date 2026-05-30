import copy
import datetime
import os
from typing import Any

import pytz
from jinja2 import Environment, FileSystemLoader, select_autoescape


class WeasyRenderer:
    """Standard PDF renderer using WeasyPrint (Python-based)."""

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
        render_data["playwright"] = False

        tz = pytz.timezone("America/Los_Angeles")
        # Format like MM: "2:17 PM 5/29/2026"
        # %-m and %-d remove leading zeros on Linux/Unix
        render_data["generation_time"] = datetime.datetime.now(tz).strftime("%-I:%M %p %-m/%-d/%Y")

        return template.render(**render_data)

    def _write_pdf(self, html_content: str):
        from weasyprint import HTML

        html = HTML(string=html_content, base_url=self.template_dir)
        # Optimized for speed: skip font subsetting and keep only essential PDF optimization
        html.write_pdf(self.output_path, optimize_size=("images",))

    def render_meet_program(self, data: dict[str, Any]):
        html_out = self._render_html(data, "meet_program.j2")
        if self.output_path.endswith(".pdf"):
            self._write_pdf(html_out)
        else:
            with open(self.output_path, "w") as f:
                f.write(html_out)
        return html_out

    def render_entries(self, data: dict[str, Any], template_name: str):
        html_out = self._render_html(data, template_name)
        if self.output_path.endswith(".pdf"):
            self._write_pdf(html_out)
        else:
            with open(self.output_path, "w") as f:
                f.write(html_out)
        return html_out

    def render_to_html(self, data: dict[str, Any], template_name: str = "meet_program.j2") -> str:
        """Returns the raw HTML for Web UI integration."""
        return self._render_html(data, template_name)
