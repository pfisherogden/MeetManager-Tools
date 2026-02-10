from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
import datetime

class ReportGenerator:
    def __init__(self, data, title="Meet Report"):
        self.data = data
        self.title = title
        self.styles = getSampleStyleSheet()
        self.custom_styles = self._create_custom_styles()

    def _create_custom_styles(self):
        styles = {}
        styles['ReportTitle'] = ParagraphStyle(
            'ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            alignment=1  # Center
        )
        styles['MeetInfo'] = ParagraphStyle(
            'MeetInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=1,
            spaceAfter=6
        )
        styles['EventHeader'] = ParagraphStyle(
            'EventHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            backgroundColor=colors.lightgrey
        )
        return styles

    def _header_footer(self, canvas, doc):
        canvas.saveState()
        # Footer
        footer = f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Page {doc.page}"
        canvas.setFont('Helvetica', 8)
        canvas.drawCentredString(letter[0]/2, 0.5*inch, footer)
        canvas.restoreState()

    def generate_psych_sheet(self, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        # Title
        elements.append(Paragraph(self.title, self.custom_styles['ReportTitle']))
        elements.append(Paragraph(self.data.get('meetName', 'Unknown Meet'), self.custom_styles['MeetInfo']))
        elements.append(Paragraph(f"{self.data.get('meetStart', '')} - {self.data.get('meetEnd', '')}", self.custom_styles['MeetInfo']))
        elements.append(Spacer(1, 0.2*inch))

        for session in self.data.get('sessions', []):
            for event in session.get('events', []):
                elements.append(Paragraph(f"Event {event['eventNum']}: {event['eventDesc']}", self.custom_styles['EventHeader']))
                
                # Table for entries
                table_data = [['Lane', 'Name', 'Age', 'Team', 'Seed Time']]
                # Sort entries by seed time for psych sheet if not already sorted
                entries = sorted(event.get('entries', []), key=lambda x: x.get('seedTime', 'NT'))
                
                for entry in entries:
                    table_data.append([
                        entry.get('lane', ''),
                        entry.get('name', ''),
                        entry.get('age', ''),
                        entry.get('team', ''),
                        entry.get('seedTime', 'NT')
                    ])

                t = Table(table_data, colWidths=[0.5*inch, 2.5*inch, 0.5*inch, 2.5*inch, 1.0*inch])
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                elements.append(t)
                elements.append(Spacer(1, 0.1*inch))

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def generate_meet_entries(self, output_path, team_filter=None):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        elements.append(Paragraph(self.title, self.custom_styles['ReportTitle']))
        elements.append(Spacer(1, 0.2*inch))

        # Re-organize data by athlete/team
        records = []
        for session in self.data.get('sessions', []):
            for event in session.get('events', []):
                for entry in event.get('entries', []):
                    if team_filter and entry.get('team') != team_filter:
                        continue
                    records.append({
                        'team': entry.get('team'),
                        'name': entry.get('name'),
                        'age': entry.get('age'),
                        'eventNum': event['eventNum'],
                        'eventDesc': event['eventDesc'],
                        'seedTime': entry.get('seedTime')
                    })

        # Group by team then name
        records.sort(key=lambda x: (x['team'], x['name']))

        current_team = None
        current_athlete = None
        
        for rec in records:
            if rec['team'] != current_team:
                current_team = rec['team']
                elements.append(Paragraph(f"Team: {current_team}", self.styles['Heading2']))
            
            if rec['name'] != current_athlete:
                current_athlete = rec['name']
                elements.append(Paragraph(f"{current_athlete} (Age: {rec['age']})", self.styles['Heading3']))

            elements.append(Paragraph(f"Event {rec['eventNum']}: {rec['eventDesc']} - {rec['seedTime']}", self.styles['Normal']))

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def generate_lineup_sheets(self, output_path):
        # Specific for parent volunteers: Grouped by Gender and Age
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []
        
        elements.append(Paragraph(self.title, self.custom_styles['ReportTitle']))
        
        # We need to extract gender and age from the event description or data if available
        # MmToJsonConverter doesn't explicitly store gender/age in to_dict() for Event currently,
        # it puts it in eventDesc. We might need to adjust MmToJsonConverter or parse eventDesc.
        # For now, let's just group by event.
        
        for session in self.data.get('sessions', []):
            for event in session.get('events', []):
                elements.append(Paragraph(f"Lineup for {event['eventDesc']}", self.custom_styles['EventHeader']))
                
                table_data = [['Heat', 'Lane', 'Name', 'Team']]
                entries = sorted(event.get('entries', []), key=lambda x: (x.get('heat', 0), x.get('lane', 0)))
                
                for entry in entries:
                    table_data.append([
                        entry.get('heat', ''),
                        entry.get('lane', ''),
                        entry.get('name', ''),
                        entry.get('team', '')
                    ])

                t = Table(table_data, colWidths=[0.5*inch, 0.5*inch, 3.0*inch, 3.0*inch])
                t.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 0.2*inch))

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)

    def generate_meet_results(self, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        elements.append(Paragraph(self.title, self.custom_styles['ReportTitle']))
        
        for session in self.data.get('sessions', []):
            for event in session.get('events', []):
                elements.append(Paragraph(f"Results: {event['eventDesc']}", self.custom_styles['EventHeader']))
                
                table_data = [['Place', 'Name', 'Team', 'Seed Time', 'Final Time', 'Points']]
                # Results should have final time and place
                entries = sorted(event.get('entries', []), key=lambda x: x.get('place', 999))
                
                for entry in entries:
                    table_data.append([
                        entry.get('place', ''),
                        entry.get('name', ''),
                        entry.get('team', ''),
                        entry.get('seedTime', ''),
                        entry.get('psTime', entry.get('finalTime', '')), # psTime is often used for prelim/final in some apps
                        entry.get('points', '')
                    ])

                t = Table(table_data, colWidths=[0.5*inch, 2.0*inch, 1.5*inch, 1.0*inch, 1.0*inch, 0.5*inch])
                t.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ]))
                elements.append(t)
                elements.append(Spacer(1, 0.1*inch))

        doc.build(elements, onFirstPage=self._header_footer, onLaterPages=self._header_footer)
