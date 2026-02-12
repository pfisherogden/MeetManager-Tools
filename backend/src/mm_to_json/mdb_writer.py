import logging
import os

import jpype
import jpype.imports
from jpype.types import *  # noqa: F403

logger = logging.getLogger(__name__)


def get_classpath():
    """Returns the classpath list for Jackcess."""
    lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
    jars = [os.path.join(lib_dir, f) for f in os.listdir(lib_dir) if f.endswith(".jar")]
    return jars


def ensure_jvm_started():
    """Starts the JVM if not already started."""
    if jpype.isJVMStarted():
        return

    logger.debug("Starting JVM...")

    jars = get_classpath()
    if not jars:
        raise RuntimeError("No libraries found in lib/. Cannot start JVM for Jackcess.")

    classpath = os.pathsep.join(jars)
    logger.debug(f"Classpath: {classpath}")
    
    jvm_path = jpype.getDefaultJVMPath()
    logger.debug(f"JVM Path: {jvm_path}")

    # -Djava.class.path must be set at startup
    jpype.startJVM(jvm_path, "-Djava.class.path=" + classpath)
    logger.debug("JVM started successfully.")


def open_db(mdb_path):
    """
    Opens the Access Database using Jackcess and returns the Database object.
    Caller is responsible for calling db.close() or try/finally.
    """
    ensure_jvm_started()

    from com.healthmarketscience.jackcess import DatabaseBuilder
    from java.io import File

    logger.debug(f"Opening file via Jackcess: {mdb_path}")
    # Open in read/write mode (default)
    # Jackcess 3.x+ usually auto-detects version and handling
    # If the DB has no password (which verified tests show), simple open works.
    db = DatabaseBuilder.open(File(mdb_path))
    logger.debug("Database opened successfully via Jackcess.")
    return db


def _add_row(db, table_name, **kwargs):
    """
    Helper to add a row to a table.
    """
    table = db.getTable(table_name)
    if table is None:
        raise ValueError(f"Table {table_name} not found")

    # Jackcess addRow takes object array or map?
    # .addRow(Object... row) order must match columns?
    # .addRowFromMap(Map<String, Object> row) is safer.

    # We need to construct a Java Map
    from java.util import HashMap

    row_map = HashMap()
    for k, v in kwargs.items():
        row_map.put(k, v)

    table.addRowFromMap(row_map)
    return True


# --- API Methods ---


def add_session(db, session_num, day, start_time, meet_id, am_pm=False, max_ind=3, max_rel=3):
    """
    Adds a session to SESSIONS table.
    """
    # Note: Types must match Jackcess expectations (Java types mostly auto-converted by JPype)
    # BYTE fields need simple ints in Python usually works.
    _add_row(
        db,
        "SESSIONS",
        SESSION=session_num,
        MEETID=meet_id,
        DAY=day,
        STARTTIME=str(start_time),
        AMPM=am_pm,
        MAXIND=max_ind,
        MAXREL=max_rel,
        MAXCOMBINED=max_ind + max_rel,
        SESSX="",  # Assuming empty string ok
    )


def add_team(db, team_id, abbr, name, short_name="", lsc="AB", t_type="AGE"):
    """
    Adds a team to TEAM table.
    team_id: LONG (PK)
    """
    _add_row(
        db,
        "TEAM",
        Team=team_id,
        TCode=abbr,
        TName=name,
        Short=short_name if short_name else name,
        LSC=lsc,
        TType=t_type,
        Regn="U",  # Default region - Max 1 char
        TM50=False,
    )

    # Retrieve ID
    from java.util import HashMap

    criteria = HashMap()
    criteria.put("TCode", abbr)
    criteria.put("TName", name)

    t = db.getTable("TEAM")
    c = t.getDefaultCursor()
    if c.findFirstRow(criteria):
        return c.getCurrentRow().get("Team")
    return team_id


def add_athlete(db, athlete_id, team_id, first, last, gender, age, school_year=""):
    """
    Adds an athlete to ATHLETE table.
    athlete_id: LONG (PK)
    """
    _add_row(
        db,
        "ATHLETE",
        Athlete=athlete_id,
        Team1=team_id,
        First=first,
        Last=last,
        Sex=gender,
        Age=age,
        Class=school_year,
        Citizen="USA",
        Inactive=False,
    )

    # Retrieve ID
    from java.util import HashMap

    criteria = HashMap()
    criteria.put("First", first)
    criteria.put("Last", last)
    criteria.put("Team1", team_id)

    t = db.getTable("ATHLETE")
    c = t.getDefaultCursor()
    if c.findFirstRow(criteria):
        return c.getCurrentRow().get("Athlete")
    return athlete_id


def add_event(
    db,
    event_id,
    session_num,
    event_no,
    distance,
    stroke,
    gender,
    meet_id,
    i_r="I",
    age_low=0,
    age_high=0,
):
    """
    Adds an event to MTEVENT table.
    event_id: LONG (PK) - MtEvent
    event_no: INT - MtEv (The displayed number)
    stroke: INT (1=Free, 2=Back, 3=Breast, 4=Fly, 5=IM)
    """
    # Create Lo_Hi value (e.g. 1112 for 11-12)
    # Simple logic for now
    lo_hi = 0
    if age_low > 0 or age_high > 0:
        # Heuristic mentioned in code: 1112
        if age_low < 10 and age_high < 10:
            lo_hi = (age_low * 10) + age_high  # e.g. 8 * 10 + 9 ??? No wait inspector said INT.
            # mm_to_json.py logic:
            # if len=3 (910) -> 9-10
            # if len=4 (1112) -> 11-12
            # 8&U -> 8 ?
        else:
            lo_hi = int(f"{age_low}{age_high}")

    _add_row(
        db,
        "MTEVENT",
        MtEvent=event_id,
        Meet=meet_id,
        Session=session_num,
        MtEv=event_no,
        Distance=distance,
        Stroke=stroke,
        Sex=gender,
        I_R=i_r,
        Lo_Hi=lo_hi,
        Division="",  # Optional
        EventType="L",  # L=Standard?
    )

    # Retrieve the actual ID (in case of AutoNumber)
    # Search by unique combo: Meet, Session, MtEv
    from java.util import HashMap

    criteria = HashMap()
    criteria.put("Meet", meet_id)
    criteria.put("Session", session_num)
    criteria.put("MtEv", event_no)

    t = db.getTable("MTEVENT")
    c = t.getDefaultCursor()
    if c.findFirstRow(criteria):
        return c.getCurrentRow().get("MtEvent")
    return event_id  # Fallback if not found (unlikely)


def add_entry(db, entry_id, athlete_id, event_id, team_id, heat, lane, meet_id, score=0, i_r="I"):
    """
    Adds an entry to ENTRY table.
    entry_id: LONG
    score: LONG (used for Time/Seed sometimes? or 0)
    """
    _add_row(
        db,
        "ENTRY",
        Entry=entry_id,
        Meet=meet_id,
        Athlete=athlete_id,
        MtEvent=event_id,
        Team=team_id,
        HEAT=heat,
        LANE=lane,
        Score=score,
        I_R=i_r,
        Course="Y",  # Yards default
    )


def add_relay_team(db, relay_id, meet_id, team_id, letter, gender, age_range_code=0, athletes=None):
    """
    Adds a relay team to RELAY table.
    athletes: List of 4 (or up to 8) athlete IDs.
    """
    row_data = {
        "RELAY": relay_id,
        "MEET": meet_id,
        "TEAM": team_id,
        "LETTER": letter,
        "SEX": gender,
        "AGE_RANGE": age_range_code,
        "LO_HI": age_range_code,  # Often duplicate?
    }

    if athletes:
        for i, ath_id in enumerate(athletes):
            if i >= 8:
                break
            # Col name is ATH(1), ATH(2)...
            row_data[f"ATH({i + 1})"] = ath_id

    _add_row(db, "RELAY", **row_data)

    # Retrieve ID
    from java.util import HashMap

    criteria = HashMap()
    criteria.put("MEET", meet_id)
    criteria.put("TEAM", team_id)
    criteria.put("LETTER", letter)
    criteria.put("SEX", gender)
    # Could check Age Range too

    t = db.getTable("RELAY")
    c = t.getDefaultCursor()
    if c.findFirstRow(criteria):
        return c.getCurrentRow().get("RELAY")
    return relay_id
