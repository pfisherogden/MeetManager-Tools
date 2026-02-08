from .config import ReportConfig, TextStyle, GroupConfig, ColumnConfig, ReportLayout

# "Meet Entries" Configuration
MEET_ENTRIES_CONFIG = ReportConfig(
    title="Entries - All Events",
    layout=ReportLayout(
       page_size="Letter",
       margin_top=0.75, # Header needs space
       margin_bottom=0.5,
       margin_left=0.5,
       margin_right=0.5
    ),
    header_style=TextStyle(
        font_name="Helvetica-Bold",
        font_size=14,
        alignment=1, # Center
        space_after=4
    ),
    subheader_style=TextStyle(
        font_name="Helvetica",
        font_size=10,
        alignment=1, # Center
        space_after=4
    ),
    main_group=GroupConfig(
        group_by="team_name",
        header_style=TextStyle(
            font_name="Helvetica-Bold",
            font_size=12,
            alignment=0, # Left
            space_after=6
        ),
        page_break_after=False, # Athletes flow continuously unless Team breaks (maybe true?)
        new_page_per_group=True # Teams usually start on new pages in large meets? Usually continuous.
        # But for 'Champs Entries', teams might be separated. Let's assume continuous for density.
        # Actually reference "Champs Entries 2025 DP only.pdf" implies separate team.
        # But if running full report, probably continuous? 
        # Let's verify against reference visual...
        # Reference is "DP only", so only 1 team.
        # Let's set new_page_per_group=True to be safe for multi-team reports.
    ),
    item_group=GroupConfig(
         group_by="athlete_name",
         item_layout="2col_table"
    ),
    two_column_layout=True # Enable special 2-col logic in Renderer
)
