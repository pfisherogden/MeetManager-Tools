from dataclasses import dataclass, field
from typing import List, Optional

# Ensure mdb_writer can be imported
from . import mdb_writer


@dataclass
class Team:
    abbr: str
    name: str
    lsc: str = "US"
    team_id: Optional[int] = None

    def save(self, db):
        if self.team_id:
            # Check if exists or update logic?
            # For this simple ORM, we add.
            pass
        # mdb_writer returns ID.
        # But wait, mdb_writer.add_team argument order?
        # add_team(db, team_id, abbr, name, short_name=None, lsc="US")
        # We might need to handle generated ID.
        # The underlying add_team allows forcing ID or auto.

        # If ID is 0/None, we probably want auto ID.
        t_id = self.team_id if self.team_id is not None else 0
        new_id = mdb_writer.add_team(db, t_id, self.abbr, self.name, self.name, self.lsc)
        self.team_id = new_id
        return new_id


@dataclass
class Athlete:
    team_id: int  # FK
    first_name: str
    last_name: str
    gender: str
    age: int
    birth_date: Optional[str] = None  # Or date object
    athlete_id: Optional[int] = None

    def save(self, db):
        # add_athlete(db, ath_id, team_id, last, first, gender, age, ...)
        a_id = self.athlete_id if self.athlete_id is not None else 0
        new_id = mdb_writer.add_athlete(
            db, a_id, self.team_id, self.last_name, self.first_name, self.gender, self.age
        )
        self.athlete_id = new_id
        return new_id


@dataclass
class Session:
    num: int
    day: int
    start_time: str
    meet_id: int
    session_id: Optional[int] = None

    def save(self, db):
        # add_session(db, sess_num, day, start_time, meet_id, ...)
        # Note: add_session doesn't strictly return ID in current impl?
        # It adds to SESSIONS table. ID is usually Session #.
        mdb_writer.add_session(db, self.num, self.day, self.start_time, self.meet_id)
        self.session_id = self.num
        return self.num


@dataclass
class Event:
    number: int
    session_num: int
    distance: int
    stroke: int  # 1=Free, etc.
    gender: str
    meet_id: int
    age_low: int = 0
    age_high: int = 109
    is_relay: bool = False
    event_id: Optional[int] = None

    def save(self, db):
        # add_event(db, event_id, session_num, event_no, distance, stroke, gender, meet_id, ...)
        e_id = self.event_id if self.event_id is not None else self.number
        i_r = "R" if self.is_relay else "I"

        mdb_writer.add_event(
            db,
            e_id,
            self.session_num,
            self.number,
            self.distance,
            self.stroke,
            self.gender,
            self.meet_id,
            i_r=i_r,
            age_low=self.age_low,
            age_high=self.age_high,
        )
        # Note: add_event does not return generated ID currently in mdb_writer unless updated?
        # It updates MTEVENT. The PK is MtEvent (ID).
        # mdb_writer.add_event maps `event_id` to `MtEvent`.
        self.event_id = e_id
        return e_id


@dataclass
class Entry:
    athlete_id: int  # or Relay Team ID
    event_id: int
    team_id: int
    meet_id: int
    heat: int = 0
    lane: int = 0
    time: str = "NT"
    is_relay_entry: bool = False
    entry_id: Optional[int] = None

    def save(self, db):
        # add_entry(db, entry_id, ath_id, event_id, team_id, heat=0, lane=0,
        #           time=None, meet_id=0, i_r="I", ...)
        e_id = self.entry_id if self.entry_id is not None else 0
        i_r = "R" if self.is_relay_entry else "I"

        mdb_writer.add_entry(
            db,
            e_id,
            self.athlete_id,
            self.event_id,
            self.team_id,
            heat=self.heat,
            lane=self.lane,
            meet_id=self.meet_id,
            i_r=i_r,
        )
        # add_entry might not return ID?
        return e_id


@dataclass
class RelayTeam:
    meet_id: int
    team_id: int
    letter: str
    gender: str
    athletes: List[int] = field(default_factory=list)
    relay_id: Optional[int] = None

    def save(self, db):
        # add_relay_team(db, relay_id, meet_id, team_id, letter, gender, ...)
        r_id = self.relay_id if self.relay_id is not None else 0
        new_id = mdb_writer.add_relay_team(
            db, r_id, self.meet_id, self.team_id, self.letter, self.gender, athletes=self.athletes
        )
        self.relay_id = new_id
        return new_id
