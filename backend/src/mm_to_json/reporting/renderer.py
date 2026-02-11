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
                fontSize=12,  # User requested smaller font (was config default, likely 14+)
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

        # Header Line (Horizontal) - Optional, user asked for line UNDER event.
        # But this is page header.
        # canvas.line(0.5*inch, 10.2*inch, 8.0*inch, 10.2*inch)

        # Title on every page (Header)? No, title is in flow.
        # But if we want it on every page... NO, usually title is first page.
        # Unless config says so.
        # Current implementation puts title in `_build_elements`.

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
        # Adjust width calc if we want separator in the middle
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

            # Application of Vertical Separator between columns
            canvas.saveState()
            canvas.setStrokeColor(colors.black)
            canvas.setLineWidth(0.5)
            mid_x = page_width / 2.0
            # Draw line from just below top margin to just above bottom margin
            # Top of text area = page_height - margin_top
            # Bottom of text area = margin_bottom
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
            topMargin=self.config.layout.margin_top * inch,  # Increased for header space
            bottomMargin=self.config.layout.margin_bottom * inch,
        )
        # Pass full width availability (approx)
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

        # Groups (Events)
        groups = data.get("groups", [])
        if not groups:
            # Fallback for flat structure reports
            data.get("items", [])
            # Wrap as a single group? or iterate directly.
            # Let's assume standard reports use groups.
            pass

        for group in groups:
            # 1. Event Group Header (One per Event)
            # Use `header` from group dict.
            event_header = group.get("header", "")

            # Break page before new event if configured?
            # if self.config.main_group.new_page_per_group: ...

            if event_header:
                # Spacer between events
                elements.append(Spacer(1, 12))

                # Event Header Style
                # User wants: Font Size same as Heat (Heading4, ~8-10pt), Bold.
                # Bold Line underneath.
                evt_style = ParagraphStyle(
                    "EventHeader",
                    parent=self.styles["Heading4"],
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    spaceAfter=2,
                    keepWithNext=True,
                )
                elements.append(Paragraph(event_header, evt_style))

                # Bold Line
                elements.append(HRFlowable(width="100%", thickness=1, color=colors.black, spaceBefore=0, spaceAfter=2))

                # Inject Column Headers HERE (One time per Event)
                # Determine if Relay or Individual based on first entry of FIRST HEAT
                heats = group.get("items", [])
                is_relay = False
                if heats:
                    first_heat_entries = heats[0].get("sub_items", [])
                    if first_heat_entries:
                        first_entry = first_heat_entries[0]
                        if "swimmers" in first_entry or first_entry.get("is_relay"):
                            is_relay = True

                # Define Column Widths (Must match entry table widths)
                aw = available_width
                if is_relay:
                    # Relay Headers: Lane(12%), Team, Relay(10%), Time(20%)
                    w_lane = 0.12 * aw
                    w_relay = 0.1 * aw
                    w_time = 0.2 * aw
                    w_team = aw - w_lane - w_relay - w_time
                    h_data = [["Lane", "Team", "Relay", "Seed Time"]]
                    t_cols = [w_lane, w_team, w_relay, w_time]
                else:
                    # Individual Headers: Lane(12%), Name, Age(10%), Team(20%), Time(20%)
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
                            ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),  # Time Right
                            ("LEFTPADDING", (0, 0), (-1, -1), 2),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.black),
                        ]
                    )
                )
                elements.append(t_head)
                # elements.append(Spacer(1, 2))

            # 2. Iterate Heats (Items)
            for item in group.get("items", []):
                item_elements = []

                # Heat Header
                item_header = item.get("header", "")
                if item_header:
                    # Custom Style for Heat Header: 10pt Bold (Same as Event)
                    heat_style = ParagraphStyle(
                        "HeatHeader",
                        parent=self.styles["Heading4"],
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        spaceAfter=1,
                        keepWithNext=True,
                    )
                    item_elements.append(Paragraph(item_header, heat_style))

                # 3. Entries (Sub Items)
                sub_items = item.get("sub_items", [])

                if sub_items:
                    is_relay_heat = "swimmers" in sub_items[0]
                    if is_relay_heat:
                        t = self._create_relay_table(sub_items, available_width)
                    else:
                        t = self._create_individual_table(sub_items, available_width)

                    if t:
                        item_elements.append(t)
                        item_elements.append(Spacer(1, 4))

                elements.append(KeepTogether(item_elements))

        return elements

    def _create_relay_table(self, sub_items, aw):
        """Creates a single Table for a heat of relay entries."""
        w_lane = 0.12 * aw
        w_relay = 0.1 * aw
        w_time = 0.2 * aw
        w_team = aw - w_lane - w_relay - w_time

        table_data = []
        table_styles = [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]

        for i, s in enumerate(sub_items):
            # --- ROW A: Main Entry Data ---
            row_a = [
                s.get("lane", ""),
                s.get("team", ""),
                s.get("relay_ltr", ""),
                s.get("time", ""),
            ]
            table_data.append(row_a)

            row_a_idx = i * 2
            table_styles.extend(
                [
                    ("ALIGN", (0, row_a_idx), (0, row_a_idx), "CENTER"),  # Lane
                    ("ALIGN", (1, row_a_idx), (1, row_a_idx), "LEFT"),  # Team
                    ("ALIGN", (2, row_a_idx), (2, row_a_idx), "CENTER"),  # Relay
                    ("ALIGN", (3, row_a_idx), (3, row_a_idx), "RIGHT"),  # Time
                    ("BOTTOMPADDING", (0, row_a_idx), (-1, row_a_idx), 0),
                ]
            )

            # --- ROW B: Swimmers (Nested Table) ---
            swimmers = s.get("swimmers", [])
            t_inner = ""
            if swimmers:
                inner_data = []
                formatted = [f"{idx + 1}) {name}" for idx, name in enumerate(swimmers)]
                for k in range(0, len(formatted), 2):
                    row = [formatted[k]]
                    if k + 1 < len(formatted):
                        row.append(formatted[k + 1])
                    else:
                        row.append("")
                    inner_data.append(row)

                w_inner_total = w_team + w_relay + w_time
                t_inner = Table(inner_data, colWidths=[w_inner_total * 0.5, w_inner_total * 0.5])
                t_inner.setStyle(
                    TableStyle(
                        [
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                            ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ]
                    )
                )

            row_b = ["", t_inner, "", ""]
            table_data.append(row_b)

            row_b_idx = row_a_idx + 1
            table_styles.extend(
                [
                    ("SPAN", (1, row_b_idx), (3, row_b_idx)),
                    ("TOPPADDING", (0, row_b_idx), (-1, row_b_idx), 0),
                    ("BOTTOMPADDING", (0, row_b_idx), (-1, row_b_idx), 8),
                ]
            )

        t = Table(table_data, colWidths=[w_lane, w_team, w_relay, w_time])
        t.setStyle(TableStyle(table_styles))
        return t

    def _create_individual_table(self, sub_items, aw):
        """Creates a single Table for a heat of individual entries."""
        w_lane = 0.12 * aw
        w_age = 0.1 * aw
        w_time = 0.2 * aw
        w_team = 0.2 * aw
        w_name = aw - w_lane - w_age - w_team - w_time

        grid_data = []
        for s in sub_items:
            grid_data.append(
                [
                    s.get("lane", ""),
                    s.get("name", ""),
                    s.get("age", ""),
                    s.get("team", ""),
                    s.get("time", ""),
                ]
            )

        t = Table(grid_data, colWidths=[w_lane, w_name, w_age, w_team, w_time])
        t.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("ALIGN", (2, 0), (2, -1), "CENTER"),
                    ("ALIGN", (3, 0), (3, -1), "LEFT"),
                    ("ALIGN", (4, 0), (4, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        return t
