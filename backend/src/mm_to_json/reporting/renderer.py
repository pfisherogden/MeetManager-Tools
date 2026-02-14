import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .config import ReportConfig


class PDFRenderer:
    def __init__(self, output_path: str, config: ReportConfig):
        self.output_path = output_path
        self.config = config
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        # Override Normal style if needed
        self.styles["Normal"].fontName = "Helvetica"
        self.styles["Normal"].fontSize = 9

        # Add custom styles based on config
        self.styles.add(
            ParagraphStyle(
                "ReportTitle",
                parent=self.styles["Heading1"],
                fontName=self.config.header_style.font_name,
                fontSize=12,
                alignment=self.config.header_style.alignment,
                spaceAfter=self.config.header_style.space_after,
            )
        )
        self.styles.add(
            ParagraphStyle(
                "SubHeader",
                parent=self.styles["Normal"],
                fontName=self.config.subheader_style.font_name,
                fontSize=self.config.subheader_style.font_size,
                alignment=self.config.subheader_style.alignment,
                spaceAfter=self.config.subheader_style.space_after,
            )
        )

        # Group Header
        if self.config.main_group:
            self.styles.add(
                ParagraphStyle(
                    "GroupHeader",
                    parent=self.styles["Heading2"],
                    fontName=self.config.main_group.header_style.font_name,
                    fontSize=self.config.main_group.header_style.font_size,
                    alignment=self.config.main_group.header_style.alignment,
                    spaceAfter=self.config.main_group.header_style.space_after,
                )
            )

        # Athlete Header (Bold)
        self.styles.add(
            ParagraphStyle(
                "AthleteHeader",
                parent=self.styles["Normal"],
                fontName="Helvetica-Bold",
            )
        )

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        # Footer (Date/Page)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(0.5 * inch, 0.5 * inch, datetime.datetime.now().strftime("%m/%d/%Y"))
        canvas.drawRightString(8.0 * inch, 0.5 * inch, f"Page {doc.page}")
        canvas.restoreState()

    def render(self, data: dict):
        if self.config.layout.columns_on_page > 1:
            self._render_multi_col(data)
        else:
            self._render_single_col(data)

    def _render_multi_col(self, data: dict):
        # Create Frame(s) for columns
        margin_left = self.config.layout.margin_left * inch
        margin_right = self.config.layout.margin_right * inch
        margin_top = self.config.layout.margin_top * inch
        margin_bottom = self.config.layout.margin_bottom * inch

        page_width, page_height = letter
        printable_height = page_height - margin_top - margin_bottom

        col_count = self.config.layout.columns_on_page
        gutter = 0.2 * inch
        printable_width = page_width - margin_left - margin_right
        col_width = (printable_width - (col_count - 1) * gutter) / col_count

        frames = []
        for i in range(col_count):
            left_offset = margin_left + i * (col_width + gutter)
            f = Frame(left_offset, margin_bottom, col_width, printable_height, id=f"col{i}", showBoundary=0)
            frames.append(f)

        doc = BaseDocTemplate(
            self.output_path,
            pagesize=letter,
            leftMargin=margin_left,
            rightMargin=margin_right,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
        )

        def on_page(canvas, doc):
            self._header_footer(canvas, doc)
            canvas.saveState()
            canvas.setStrokeColor(colors.black)
            canvas.setLineWidth(0.5)
            mid_x = page_width / 2.0
            canvas.line(mid_x, margin_bottom, mid_x, page_height - margin_top)
            canvas.restoreState()

        template = PageTemplate(id="TwoCol", frames=frames, onPage=on_page)
        doc.addPageTemplates([template])

        elements = self._build_elements(data, col_width)
        doc.build(elements)

    def _render_single_col(self, data: dict):
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=letter,
            leftMargin=self.config.layout.margin_left * inch,
            rightMargin=self.config.layout.margin_right * inch,
            topMargin=self.config.layout.margin_top * inch,
            bottomMargin=self.config.layout.margin_bottom * inch,
        )
        max_width = letter[0] - (self.config.layout.margin_left + self.config.layout.margin_right) * inch
        elements = self._build_elements(data, max_width)
        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def _build_elements(self, data: dict, available_width: float):
        elements = []

        # Title Block
        elements.append(Paragraph(self.config.title, self.styles["ReportTitle"]))
        if "meet_name" in data:
            elements.append(Paragraph(data["meet_name"], self.styles["SubHeader"]))
        if "sub_title" in data:
            elements.append(Paragraph(data["sub_title"], self.styles["SubHeader"]))

        elements.append(Spacer(1, 12))

        groups = data.get("groups", [])
        for group in groups:
            event_header = group.get("header", "")
            if event_header:
                elements.append(Spacer(1, 12))
                evt_style = ParagraphStyle(
                    "EventHeader",
                    parent=self.styles["Heading4"],
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    spaceAfter=2,
                    keepWithNext=True,
                )
                elements.append(Paragraph(event_header, evt_style))
                elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=0, spaceAfter=2))

                # Column Headers
                heats = group.get("items", [])
                is_relay = False
                if heats:
                    first_heat_entries = heats[0].get("sub_items", [])
                    if first_heat_entries:
                        first_entry = first_heat_entries[0]
                        if "swimmers" in first_entry or first_entry.get("is_relay"):
                            is_relay = True

                aw = available_width
                if self.config.title == "Psych Sheet":
                    w_rank = 0.08 * aw
                    w_age = 0.08 * aw
                    w_time = 0.2 * aw
                    w_team = 0.2 * aw
                    w_name = aw - w_rank - w_age - w_team - w_time
                    h_data = [["Rank", "Name", "Age", "Team", "Seed Time"]]
                    t_cols = [w_rank, w_name, w_age, w_team, w_time]
                elif self.config.title == "Timer Sheets":
                    w_lane = 0.1 * aw
                    w_seed = 0.15 * aw
                    w_team = 0.15 * aw
                    w_box = 0.3 * aw
                    w_name = aw - w_lane - w_seed - w_team - w_box
                    h_data = [["Lane", "Name", "Team", "Seed", "Actual Time"]]
                    t_cols = [w_lane, w_name, w_team, w_seed, w_box]
                elif self.config.title == "Meet Results":
                    w_place = 0.08 * aw
                    w_age = 0.08 * aw
                    w_time = 0.15 * aw
                    w_seed = 0.15 * aw
                    w_team = 0.15 * aw
                    w_name = aw - w_place - w_age - w_team - w_seed - w_time
                    h_data = [["Place", "Name", "Age", "Team", "Seed Time", "Final Time"]]
                    t_cols = [w_place, w_name, w_age, w_team, w_seed, w_time]
                elif is_relay:
                    w_lane = 0.12 * aw
                    w_relay = 0.1 * aw
                    w_time = 0.2 * aw
                    w_team = aw - w_lane - w_relay - w_time
                    h_data = [["Lane", "Team", "Relay", "Seed Time"]]
                    t_cols = [w_lane, w_team, w_relay, w_time]
                else:
                    w_lane = 0.12 * aw
                    w_age = 0.1 * aw
                    w_time = 0.2 * aw
                    w_team = 0.2 * aw
                    w_name = aw - w_lane - w_age - w_team - w_time
                    h_data = [["Lane", "Name", "Age", "Team", "Seed Time"]]
                    t_cols = [w_lane, w_name, w_age, w_team, w_time]

                t_head = Table(h_data, colWidths=t_cols)
                t_head.setStyle(
                    TableStyle(
                        [
                            ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, -1), 8),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                            ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.black),
                        ]
                    )
                )
                elements.append(t_head)

            for item in group.get("items", []):
                item_elements = []
                item_header = item.get("header", "")
                if item_header:
                    heat_style = ParagraphStyle(
                        "HeatHeader",
                        parent=self.styles["Heading4"],
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        spaceAfter=1,
                        keepWithNext=True,
                    )
                    item_elements.append(Paragraph(item_header, heat_style))

                sub_items = item.get("sub_items", [])
                if sub_items:
                    is_relay_heat = "swimmers" in sub_items[0]
                    if self.config.title == "Psych Sheet":
                        t = self._create_psych_table(sub_items, available_width)
                    elif self.config.title == "Timer Sheets":
                        t = self._create_timer_table(sub_items, available_width)
                    elif self.config.title == "Meet Results":
                        t = self._create_results_table(sub_items, available_width)
                    elif is_relay_heat:
                        t = self._create_relay_table(sub_items, available_width)
                    else:
                        t = self._create_individual_table(sub_items, available_width)

                    if t:
                        item_elements.append(t)
                        item_elements.append(Spacer(1, 4))

                elements.append(KeepTogether(item_elements))

        return elements

    def _create_psych_table(self, sub_items, aw):
        w_rank = 0.08 * aw
        w_age = 0.08 * aw
        w_time = 0.2 * aw
        w_team = 0.2 * aw
        w_name = aw - w_rank - w_age - w_team - w_time
        grid_data = []
        for s in sub_items:
            grid_data.append([s.get("rank", ""), s.get("name", ""), s.get("age", ""), s.get("team", ""), s.get("time", "")])
        t = Table(grid_data, colWidths=[w_rank, w_name, w_age, w_team, w_time])
        t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (0, 0), (0, -1), "RIGHT"), ("ALIGN", (1, 0), (1, -1), "LEFT"), ("ALIGN", (2, 0), (2, -1), "CENTER"), ("ALIGN", (3, 0), (3, -1), "LEFT"), ("ALIGN", (4, 0), (4, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return t

    def _create_timer_table(self, sub_items, aw):
        w_lane = 0.1 * aw
        w_seed = 0.15 * aw
        w_team = 0.15 * aw
        w_box = 0.3 * aw
        w_name = aw - w_lane - w_seed - w_team - w_box
        grid_data = []
        for s in sub_items:
            grid_data.append([s.get("lane", ""), s.get("name", ""), s.get("team", ""), s.get("seed", ""), ""])
        t = Table(grid_data, colWidths=[w_lane, w_name, w_team, w_seed, w_box], rowHeights=40)
        t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (0, -1), 14), ("FONTSIZE", (1, 0), (1, -1), 12), ("FONTSIZE", (2, 0), (3, -1), 10), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("ALIGN", (0, 0), (0, -1), "CENTER"), ("ALIGN", (4, 0), (4, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("GRID", (4, 0), (4, -1), 2, colors.black), ("LINEBELOW", (0, 0), (-2, -1), 0.5, colors.grey)]))
        return t

    def _create_results_table(self, sub_items, aw):
        w_place = 0.08 * aw
        w_age = 0.08 * aw
        w_time = 0.15 * aw
        w_seed = 0.15 * aw
        w_team = 0.15 * aw
        w_name = aw - w_place - w_age - w_team - w_seed - w_time
        grid_data = []
        for s in sub_items:
            grid_data.append([s.get("place", ""), s.get("name", ""), s.get("age", ""), s.get("team", ""), s.get("seed", ""), s.get("time", "")])
        t = Table(grid_data, colWidths=[w_place, w_name, w_age, w_team, w_seed, w_time])
        t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 9), ("ALIGN", (0, 0), (0, -1), "RIGHT"), ("ALIGN", (1, 0), (1, -1), "LEFT"), ("ALIGN", (2, 0), (2, -1), "CENTER"), ("ALIGN", (3, 0), (3, -1), "LEFT"), ("ALIGN", (4, 0), (4, -1), "RIGHT"), ("ALIGN", (5, 0), (5, -1), "RIGHT"), ("FONTNAME", (5, 0), (5, -1), "Helvetica-Bold"), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return t

    def _create_relay_table(self, sub_items, aw):
        w_lane = 0.12 * aw
        w_relay = 0.1 * aw
        w_time = 0.2 * aw
        w_team = aw - w_lane - w_relay - w_time
        table_data = []
        table_styles = [("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 10), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]
        for i, s in enumerate(sub_items):
            row_a = [s.get("lane", ""), s.get("team", ""), s.get("relay_ltr", ""), s.get("time", "")]
            table_data.append(row_a)
            row_a_idx = i * 2
            table_styles.extend([("ALIGN", (0, row_a_idx), (0, row_a_idx), "CENTER"), ("ALIGN", (1, row_a_idx), (1, row_a_idx), "LEFT"), ("ALIGN", (2, row_a_idx), (2, row_a_idx), "CENTER"), ("ALIGN", (3, row_a_idx), (3, row_a_idx), "RIGHT"), ("BOTTOMPADDING", (0, row_a_idx), (-1, row_a_idx), 0)])
            swimmers = s.get("swimmers", [])
            t_inner = ""
            if swimmers:
                inner_data = []
                formatted = [f"{idx + 1}) {name}" for idx, name in enumerate(swimmers)]
                for k in range(0, len(formatted), 2):
                    row = [formatted[k]]
                    if k + 1 < len(formatted): row.append(formatted[k+1])
                    else: row.append("")
                    inner_data.append(row)
                w_inner_total = w_team + w_relay + w_time
                t_inner = Table(inner_data, colWidths=[w_inner_total * 0.5, w_inner_total * 0.5])
                t_inner.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 10)]))
            row_b = ["", t_inner, "", ""]
            table_data.append(row_b)
            row_b_idx = row_a_idx + 1
            table_styles.extend([("SPAN", (1, row_b_idx), (3, row_b_idx)), ("TOPPADDING", (0, row_b_idx), (-1, row_b_idx), 0), ("BOTTOMPADDING", (0, row_b_idx), (-1, row_b_idx), 8)])
        t = Table(table_data, colWidths=[w_lane, w_team, w_relay, w_time])
        t.setStyle(TableStyle(table_styles))
        return t

    def _create_individual_table(self, sub_items, aw):
        w_lane = 0.12 * aw
        w_age = 0.1 * aw
        w_time = 0.2 * aw
        w_team = 0.2 * aw
        w_name = aw - w_lane - w_age - w_team - w_time
        grid_data = []
        for s in sub_items:
            grid_data.append([s.get("lane", ""), s.get("name", ""), s.get("age", ""), s.get("team", ""), s.get("time", "")])
        t = Table(grid_data, colWidths=[w_lane, w_name, w_age, w_team, w_time])
        t.setStyle(TableStyle([("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 10), ("ALIGN", (0, 0), (0, -1), "CENTER"), ("ALIGN", (1, 0), (1, -1), "LEFT"), ("ALIGN", (2, 0), (2, -1), "CENTER"), ("ALIGN", (3, 0), (3, -1), "LEFT"), ("ALIGN", (4, 0), (4, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("TOPPADDING", (0, 0), (-1, -1), 1)]))
        return t
