from dataclasses import dataclass, field


@dataclass
class TextStyle:
    font_name: str = "Helvetica"
    font_size: int = 10
    leading: int = 12
    alignment: int = 0  # 0=Left, 1=Center, 2=Right
    space_after: int = 0
    space_before: int = 0
    bg_color: str | None = None
    text_color: str = "black"


@dataclass
class ColumnConfig:
    header: str
    width: float  # in inches
    alignment: int = 0  # 0=Left, 1=Center, 2=Right
    data_key: str = ""  # Key in the data dict to populate this column
    style: TextStyle = field(default_factory=TextStyle)


@dataclass
class GroupConfig:
    group_by: str  # Data key to group by (e.g., "team_name")
    header_style: TextStyle = field(default_factory=lambda: TextStyle(font_size=12, space_after=6))
    item_layout: str = "block"  # "block" (vertical stack), "table" (grid), "2col_table"
    page_break_after: bool = False
    new_page_per_group: bool = False


@dataclass
class ReportLayout:
    page_size: str = "Letter"
    orientation: str = "Portrait"
    margin_top: float = 0.5
    margin_bottom: float = 0.5
    margin_left: float = 0.5
    margin_right: float = 0.5
    columns_on_page: int = 1


@dataclass
class ReportConfig:
    title: str
    layout: ReportLayout = field(default_factory=ReportLayout)
    header_style: TextStyle = field(default_factory=lambda: TextStyle(font_size=14, alignment=1, space_after=12))
    subheader_style: TextStyle = field(default_factory=lambda: TextStyle(font_size=10, alignment=1, space_after=6))

    # Main grouping (e.g., Team)
    main_group: GroupConfig | None = None

    # Item grouping (e.g., Athlete within Team)
    item_group: GroupConfig | None = None

    # Detailed data columns (e.g., Events within Athlete)
    columns: list[ColumnConfig] = field(default_factory=list)

    # Special flags
    two_column_layout: bool = False  # e.g., for 2-column event list
