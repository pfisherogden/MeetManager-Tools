import datetime

from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


class ReportGenerator:
    def __init__(self, data, title="Meet Report"):
        self.data = data
        self.title = title
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()

    def _create_custom_styles(self):
        styles = {}
        styles["ReportTitle"] = ParagraphStyle(
            "ReportTitle",
            parent=self.styles["Heading1"],
            fontSize=16,
            spaceAfter=12,
            alignment=1,  # Center
        )
        styles["MeetInfo"] = ParagraphStyle(
            "MeetInfo", parent=self.styles["Normal"], fontSize=10, alignment=1, spaceAfter=6
        )
        styles["EventHeader"] = ParagraphStyle(
            "EventHeader",
            parent=self.styles["Heading2"],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            backgroundColor=colors.lightgrey,
        )
        return styles

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        # Footer
        footer = f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Page {doc.page}"
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(letter[0] / 2, 0.5 * inch, footer)
        canvas.restoreState()

    def generate_psych_sheet(self, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        # Title
        elements.append(Paragraph(self.title, self.custom_styles["ReportTitle"]))
        elements.append(Paragraph(self.data.get("meetName", "Unknown Meet"), self.custom_styles["MeetInfo"]))
        elements.append(
            Paragraph(
                f"{self.data.get('meetStart', '')} - {self.data.get('meetEnd', '')}", self.custom_styles["MeetInfo"]
            )
        )
        elements.append(Spacer(1, 0.2 * inch))

        for session in self.data.get("sessions", []):
            for event in session.get("events", []):
                elements.append(
                    Paragraph(f"Event {event['eventNum']}: {event['eventDesc']}", self.custom_styles["EventHeader"])
                )

                # Table for entries
                table_data = [["Lane", "Name", "Age", "Team", "Seed Time"]]
                # Sort entries by seed time for psych sheet if not already sorted
                entries = sorted(event.get("entries", []), key=lambda x: x.get("seedTime", "NT"))

                for entry in entries:
                    table_data.append(
                        [
                            entry.get("lane", ""),
                            entry.get("name", ""),
                            entry.get("age", ""),
                            entry.get("team", ""),
                            entry.get("seedTime", "NT"),
                        ]
                    )

                t = Table(table_data, colWidths=[0.5 * inch, 2.5 * inch, 0.5 * inch, 2.5 * inch, 1.0 * inch])
                t.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ]
                    )
                )
                elements.append(t)
                elements.append(Spacer(1, 0.1 * inch))

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def generate_meet_entries(self, output_path, team_filter=None):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        elements.append(Paragraph(self.title, self.custom_styles["ReportTitle"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Re-organize data by athlete/team
        records = []
        for session in self.data.get("sessions", []):
            for event in session.get("events", []):
                for entry in event.get("entries", []):
                    if team_filter and entry.get("team") != team_filter:
                        continue
                    records.append(
                        {
                            "team": entry.get("team"),
                            "name": entry.get("name"),
                            "age": entry.get("age"),
                            "eventNum": event["eventNum"],
                            "eventDesc": event["eventDesc"],
                            "seedTime": entry.get("seedTime"),
                        }
                    )

        # Group by team then name
        records.sort(key=lambda x: (x["team"], x["name"]))

        current_team = None
        current_athlete = None

        for rec in records:
            if rec["team"] != current_team:
                current_team = rec["team"]
                elements.append(Paragraph(f"Team: {current_team}", self.styles["Heading2"]))

            if rec["name"] != current_athlete:
                current_athlete = rec["name"]
                elements.append(Paragraph(f"{current_athlete} (Age: {rec['age']})", self.styles["Heading3"]))

            elements.append(
                Paragraph(f"Event {rec['eventNum']}: {rec['eventDesc']} - {rec['seedTime']}", self.styles["Normal"])
            )

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def generate_lineup_sheets(self, output_path):
        # Specific for parent volunteers: Grouped by Gender and Age
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        elements.append(Paragraph(self.title, self.custom_styles["ReportTitle"]))

        # We need to extract gender and age from the event description or data if available
        # MmToJsonConverter doesn't explicitly store gender/age in to_dict() for Event currently,
        # it puts it in eventDesc. We might need to adjust MmToJsonConverter or parse eventDesc.
        # For now, let's just group by event.

        for session in self.data.get("sessions", []):
            for event in session.get("events", []):
                elements.append(Paragraph(f"Lineup for {event['eventDesc']}", self.custom_styles["EventHeader"]))

                table_data = [["Heat", "Lane", "Name", "Team"]]
                entries = sorted(event.get("entries", []), key=lambda x: (x.get("heat", 0), x.get("lane", 0)))

                for entry in entries:
                    table_data.append(
                        [entry.get("heat", ""), entry.get("lane", ""), entry.get("name", ""), entry.get("team", "")]
                    )

                t = Table(table_data, colWidths=[0.5 * inch, 0.5 * inch, 3.0 * inch, 3.0 * inch])
                t.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 1, colors.black),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ]
                    )
                )
                elements.append(t)
                elements.append(Spacer(1, 0.2 * inch))

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def generate_meet_results(self, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        elements.append(Paragraph(self.title, self.custom_styles["ReportTitle"]))

        for session in self.data.get("sessions", []):
            for event in session.get("events", []):
                elements.append(Paragraph(f"Results: {event['eventDesc']}", self.custom_styles["EventHeader"]))

                table_data = [["Place", "Name", "Team", "Seed Time", "Final Time", "Points"]]
                # Results should have final time and place
                entries = sorted(event.get("entries", []), key=lambda x: x.get("place", 999))

                for entry in entries:
                    table_data.append(
                        [
                            entry.get("place", ""),
                            entry.get("name", ""),
                            entry.get("team", ""),
                            entry.get("seedTime", ""),
                            entry.get(
                                "psTime", entry.get("finalTime", "")
                            ),  # psTime is often used for prelim/final in some apps
                            entry.get("points", ""),
                        ]
                    )

                t = Table(
                    table_data, colWidths=[0.5 * inch, 2.0 * inch, 1.5 * inch, 1.0 * inch, 1.0 * inch, 0.5 * inch]
                )
                t.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ]
                    )
                )
                elements.append(t)
                elements.append(Spacer(1, 0.1 * inch))

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def generate_meet_program(self, output_path):
        from reportlab.lib.units import inch
        from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph

        # 2-column layout setup
        doc = BaseDocTemplate(output_path, pagesize=letter)
        # Margins
        left_margin = 0.5 * inch
        right_margin = 0.5 * inch
        top_margin = 0.5 * inch
        bottom_margin = 0.5 * inch

        frame_width = (letter[0] - left_margin - right_margin) / 2 - 0.1 * inch  # 0.1 inch gap
        frame_height = letter[1] - top_margin - bottom_margin

        frame1 = Frame(left_margin, bottom_margin, frame_width, frame_height, id="col1")
        frame2 = Frame(left_margin + frame_width + 0.2 * inch, bottom_margin, frame_width, frame_height, id="col2")

        template = PageTemplate(id="TwoCol", frames=[frame1, frame2], onPage=self._header_footer_program)
        doc.addPageTemplates([template])

        elements = []

        # Meet Header (Spans specific to this report type maybe? but constrained by columns)
        # If we want a full width header, we need a separate template.
        # For simplicity, we'll just put the title in the first column or assume the footer handles context.
        # But let's add a "Meet Program" title at the top of the flow.

        elements.append(Paragraph(self.title, self.custom_styles["ReportTitle"]))
        elements.append(Paragraph(self.data.get("meetName", "Unknown Meet"), self.custom_styles["MeetInfo"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Styles for Program
        style_event_title = ParagraphStyle(
            "ProgramEventTitle",
            parent=self.styles["Heading3"],
            fontSize=11,
            spaceBefore=6,
            spaceAfter=2,
            keepWithNext=True,
        )
        style_header_row = ParagraphStyle(
            "ProgramHeaderRow", parent=self.styles["Normal"], fontSize=8, fontName="Helvetica-Oblique", spaceAfter=2
        )
        style_entry = ParagraphStyle("ProgramEntry", parent=self.styles["Normal"], fontSize=9, leading=10)
        style_entry_bold = ParagraphStyle(
            "ProgramEntryBold", parent=self.styles["Normal"], fontSize=9, leading=10, fontName="Helvetica-Bold"
        )
        style_relay_swimmers = ParagraphStyle(
            "ProgramRelaySwimmers", parent=self.styles["Normal"], fontSize=8, leftIndent=12, leading=9
        )

        # Iterate Sessions
        for session in self.data.get("sessions", []):
            # Sort events
            events = sorted(session.get("events", []), key=lambda x: x["eventNum"])

            for event in events:
                # Event Block
                event_block = []

                # Title: Event # - Desc
                event_block.append(Paragraph(f"Event {event['eventNum']}  {event['eventDesc']}", style_event_title))

                entries = event.get("entries", [])
                if not entries:
                    event_block.append(Paragraph("No Entries", style_entry))
                    elements.append(KeepTogether(event_block))
                    elements.append(Spacer(1, 0.1 * inch))
                    continue

                # Determine columns based on Relay or Ind
                is_relay = any(e.get("isRelay", False) for e in entries)

                if is_relay:
                    event_block.append(Paragraph("Lane  Team           Relay    Seed Time", style_header_row))
                else:
                    event_block.append(
                        Paragraph("Lane  Name                         Age  Team      Seed Time", style_header_row)
                    )

                # Group by Heat
                # Sort first by heat, lane
                entries.sort(key=lambda x: (x.get("heat", 999), x.get("lane", 999)))

                current_heat = -1

                for entry in entries:
                    heat = entry.get("heat", 0)
                    if heat != current_heat:
                        current_heat = heat
                        event_block.append(Spacer(1, 4))
                        event_block.append(Paragraph(f"Heat {heat} of {event.get('numHeats', '?')}", style_entry_bold))

                    lane = entry.get("lane", "")
                    seed = entry.get("seedTime", "NT")
                    team = entry.get("team", "")

                    if is_relay:
                        relay_ltr = entry.get("relayLtr", "")
                        # Lane (2chars) Team (15chars) Relay(5) Seed
                        # We might utilize a small table for alignment or formatted string
                        # Using formatted string with non-breaking spaces is tricky in proportional fonts
                        # Table is better for alignment

                        # Relay Entry Main Line
                        # Just listing team and seed
                        # Format: Lane Team Relay Seed
                        line_text = f"<b>{lane}</b>   {team[:18]}   {relay_ltr}   {seed}"
                        event_block.append(Paragraph(line_text, style_entry))

                        # Swimmers
                        swimmers = entry.get("relaySwimmers", [])
                        if swimmers:
                            # 2 per line
                            # "1) Name 2) Name"
                            # "3) Name 4) Name"
                            row1 = []
                            row2 = []
                            for i, s_name in enumerate(swimmers):
                                if i < 2:
                                    row1.append(f"{i + 1}) {s_name}")
                                else:
                                    row2.append(f"{i + 1}) {s_name}")

                            if row1:
                                event_block.append(Paragraph(" ".join(row1), style_relay_swimmers))
                            if row2:
                                event_block.append(Paragraph(" ".join(row2), style_relay_swimmers))

                    else:  # Individual
                        entry.get("name", "")
                        entry.get("age", "")
                        # Format: Lane Name Age Team Seed
                        # Aligning with spaces is hard. Let's try to make a one-row table?
                        # Or just use tabs/spaces if font allows (Helvetica is proportional)
                        # Let's use a Table for strict alignment if performance allows,
                        # or just cleaner structured string if acceptable.
                        # Given user wanted "Lane, Name, Age, Team, Seed Time"

                        # Let's use a fixed width font or Table.
                        # Using Table for each entry is heavy.
                        # Maybe construct a Table for the whole heat?
                        pass

                # If individual, let's redo the loop to build a table per heat for better alignment
                if not is_relay:
                    # Re-group by heat locally
                    heats: dict[int, list[dict[str, Any]]] = {}
                    for e in entries:
                        h = e.get("heat", 0)
                        if h not in heats:
                            heats[h] = []
                        heats[h].append(e)

                    for h_num in sorted(heats.keys()):
                        event_block.append(Spacer(1, 4))
                        event_block.append(Paragraph(f"Heat {h_num}", style_entry_bold))

                        t_data = []
                        for e in heats[h_num]:
                            t_data.append(
                                [
                                    str(e.get("lane", "")),
                                    e.get("name", "")[:25],  # Truncate long names
                                    str(e.get("age", "")),
                                    e.get("team", "")[:15],
                                    e.get("seedTime", ""),
                                ]
                            )

                        # Table structure: Lane, Name, Age, Team, Seed
                        col_widths = [0.3 * inch, 1.6 * inch, 0.4 * inch, 0.8 * inch, 0.8 * inch]
                        t = Table(t_data, colWidths=col_widths)
                        t.setStyle(
                            TableStyle(
                                [
                                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                                    ("ALIGN", (0, 0), (0, -1), "CENTER"),  # Lane
                                    ("ALIGN", (2, 0), (2, -1), "CENTER"),  # Age
                                    ("ALIGN", (4, 0), (4, -1), "RIGHT"),  # Seed
                                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                                ]
                            )
                        )
                        event_block.append(t)

                elements.append(KeepTogether(event_block))
                elements.append(Spacer(1, 0.1 * inch))

        doc.build(elements)

    def _header_footer_program(self, canvas, doc):
        canvas.saveState()
        # Footer
        footer = f"{self.title} - Page {doc.page}"
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(letter[0] / 2, 0.5 * inch, footer)
        canvas.restoreState()
