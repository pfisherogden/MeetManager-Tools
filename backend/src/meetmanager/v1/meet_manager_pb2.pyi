from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ReportType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    REPORT_TYPE_PSYCH_UNSPECIFIED: _ClassVar[ReportType]
    REPORT_TYPE_ENTRIES: _ClassVar[ReportType]
    REPORT_TYPE_LINEUPS: _ClassVar[ReportType]
    REPORT_TYPE_RESULTS: _ClassVar[ReportType]
    REPORT_TYPE_MEET_PROGRAM: _ClassVar[ReportType]
REPORT_TYPE_PSYCH_UNSPECIFIED: ReportType
REPORT_TYPE_ENTRIES: ReportType
REPORT_TYPE_LINEUPS: ReportType
REPORT_TYPE_RESULTS: ReportType
REPORT_TYPE_MEET_PROGRAM: ReportType

class GetMeetsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetMeetsResponse(_message.Message):
    __slots__ = ("meets",)
    MEETS_FIELD_NUMBER: _ClassVar[int]
    meets: _containers.RepeatedCompositeFieldContainer[Meet]
    def __init__(self, meets: _Optional[_Iterable[_Union[Meet, _Mapping]]] = ...) -> None: ...

class GetDashboardStatsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetDashboardStatsResponse(_message.Message):
    __slots__ = ("meet_count", "team_count", "athlete_count", "event_count")
    MEET_COUNT_FIELD_NUMBER: _ClassVar[int]
    TEAM_COUNT_FIELD_NUMBER: _ClassVar[int]
    ATHLETE_COUNT_FIELD_NUMBER: _ClassVar[int]
    EVENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    meet_count: int
    team_count: int
    athlete_count: int
    event_count: int
    def __init__(self, meet_count: _Optional[int] = ..., team_count: _Optional[int] = ..., athlete_count: _Optional[int] = ..., event_count: _Optional[int] = ...) -> None: ...

class GetTeamsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetTeamsResponse(_message.Message):
    __slots__ = ("teams",)
    TEAMS_FIELD_NUMBER: _ClassVar[int]
    teams: _containers.RepeatedCompositeFieldContainer[Team]
    def __init__(self, teams: _Optional[_Iterable[_Union[Team, _Mapping]]] = ...) -> None: ...

class GetTeamRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class GetTeamResponse(_message.Message):
    __slots__ = ("team",)
    TEAM_FIELD_NUMBER: _ClassVar[int]
    team: Team
    def __init__(self, team: _Optional[_Union[Team, _Mapping]] = ...) -> None: ...

class GetAthletesRequest(_message.Message):
    __slots__ = ("team_id",)
    TEAM_ID_FIELD_NUMBER: _ClassVar[int]
    team_id: str
    def __init__(self, team_id: _Optional[str] = ...) -> None: ...

class GetAthletesResponse(_message.Message):
    __slots__ = ("athletes",)
    ATHLETES_FIELD_NUMBER: _ClassVar[int]
    athletes: _containers.RepeatedCompositeFieldContainer[Athlete]
    def __init__(self, athletes: _Optional[_Iterable[_Union[Athlete, _Mapping]]] = ...) -> None: ...

class GetAthleteRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: int
    def __init__(self, id: _Optional[int] = ...) -> None: ...

class GetAthleteResponse(_message.Message):
    __slots__ = ("athlete",)
    ATHLETE_FIELD_NUMBER: _ClassVar[int]
    athlete: Athlete
    def __init__(self, athlete: _Optional[_Union[Athlete, _Mapping]] = ...) -> None: ...

class GetEventsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetEventsResponse(_message.Message):
    __slots__ = ("events",)
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedCompositeFieldContainer[Event]
    def __init__(self, events: _Optional[_Iterable[_Union[Event, _Mapping]]] = ...) -> None: ...

class ListDatasetsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListDatasetsResponse(_message.Message):
    __slots__ = ("datasets",)
    DATASETS_FIELD_NUMBER: _ClassVar[int]
    datasets: _containers.RepeatedCompositeFieldContainer[Dataset]
    def __init__(self, datasets: _Optional[_Iterable[_Union[Dataset, _Mapping]]] = ...) -> None: ...

class SetActiveDatasetRequest(_message.Message):
    __slots__ = ("filename",)
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    filename: str
    def __init__(self, filename: _Optional[str] = ...) -> None: ...

class SetActiveDatasetResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class UploadDatasetRequest(_message.Message):
    __slots__ = ("filename", "chunk")
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    CHUNK_FIELD_NUMBER: _ClassVar[int]
    filename: str
    chunk: bytes
    def __init__(self, filename: _Optional[str] = ..., chunk: _Optional[bytes] = ...) -> None: ...

class UploadDatasetResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class ClearDatasetRequest(_message.Message):
    __slots__ = ("filename",)
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    filename: str
    def __init__(self, filename: _Optional[str] = ...) -> None: ...

class ClearDatasetResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ClearAllDatasetsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ClearAllDatasetsResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetRelaysRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetRelaysResponse(_message.Message):
    __slots__ = ("relays",)
    RELAYS_FIELD_NUMBER: _ClassVar[int]
    relays: _containers.RepeatedCompositeFieldContainer[Relay]
    def __init__(self, relays: _Optional[_Iterable[_Union[Relay, _Mapping]]] = ...) -> None: ...

class GetScoresRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetScoresResponse(_message.Message):
    __slots__ = ("scores",)
    SCORES_FIELD_NUMBER: _ClassVar[int]
    scores: _containers.RepeatedCompositeFieldContainer[Score]
    def __init__(self, scores: _Optional[_Iterable[_Union[Score, _Mapping]]] = ...) -> None: ...

class GetEntriesRequest(_message.Message):
    __slots__ = ("athlete_id", "event_id")
    ATHLETE_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    athlete_id: str
    event_id: str
    def __init__(self, athlete_id: _Optional[str] = ..., event_id: _Optional[str] = ...) -> None: ...

class GetEntriesResponse(_message.Message):
    __slots__ = ("entries",)
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.RepeatedCompositeFieldContainer[Entry]
    def __init__(self, entries: _Optional[_Iterable[_Union[Entry, _Mapping]]] = ...) -> None: ...

class GetSessionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetSessionsResponse(_message.Message):
    __slots__ = ("sessions",)
    SESSIONS_FIELD_NUMBER: _ClassVar[int]
    sessions: _containers.RepeatedCompositeFieldContainer[Session]
    def __init__(self, sessions: _Optional[_Iterable[_Union[Session, _Mapping]]] = ...) -> None: ...

class GetAdminConfigRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetAdminConfigResponse(_message.Message):
    __slots__ = ("meet_name", "meet_description")
    MEET_NAME_FIELD_NUMBER: _ClassVar[int]
    MEET_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    meet_name: str
    meet_description: str
    def __init__(self, meet_name: _Optional[str] = ..., meet_description: _Optional[str] = ...) -> None: ...

class UpdateAdminConfigRequest(_message.Message):
    __slots__ = ("meet_name", "meet_description")
    MEET_NAME_FIELD_NUMBER: _ClassVar[int]
    MEET_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    meet_name: str
    meet_description: str
    def __init__(self, meet_name: _Optional[str] = ..., meet_description: _Optional[str] = ...) -> None: ...

class UpdateAdminConfigResponse(_message.Message):
    __slots__ = ("meet_name", "meet_description")
    MEET_NAME_FIELD_NUMBER: _ClassVar[int]
    MEET_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    meet_name: str
    meet_description: str
    def __init__(self, meet_name: _Optional[str] = ..., meet_description: _Optional[str] = ...) -> None: ...

class GetEventScoresRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetEventScoresResponse(_message.Message):
    __slots__ = ("event_scores",)
    EVENT_SCORES_FIELD_NUMBER: _ClassVar[int]
    event_scores: _containers.RepeatedCompositeFieldContainer[EventScore]
    def __init__(self, event_scores: _Optional[_Iterable[_Union[EventScore, _Mapping]]] = ...) -> None: ...

class Dataset(_message.Message):
    __slots__ = ("filename", "is_active", "last_modified")
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    LAST_MODIFIED_FIELD_NUMBER: _ClassVar[int]
    filename: str
    is_active: bool
    last_modified: str
    def __init__(self, filename: _Optional[str] = ..., is_active: bool = ..., last_modified: _Optional[str] = ...) -> None: ...

class Relay(_message.Message):
    __slots__ = ("id", "event_id", "team_id", "team_name", "leg1_name", "leg2_name", "leg3_name", "leg4_name", "seed_time", "final_time", "place", "event_name", "relay_letter", "heat", "lane")
    ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    TEAM_ID_FIELD_NUMBER: _ClassVar[int]
    TEAM_NAME_FIELD_NUMBER: _ClassVar[int]
    LEG1_NAME_FIELD_NUMBER: _ClassVar[int]
    LEG2_NAME_FIELD_NUMBER: _ClassVar[int]
    LEG3_NAME_FIELD_NUMBER: _ClassVar[int]
    LEG4_NAME_FIELD_NUMBER: _ClassVar[int]
    SEED_TIME_FIELD_NUMBER: _ClassVar[int]
    FINAL_TIME_FIELD_NUMBER: _ClassVar[int]
    PLACE_FIELD_NUMBER: _ClassVar[int]
    EVENT_NAME_FIELD_NUMBER: _ClassVar[int]
    RELAY_LETTER_FIELD_NUMBER: _ClassVar[int]
    HEAT_FIELD_NUMBER: _ClassVar[int]
    LANE_FIELD_NUMBER: _ClassVar[int]
    id: int
    event_id: int
    team_id: int
    team_name: str
    leg1_name: str
    leg2_name: str
    leg3_name: str
    leg4_name: str
    seed_time: str
    final_time: str
    place: int
    event_name: str
    relay_letter: str
    heat: int
    lane: int
    def __init__(self, id: _Optional[int] = ..., event_id: _Optional[int] = ..., team_id: _Optional[int] = ..., team_name: _Optional[str] = ..., leg1_name: _Optional[str] = ..., leg2_name: _Optional[str] = ..., leg3_name: _Optional[str] = ..., leg4_name: _Optional[str] = ..., seed_time: _Optional[str] = ..., final_time: _Optional[str] = ..., place: _Optional[int] = ..., event_name: _Optional[str] = ..., relay_letter: _Optional[str] = ..., heat: _Optional[int] = ..., lane: _Optional[int] = ...) -> None: ...

class Score(_message.Message):
    __slots__ = ("team_id", "team_name", "individual_points", "relay_points", "total_points", "rank", "meet_name")
    TEAM_ID_FIELD_NUMBER: _ClassVar[int]
    TEAM_NAME_FIELD_NUMBER: _ClassVar[int]
    INDIVIDUAL_POINTS_FIELD_NUMBER: _ClassVar[int]
    RELAY_POINTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_POINTS_FIELD_NUMBER: _ClassVar[int]
    RANK_FIELD_NUMBER: _ClassVar[int]
    MEET_NAME_FIELD_NUMBER: _ClassVar[int]
    team_id: int
    team_name: str
    individual_points: float
    relay_points: float
    total_points: float
    rank: int
    meet_name: str
    def __init__(self, team_id: _Optional[int] = ..., team_name: _Optional[str] = ..., individual_points: _Optional[float] = ..., relay_points: _Optional[float] = ..., total_points: _Optional[float] = ..., rank: _Optional[int] = ..., meet_name: _Optional[str] = ...) -> None: ...

class EventScore(_message.Message):
    __slots__ = ("event_id", "event_name", "entries")
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_NAME_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    event_id: int
    event_name: str
    entries: _containers.RepeatedCompositeFieldContainer[Entry]
    def __init__(self, event_id: _Optional[int] = ..., event_name: _Optional[str] = ..., entries: _Optional[_Iterable[_Union[Entry, _Mapping]]] = ...) -> None: ...

class Entry(_message.Message):
    __slots__ = ("id", "event_id", "athlete_id", "athlete_name", "team_id", "team_name", "seed_time", "final_time", "place", "event_name", "heat", "lane", "points")
    ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    ATHLETE_ID_FIELD_NUMBER: _ClassVar[int]
    ATHLETE_NAME_FIELD_NUMBER: _ClassVar[int]
    TEAM_ID_FIELD_NUMBER: _ClassVar[int]
    TEAM_NAME_FIELD_NUMBER: _ClassVar[int]
    SEED_TIME_FIELD_NUMBER: _ClassVar[int]
    FINAL_TIME_FIELD_NUMBER: _ClassVar[int]
    PLACE_FIELD_NUMBER: _ClassVar[int]
    EVENT_NAME_FIELD_NUMBER: _ClassVar[int]
    HEAT_FIELD_NUMBER: _ClassVar[int]
    LANE_FIELD_NUMBER: _ClassVar[int]
    POINTS_FIELD_NUMBER: _ClassVar[int]
    id: int
    event_id: int
    athlete_id: int
    athlete_name: str
    team_id: int
    team_name: str
    seed_time: str
    final_time: str
    place: int
    event_name: str
    heat: int
    lane: int
    points: float
    def __init__(self, id: _Optional[int] = ..., event_id: _Optional[int] = ..., athlete_id: _Optional[int] = ..., athlete_name: _Optional[str] = ..., team_id: _Optional[int] = ..., team_name: _Optional[str] = ..., seed_time: _Optional[str] = ..., final_time: _Optional[str] = ..., place: _Optional[int] = ..., event_name: _Optional[str] = ..., heat: _Optional[int] = ..., lane: _Optional[int] = ..., points: _Optional[float] = ...) -> None: ...

class Session(_message.Message):
    __slots__ = ("id", "meet_id", "name", "date", "warm_up_time", "start_time", "event_count", "session_num", "day")
    ID_FIELD_NUMBER: _ClassVar[int]
    MEET_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DATE_FIELD_NUMBER: _ClassVar[int]
    WARM_UP_TIME_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    EVENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    SESSION_NUM_FIELD_NUMBER: _ClassVar[int]
    DAY_FIELD_NUMBER: _ClassVar[int]
    id: str
    meet_id: str
    name: str
    date: str
    warm_up_time: str
    start_time: str
    event_count: int
    session_num: int
    day: int
    def __init__(self, id: _Optional[str] = ..., meet_id: _Optional[str] = ..., name: _Optional[str] = ..., date: _Optional[str] = ..., warm_up_time: _Optional[str] = ..., start_time: _Optional[str] = ..., event_count: _Optional[int] = ..., session_num: _Optional[int] = ..., day: _Optional[int] = ...) -> None: ...

class Meet(_message.Message):
    __slots__ = ("id", "name", "location", "start_date", "end_date", "status")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    location: str
    start_date: str
    end_date: str
    status: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., location: _Optional[str] = ..., start_date: _Optional[str] = ..., end_date: _Optional[str] = ..., status: _Optional[str] = ...) -> None: ...

class Team(_message.Message):
    __slots__ = ("id", "name", "code", "lsc", "city", "state", "athlete_count")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    LSC_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ATHLETE_COUNT_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    code: str
    lsc: str
    city: str
    state: str
    athlete_count: int
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., code: _Optional[str] = ..., lsc: _Optional[str] = ..., city: _Optional[str] = ..., state: _Optional[str] = ..., athlete_count: _Optional[int] = ...) -> None: ...

class Athlete(_message.Message):
    __slots__ = ("id", "first_name", "last_name", "gender", "age", "team_id", "team_name", "school_year", "reg_no", "date_of_birth")
    ID_FIELD_NUMBER: _ClassVar[int]
    FIRST_NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_NAME_FIELD_NUMBER: _ClassVar[int]
    GENDER_FIELD_NUMBER: _ClassVar[int]
    AGE_FIELD_NUMBER: _ClassVar[int]
    TEAM_ID_FIELD_NUMBER: _ClassVar[int]
    TEAM_NAME_FIELD_NUMBER: _ClassVar[int]
    SCHOOL_YEAR_FIELD_NUMBER: _ClassVar[int]
    REG_NO_FIELD_NUMBER: _ClassVar[int]
    DATE_OF_BIRTH_FIELD_NUMBER: _ClassVar[int]
    id: int
    first_name: str
    last_name: str
    gender: str
    age: int
    team_id: int
    team_name: str
    school_year: str
    reg_no: str
    date_of_birth: str
    def __init__(self, id: _Optional[int] = ..., first_name: _Optional[str] = ..., last_name: _Optional[str] = ..., gender: _Optional[str] = ..., age: _Optional[int] = ..., team_id: _Optional[int] = ..., team_name: _Optional[str] = ..., school_year: _Optional[str] = ..., reg_no: _Optional[str] = ..., date_of_birth: _Optional[str] = ...) -> None: ...

class Event(_message.Message):
    __slots__ = ("id", "gender", "distance", "stroke", "low_age", "high_age", "session", "status", "entry_count", "age_group")
    ID_FIELD_NUMBER: _ClassVar[int]
    GENDER_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    STROKE_FIELD_NUMBER: _ClassVar[int]
    LOW_AGE_FIELD_NUMBER: _ClassVar[int]
    HIGH_AGE_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ENTRY_COUNT_FIELD_NUMBER: _ClassVar[int]
    AGE_GROUP_FIELD_NUMBER: _ClassVar[int]
    id: int
    gender: str
    distance: int
    stroke: str
    low_age: int
    high_age: int
    session: int
    status: str
    entry_count: int
    age_group: str
    def __init__(self, id: _Optional[int] = ..., gender: _Optional[str] = ..., distance: _Optional[int] = ..., stroke: _Optional[str] = ..., low_age: _Optional[int] = ..., high_age: _Optional[int] = ..., session: _Optional[int] = ..., status: _Optional[str] = ..., entry_count: _Optional[int] = ..., age_group: _Optional[str] = ...) -> None: ...

class GenerateReportRequest(_message.Message):
    __slots__ = ("type", "title", "team_filter")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    TEAM_FILTER_FIELD_NUMBER: _ClassVar[int]
    type: ReportType
    title: str
    team_filter: str
    def __init__(self, type: _Optional[_Union[ReportType, str]] = ..., title: _Optional[str] = ..., team_filter: _Optional[str] = ...) -> None: ...

class GenerateReportResponse(_message.Message):
    __slots__ = ("success", "message", "pdf_content", "filename")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PDF_CONTENT_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    pdf_content: bytes
    filename: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ..., pdf_content: _Optional[bytes] = ..., filename: _Optional[str] = ...) -> None: ...
