import copy
import datetime
import os
from typing import Any

import pytz
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
        render_data["playwright"] = True

        tz = pytz.timezone("America/Los_Angeles")
        # Format like MM: "2:17 PM 5/29/2026"
        render_data["generation_time"] = datetime.datetime.now(tz).strftime("%-I:%M %p %-m/%-d/%Y")

        return template.render(**render_data)

    def _write_pdf(self, html_content: str, meet_name: str = "", sub_title: str = ""):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # Launch browser (headless)
            browser = p.chromium.launch()
            page = browser.new_page()

            # Set content and wait for it to be ready
            # Optimized: 'load' is faster than 'networkidle' and sufficient for static content
            page.set_content(html_content, wait_until="load")

            # Native Header Template (Chromium specific)
            # Use data-passed titles or fallback
            display_meet = meet_name or "Meet Manager Tools"

            tz = pytz.timezone("America/Los_Angeles")
            gen_time = datetime.datetime.now(tz).strftime("%-I:%M %p %-m/%-d/%Y")

            header_html = f"""
            <div style="font-family: Helvetica, Arial, sans-serif; font-size: 8pt; width: 100%; margin: 0 0.5in; border-bottom: 0.5pt solid #000; padding-bottom: 3pt;">
                <div style="display: flex; justify-content: space-between; align-items: flex-end; width: 100%;">
                    <div style="text-align: left;">
                        <div style="font-weight: bold;">Tri-Valley Swim Lg. C</div>
                        <div>{display_meet}</div>
                    </div>
                    <div style="text-align: right;">
                        <div>HY-TEK's MEET MANAGER 7.0 - {gen_time}</div>
                        <div>Page <span class="pageNumber"></span></div>
                    </div>
                </div>
            </div>
            """

            # Generate PDF with native header/footer
            page.pdf(
                path=self.output_path,
                format="Letter",
                print_background=True,
                prefer_css_page_size=True,
                display_header_footer=True,
                header_template=header_html,
                footer_template='<div style="font-size: 8pt; width: 100%; text-align: center; margin: 0 0.5in;"></div>',
                margin={"top": "0.8in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"},
            )

            browser.close()

    def render_meet_program(self, data: dict[str, Any]):
        html_out = self._render_html(data, "meet_program.j2")
        if self.output_path.endswith(".pdf"):
            self._write_pdf(html_out, str(data.get("meet_name") or ""), str(data.get("sub_title") or ""))
        else:
            with open(self.output_path, "w") as f:
                f.write(html_out)
        return html_out

    def render_entries(self, data: dict[str, Any], template_name: str):
        html_out = self._render_html(data, template_name)
        if self.output_path.endswith(".pdf"):
            self._write_pdf(html_out, str(data.get("meet_name") or ""), str(data.get("sub_title") or ""))
        else:
            with open(self.output_path, "w") as f:
                f.write(html_out)
        return html_out

    def render_to_html(self, data: dict[str, Any], template_name: str = "meet_program.j2") -> str:
        """Returns the raw HTML for Web UI integration."""
        return self._render_html(data, template_name)
