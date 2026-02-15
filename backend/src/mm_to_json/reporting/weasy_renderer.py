import copy
import datetime
import os
import sys
from typing import Any

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


class WeasyRenderer:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

        # Ensure macOS libraries are found if running locally
        if os.name == "posix" and "darwin" in sys.platform:
            if "/opt/homebrew/lib" not in os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", ""):
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib:" + os.environ.get(
                    "DYLD_FALLBACK_LIBRARY_PATH", ""
                )

    def render_meet_program(self, data: dict[str, Any]):
        template = self.env.get_template("meet_program.html")

        # Load CSS
        css_path = os.path.join(self.template_dir, "report_style.css")
        with open(css_path) as f:
            css_content = f.read()

        # Add metadata (do not overwrite if already present, but WeasyRenderer usually generates it)
        render_data = copy.copy(data)
        render_data["css_content"] = css_content
        import pytz

        tz = pytz.timezone("America/Los_Angeles")
        render_data["generation_time"] = datetime.datetime.now(tz).strftime("%I:%M %p %Y/%m/%d")

        # Render HTML
        html_out = template.render(**render_data)

        # Convert to PDF
        HTML(string=html_out).write_pdf(self.output_path)

        return html_out

    def render_entries(self, data: dict[str, Any], template_name: str):
        template = self.env.get_template(template_name)

        css_path = os.path.join(self.template_dir, "report_style.css")
        with open(css_path) as f:
            css_content = f.read()

        render_data = copy.copy(data)
        render_data["css_content"] = css_content
        import pytz

        tz = pytz.timezone("America/Los_Angeles")
        render_data["generation_time"] = datetime.datetime.now(tz).strftime("%I:%M %p %Y/%m/%d")

        html_out = template.render(**render_data)
        HTML(string=html_out).write_pdf(self.output_path)
        return html_out

    def render_to_html(self, data: dict[str, Any]) -> str:
        """Returns the raw HTML for Web UI integration."""
        template = self.env.get_template("meet_program.html")

        css_path = os.path.join(self.template_dir, "report_style.css")
        with open(css_path) as f:
            css_content = f.read()

        render_data = copy.copy(data)
        render_data["css_content"] = css_content
        import pytz

        tz = pytz.timezone("America/Los_Angeles")
        render_data["generation_time"] = datetime.datetime.now(tz).strftime("%I:%M %p %Y/%m/%d")

        return template.render(**render_data)
