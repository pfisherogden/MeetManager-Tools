import asyncio
import datetime
import os
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape


class PlaywrightRenderer:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir), autoescape=select_autoescape(["html", "xml"])
        )

    async def _render_async(self, html_content: str):
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(html_content)
            # Wait for any dynamic content/fonts
            await page.wait_for_load_state(state="networkidle")
            await page.pdf(
                path=self.output_path,
                format="Letter",
                margin={"top": "0.5in", "bottom": "0.5in", "left": "0.5in", "right": "0.5in"},
                print_background=True,
            )
            await browser.close()

    def render_meet_program(self, data: dict[str, Any]):
        html_out = self.render_to_html(data)

        # Run async in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # If we are already in an event loop (e.g. running in some async servers)
            # This is tricky. For now we assume sync context or use a thread.
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor() as executor:
                executor.submit(asyncio.run, self._render_async(html_out)).result()
        else:
            asyncio.run(self._render_async(html_out))

        return html_out

    def render_to_html(self, data: dict[str, Any]) -> str:
        template = self.env.get_template("meet_program.html")

        css_path = os.path.join(self.template_dir, "report_style.css")
        with open(css_path) as f:
            css_content = f.read()

        data["css_content"] = css_content
        data["generation_time"] = datetime.datetime.now().strftime("%I:%M %p %m/%d/%Y")

        return template.render(**data)
