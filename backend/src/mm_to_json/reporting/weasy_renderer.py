import copy
import datetime
import logging
import os
import sys
import threading
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from weasyprint.text.fonts import FontConfiguration

# Thread-local storage for FontConfiguration to prevent GLib/Pango thread-safety crashes
# while avoiding the overhead of rebuilding the font cache for every single report.
_thread_local = threading.local()


def get_font_config():
    if not hasattr(_thread_local, "font_config"):
        _thread_local.font_config = FontConfiguration()
    return _thread_local.font_config


class WeasyRenderer:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir), autoescape=select_autoescape(["html", "xml"])
        )

        # Ensure macOS libraries are found if running locally
        if os.name == "posix" and "darwin" in sys.platform:
            if "/opt/homebrew/lib" not in os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", ""):
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib:" + os.environ.get(
                    "DYLD_FALLBACK_LIBRARY_PATH", ""
                )

    def render_meet_program(self, data: dict[str, Any]):
        template = self.env.get_template("meet_program.j2")

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

        # Render HTML
        html_out = template.render(**render_data)

        # Aggressively silence noisy loggers right before rendering
        logging.getLogger("fontTools").setLevel(logging.ERROR)
        logging.getLogger("weasyprint").setLevel(logging.ERROR)

        # Convert to PDF using thread-local font config
        # optimize_size=('images',) disables slow font subsetting for massive speed gains
        HTML(string=html_out).write_pdf(self.output_path, font_config=get_font_config(), optimize_size=("images",))

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

        # Aggressively silence noisy loggers right before rendering
        logging.getLogger("fontTools").setLevel(logging.ERROR)
        logging.getLogger("weasyprint").setLevel(logging.ERROR)

        # Convert to PDF using thread-local font config
        # optimize_size=('images',) disables slow font subsetting
        HTML(string=html_out).write_pdf(self.output_path, font_config=get_font_config(), optimize_size=("images",))
        return html_out

    def render_to_html(self, data: dict[str, Any], template_name: str = "meet_program.j2") -> str:
        """Returns the raw HTML for Web UI integration."""
        template = self.env.get_template(template_name)

        css_path = os.path.join(self.template_dir, "report_style.css")
        with open(css_path) as f:
            css_content = f.read()

        render_data = copy.copy(data)
        render_data["css_content"] = css_content
        import pytz

        tz = pytz.timezone("America/Los_Angeles")
        render_data["generation_time"] = datetime.datetime.now(tz).strftime("%I:%M %p %Y/%m/%d")

        return template.render(**render_data)
