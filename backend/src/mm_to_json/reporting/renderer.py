import dataclasses
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, Frame, PageTemplate
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from .config import ReportConfig
import datetime

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
        self.styles.add(ParagraphStyle(
            "ReportTitle",
            parent=self.styles["Heading1"],
            fontName=self.config.header_style.font_name,
            fontSize=self.config.header_style.font_size,
            alignment=self.config.header_style.alignment,
            spaceAfter=self.config.header_style.space_after,
        ))
        self.styles.add(ParagraphStyle(
            "SubHeader",
            parent=self.styles["Normal"],
            fontName=self.config.subheader_style.font_name,
            fontSize=self.config.subheader_style.font_size,
            alignment=self.config.subheader_style.alignment,
            spaceAfter=self.config.subheader_style.space_after,
        ))
        
        # Group Header
        if self.config.main_group:
            self.styles.add(ParagraphStyle(
                 "GroupHeader",
                 parent=self.styles["Heading2"],
                 fontName=self.config.main_group.header_style.font_name,
                 fontSize=self.config.main_group.header_style.font_size,
                 alignment=self.config.main_group.header_style.alignment,
                 spaceAfter=self.config.main_group.header_style.space_after
            ))
        
        # Athlete Header (Bold)
        self.styles.add(ParagraphStyle(
            "AthleteHeader",
            parent=self.styles["Normal"],
            fontName="Helvetica-Bold",
        ))

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        # Footer (Date/Page) - Removed Hy-Tek
        canvas.setFont('Helvetica', 8)
        # Left side: Date? Or Org?
        canvas.drawString(0.5*inch, 0.5*inch, datetime.datetime.now().strftime('%m/%d/%Y'))
        # Right side: Page
        canvas.drawRightString(8.0*inch, 0.5*inch, f"Page {doc.page}")
        
        # Header Line
        canvas.line(0.5*inch, 10.2*inch, 8.0*inch, 10.2*inch)
        
        # Title on every page (Header)
        canvas.setFont('Helvetica-Bold', 12)
        canvas.drawCentredString(letter[0]/2.0, 10.5*inch, self.config.title)
        
        canvas.restoreState()

    def render(self, data: dict):
        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=letter,
            leftMargin=self.config.layout.margin_left * inch,
            rightMargin=self.config.layout.margin_right * inch,
            topMargin=self.config.layout.margin_top * inch, # Increased for header space
            bottomMargin=self.config.layout.margin_bottom * inch
        )

        elements = []
        
        # Title Block
        elements.append(Paragraph(self.config.title, self.styles["ReportTitle"]))
        if "meet_name" in data:
            elements.append(Paragraph(data["meet_name"], self.styles["SubHeader"]))
        if "sub_title" in data:
            elements.append(Paragraph(data["sub_title"], self.styles["SubHeader"]))
            
        elements.append(Spacer(1, 12))

        # Groups
        for i, group in enumerate(data.get("groups", [])):
            if self.config.main_group:
                # Group Header logic (e.g. "Team: Demon Piranhas")
                header_text = group.get("header", "")
                if header_text:
                    # Only break if NOT the first group/item
                    if self.config.main_group.new_page_per_group and i > 0:
                        elements.append(PageBreak())
                    elements.append(Paragraph(header_text, self.styles["GroupHeader"]))
            
            # Sub-items (e.g., Athletes)
            for item in group.get("items", []):
                item_elements = []
                
                # Item Header (e.g., Athlete Name block)
                item_header = item.get("header", "")
                if item_header:
                    item_elements.append(Paragraph(item_header, self.styles["AthleteHeader"]))
                
                # Item Details (e.g. Events Grid)
                # If 2-column layout requested
                sub_items = item.get("sub_items", [])
                
                if self.config.two_column_layout and not item.get("force_1col"):
                    # Convert flat list to 2-column tabular data
                    # Col spec: 9 cols with spacer in middle:
                    # [idx, desc, time, H/L, SPACER, idx, desc, time, H/L]
                    grid_data = []
                    item_row = []
                    mid_spacer = ""
                    
                    # Layout Logic: 
                    # sub_items is list of dicts: {idx, desc, time, heat_lane}
                    processed_items = []
                    for s in sub_items:
                        row = [
                            s.get("idx", ""),
                            s.get("desc", ""),
                            s.get("time", ""),
                            s.get("heat_lane", ""),
                        ]
                        processed_items.append(row)
                    
                    # Split into 2 columns
                    idx = 0
                    while idx < len(processed_items):
                        left = processed_items[idx]
                        right = ["", "", "", ""]
                        if idx + 1 < len(processed_items):
                            right = processed_items[idx+1]
                            
                        full_row = [
                            left[0], left[1], left[2], left[3],
                            mid_spacer,
                            right[0], right[1], right[2], right[3]
                        ]
                        grid_data.append(full_row)
                        idx += 2
                    
                    if grid_data:
                        # Define column widths
                        #  0.4, 2.2, 0.6, 0.4, 0.2, 0.4, 2.2, 0.6, 0.4
                        col_widths = [
                            0.35*inch, 2.0*inch, 0.6*inch, 0.4*inch, 
                            0.2*inch, 
                            0.35*inch, 2.0*inch, 0.6*inch, 0.4*inch
                        ]
                        t = Table(grid_data, colWidths=col_widths)
                        t.setStyle(TableStyle([
                            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                            ('FONTSIZE', (0,0), (-1,-1), 8),
                            ('ALIGN', (0,0), (0,-1), 'RIGHT'), # Idx
                            ('ALIGN', (1,0), (1,-1), 'LEFT'),  # Desc
                            ('ALIGN', (2,0), (2,-1), 'RIGHT'), # Time
                            ('ALIGN', (3,0), (3,-1), 'CENTER'),# H/L
                            
                            ('ALIGN', (5,0), (5,-1), 'RIGHT'), # Idx
                            ('ALIGN', (6,0), (6,-1), 'LEFT'),  # Desc
                            ('ALIGN', (7,0), (7,-1), 'RIGHT'), # Time
                            ('ALIGN', (8,0), (8,-1), 'CENTER'),# H/L
                            
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('LEFTPADDING', (0,0), (-1,-1), 2),
                        ]))
                        item_elements.append(t)
                else: 
                     # Single Column Layout (for Relays or non-2col config)
                     # Treat as 4-Column Table: [idx, desc, time, H/L]
                     grid_data = []
                     for s in sub_items:
                         row = [
                             s.get("idx", ""),
                             s.get("desc", ""),
                             s.get("time", ""),
                             s.get("heat_lane", ""),
                         ]
                         grid_data.append(row)

                     if grid_data:
                         # Full Width (approx 7.5 inch available?)
                         # idx (0.5), desc (5.0), time (1.0), HL (1.0) -> 7.5 Total
                         col_widths = [0.4*inch, 5.0*inch, 0.8*inch, 0.8*inch]
                         t = Table(grid_data, colWidths=col_widths)
                         t.setStyle(TableStyle([
                            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
                            ('FONTSIZE', (0,0), (-1,-1), 9), # Slightly larger for single col
                            ('ALIGN', (0,0), (0,-1), 'RIGHT'), # Idx
                            ('ALIGN', (1,0), (1,-1), 'LEFT'),  # Desc
                            ('ALIGN', (2,0), (2,-1), 'RIGHT'), # Time
                            ('ALIGN', (3,0), (3,-1), 'CENTER'),# H/L
                            ('VALIGN', (0,0), (-1,-1), 'TOP'),
                            ('LEFTPADDING', (0,0), (-1,-1), 4),
                         ]))
                         item_elements.append(t)
                         item_elements.append(Spacer(1, 4))


                # Use KeepTogether so athlete block doesn't split awkwardly
                elements.append(KeepTogether(item_elements))
                # Small spacer between items (athletes)
                elements.append(Spacer(1, 0)) 

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
