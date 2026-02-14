from .config import GroupConfig, ReportConfig, ReportLayout, TextStyle

# "Meet Entries" Configuration
MEET_ENTRIES_CONFIG = ReportConfig(
    title="Entries - All Events",
    layout=ReportLayout(
        page_size="Letter",
        margin_top=0.75,
        margin_bottom=0.5,
        margin_left=0.5,
        margin_right=0.5,
    ),
    header_style=TextStyle(
        font_name="Helvetica-Bold",
        font_size=14,
        alignment=1,
        space_after=4,
    ),
    subheader_style=TextStyle(
        font_name="Helvetica",
        font_size=10,
        alignment=1,
        space_after=4,
    ),
    main_group=GroupConfig(
        group_by="team_name",
        header_style=TextStyle(
            font_name="Helvetica-Bold",
            font_size=12,
            alignment=0,
            space_after=6,
        ),
        page_break_after=False,
        new_page_per_group=True,
    ),
    item_group=GroupConfig(group_by="athlete_name", item_layout="2col_table"),
    two_column_layout=True,
)

# "Psych Sheet" Configuration
PSYCH_SHEET_CONFIG = ReportConfig(
    title="Psych Sheet",
    layout=ReportLayout(
        page_size="Letter",
        margin_top=0.75,
        margin_bottom=0.5,
        margin_left=0.5,
        margin_right=0.5,
        columns_on_page=2,
    ),
    header_style=TextStyle(
        font_name="Helvetica-Bold",
        font_size=14,
        alignment=1,
        space_after=4,
    ),
    subheader_style=TextStyle(
        font_name="Helvetica",
        font_size=10,
        alignment=1,
        space_after=4,
    ),
    main_group=GroupConfig(
        group_by="event_no",
        header_style=TextStyle(
            font_name="Helvetica-Bold",
            font_size=10,
            alignment=0,
            space_after=2,
        ),
    ),
    item_group=GroupConfig(group_by="entries", item_layout="table"),
    two_column_layout=True,
)

# "Meet Program" Configuration
MEET_PROGRAM_CONFIG = ReportConfig(
    title="Meet Program",
    layout=ReportLayout(
        page_size="Letter",
        margin_top=0.75,
        margin_bottom=0.5,
        margin_left=0.5,
        margin_right=0.5,
        columns_on_page=2,
    ),
    header_style=TextStyle(
        font_name="Helvetica-Bold",
        font_size=14,
        alignment=1,
        space_after=4,
    ),
    subheader_style=TextStyle(
        font_name="Helvetica",
        font_size=10,
        alignment=1,
        space_after=4,
    ),
    main_group=GroupConfig(
        group_by="event_no",
        header_style=TextStyle(
            font_name="Helvetica-Bold",
            font_size=10,
            alignment=0,
            space_after=2,
        ),
    ),
    item_group=GroupConfig(group_by="heat_num", item_layout="table"),
    two_column_layout=True,
)

# "Timer Sheets" Configuration
TIMER_SHEETS_CONFIG = ReportConfig(
    title="Timer Sheets",
    layout=ReportLayout(
        page_size="Letter",
        margin_top=0.75,
        margin_bottom=0.5,
        margin_left=0.5,
        margin_right=0.5,
    ),
    header_style=TextStyle(
        font_name="Helvetica-Bold",
        font_size=14,
        alignment=1,
        space_after=12,
    ),
    subheader_style=TextStyle(
        font_name="Helvetica",
        font_size=12,
        alignment=1,
        space_after=12,
    ),
    main_group=GroupConfig(
        group_by="event_heat",
        header_style=TextStyle(
            font_name="Helvetica-Bold",
            font_size=12,
            alignment=0,
            space_after=8,
        ),
        new_page_per_group=True,
    ),
)

# "Results Report" Configuration
RESULTS_REPORT_CONFIG = ReportConfig(
    title="Meet Results",
    layout=ReportLayout(
        page_size="Letter",
        margin_top=0.75,
        margin_bottom=0.5,
        margin_left=0.5,
        margin_right=0.5,
    ),
    header_style=TextStyle(
        font_name="Helvetica-Bold",
        font_size=14,
        alignment=1,
        space_after=4,
    ),
    subheader_style=TextStyle(
        font_name="Helvetica",
        font_size=10,
        alignment=1,
        space_after=4,
    ),
    main_group=GroupConfig(
        group_by="event_no",
        header_style=TextStyle(
            font_name="Helvetica-Bold",
            font_size=10,
            alignment=0,
            space_after=2,
        ),
    ),
)
