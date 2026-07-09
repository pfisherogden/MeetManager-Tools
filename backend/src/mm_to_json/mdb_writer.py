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


def get_potential_jvm_paths(local_jre: str, system: str) -> list[str]:
    """Returns a list of potential paths to the JVM library inside a local JRE folder."""
    potentials = []
    if system == "Darwin":
        potentials = [
            os.path.join(local_jre, "Contents", "Home", "lib", "server", "libjvm.dylib"),
            os.path.join(local_jre, "lib", "server", "libjvm.dylib"),
        ]
    elif system == "Windows":
        potentials = [
            os.path.join(local_jre, "bin", "server", "jvm.dll"),
            os.path.join(local_jre, "bin", "client", "jvm.dll"),
        ]
    else:
        potentials = [
            os.path.join(local_jre, "lib", "server", "libjvm.so"),
            os.path.join(local_jre, "lib", "client", "libjvm.so"),
        ]
    return potentials


def sanitize_windows_path(path: str) -> str:
    """Strips the Windows long path prefix (\\?\\) if present, as JNI loaders often fail to parse it."""
    if os.name == "nt" and path.startswith("\\\\?\\"):
        if path.startswith("\\\\?\\UNC\\"):
            return "\\\\" + path[8:]
        return path[4:]
    return path


def ensure_jvm_started():
    """Starts the JVM if not already started."""
    if jpype.isJVMStarted():
        return

    logger.info("Initializing Java Virtual Machine (JVM) startup sequence...")

    # Discover JVM path
    jvm_path = None

    # 1. Try resolving via environment variable from Tauri first
    import datetime
    import sys

    local_jre = None
    tauri_resource_dir = os.getenv("TAURI_RESOURCE_DIR")
    if tauri_resource_dir:
        tauri_jre_binaries = os.path.join(tauri_resource_dir, "binaries", "jre")
        if os.path.exists(tauri_jre_binaries):
            local_jre = tauri_jre_binaries
            logger.info(f"Resolved JRE via TAURI_RESOURCE_DIR binaries: {local_jre}")
        else:
            tauri_jre = os.path.join(tauri_resource_dir, "jre")
            if os.path.exists(tauri_jre):
                local_jre = tauri_jre
                logger.info(f"Resolved JRE via TAURI_RESOURCE_DIR direct: {local_jre}")

    # 2. Fallback to frozen executable location path discovery
    if not local_jre and getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        tauri_jre_binaries = os.path.join(exe_dir, "binaries", "jre")
        if os.path.exists(tauri_jre_binaries):
            local_jre = tauri_jre_binaries
            logger.info(f"Resolved JRE in Tauri binaries resources: {local_jre}")
        else:
            tauri_jre = os.path.join(exe_dir, "jre")
            if os.path.exists(tauri_jre):
                local_jre = tauri_jre
                logger.info(f"Resolved JRE in Tauri resources: {local_jre}")

    if not local_jre:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_jre = os.path.join(base_dir, "jre")
        logger.info(f"Fallback JRE directory checked: {local_jre} (exists={os.path.exists(local_jre)})")

    if os.path.exists(local_jre):
        import platform

        system = platform.system()
        potentials = get_potential_jvm_paths(local_jre, system)
        logger.info(f"Scanning {len(potentials)} potential JVM library paths in JRE...")

        for potential in potentials:
            if os.path.exists(potential):
                jvm_path = potential
                logger.info(f"Found JRE JVM library at: {jvm_path}")
                break

    # 2. Fallback to system default if no local JRE
    if not jvm_path:
        logger.info("Local JRE not found or missing JVM library, attempting system default JVM lookup...")
        try:
            jvm_path = jpype.getDefaultJVMPath()
            logger.info(f"Found system default JVM path: {jvm_path}")
        except Exception as e:
            logger.warning(f"Failed to resolve default system JVM path: {e}")

    if not jvm_path:
        logger.error("Startup Failure: JRE JVM library could not be located on the system.")
        raise RuntimeError("Java Runtime (JRE) not found. Please install Java or run download_libs.py.")

    jars = get_classpath()
    if not jars:
        logger.error("Startup Failure: No Jackcess JAR libraries found in lib/ directory.")
        raise RuntimeError("No libraries found in lib/. Cannot start JVM for Jackcess.")

    jvm_path = sanitize_windows_path(jvm_path)
    sanitized_jars = [sanitize_windows_path(jar) for jar in jars]
    classpath = os.pathsep.join(sanitized_jars)
    logger.info(f"Classifying classpath with {len(jars)} JAR libraries...")
    logger.info(f"Target JVM Location: {jvm_path}")

    # Hardening JRE sibling dependency resolution on Windows
    if os.name == "nt":
        # Strip long path prefix if present (e.g. \\?\) to avoid LoadLibrary confusion
        if jvm_path.startswith("\\\\?\\"):
            jvm_path = jvm_path[4:]

        # 1. Disable Windows critical error popups to prevent headless process hangs
        try:
            import ctypes

            # SEM_FAILCRITICALERRORS = 0x0001
            # SEM_NOGPFAULTERRORBOX = 0x0002
            # SEM_NOOPENFILEERRORBOX = 0x8000
            ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)  # type: ignore
            logger.info("Disabled Windows critical error popups via SetErrorMode.")
        except Exception as e:
            logger.warning(f"Failed to configure Windows SetErrorMode: {e}")

        # 2. Configure process DLL search directories to enable AddDllDirectory paths
        try:
            import ctypes

            # LOAD_LIBRARY_SEARCH_DEFAULT_DIRS = 0x00001000
            ctypes.windll.kernel32.SetDefaultDllDirectories(0x00001000)  # type: ignore
            logger.info("Configured process default DLL search directories via SetDefaultDllDirectories.")
        except Exception as e:
            logger.warning(f"Failed to call SetDefaultDllDirectories: {e}")

        # 3. Add JRE bin directory to PATH and DLL search paths
        bin_dir = os.path.dirname(os.path.dirname(jvm_path))
        os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(bin_dir)
                logger.info(f"Added JRE bin directory to DLL search path: {bin_dir}")
            except Exception as e:
                logger.warning(f"Failed to add JRE bin to DLL search path: {e}")

        # 4. Preload critical JRE DLLs using Altered Search Path
        # We must load jvm.dll first, as java.dll and other siblings depend directly on it!
        import ctypes

        dlls_to_load = [jvm_path]
        for dll_name in ["java.dll", "verify.dll", "zip.dll", "jimage.dll"]:
            dlls_to_load.append(os.path.join(bin_dir, dll_name))

        for dll_path in dlls_to_load:
            if dll_path.startswith("\\\\?\\"):
                dll_path = dll_path[4:]
            if os.path.exists(dll_path):
                try:
                    # LOAD_WITH_ALTERED_SEARCH_PATH = 0x00000008
                    handle = ctypes.windll.kernel32.LoadLibraryExW(dll_path, None, 0x00000008)  # type: ignore
                    if handle != 0:
                        logger.info(f"Successfully preloaded JRE DLL: {os.path.basename(dll_path)} (handle={handle})")
                    else:
                        err = ctypes.windll.kernel32.GetLastError()  # type: ignore
                        logger.warning(
                            f"Failed to preload JRE DLL {os.path.basename(dll_path)} via LoadLibraryExW. WinError: {err}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to preload JRE DLL {os.path.basename(dll_path)}: {e}")

    # Resolve Java Home if using portable JRE on Windows to prevent internal classloader resolution issues
    extra_jvm_args = [
        "-Djava.class.path=" + classpath,
        "-Djava.awt.headless=true",
        "-Djava.net.preferIPv4Stack=true",
        "-XX:+UseSerialGC",
        "-Xmx512m",
        "-Xrs",
    ]
    if os.name == "nt" and "jre" in jvm_path.lower():
        bin_dir = os.path.dirname(os.path.dirname(jvm_path))
        jre_home = os.path.dirname(bin_dir)
        if os.path.exists(jre_home):
            extra_jvm_args.append("-Djava.home=" + jre_home)
            logger.info(f"Adding Java Home property for portable JRE: {jre_home}")

    start_time = datetime.datetime.now()
    try:
        logger.info("Executing JNI startJVM call with headless and network optimization flags...")
        jpype.startJVM(
            jvm_path,
            *extra_jvm_args,
            interrupt=False,
        )
        duration = (datetime.datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Java Virtual Machine (JVM) booted successfully in {duration:.1f}ms")
    except RuntimeError as e:
        if "JVM is already started" in str(e):
            logger.info("JVM already started in current process context.")
        else:
            logger.error(f"JVM Startup Error: {e}", exc_info=True)
            raise


def open_db(mdb_path):
    """
    Opens the Access Database using Jackcess and returns the Database object.
    Caller is responsible for calling db.close() or try/finally.
    """
    ensure_jvm_started()

    import datetime

    from com.healthmarketscience.jackcess import DatabaseBuilder
    from java.io import File

    logger.info(f"Jackcess opening Access Database: {os.path.basename(mdb_path)}")
    start_time = datetime.datetime.now()
    try:
        db = DatabaseBuilder.open(File(mdb_path))
        duration = (datetime.datetime.now() - start_time).total_seconds() * 1000
        logger.info(f"Access Database loaded and parsed in {duration:.1f}ms")
        return db
    except Exception as e:
        logger.error(f"Failed to load Access Database: {e}", exc_info=True)
        raise


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


def update_entry_status(
    db,
    event_ptr,
    athlete_id,
    heat,
    lane,
    status="DQ",
    dq_code="",
    round_type="P",
    is_relay=False,
):
    """
    Updates the status and DQ code for a specific entry.
    round_type: 'P' for Prelims, 'F' for Finals, 'S' for Semis.
    is_relay: If True, updates RELAY table instead of ENTRY.
    """
    table_name = "RELAY" if is_relay else "ENTRY"
    table = db.getTable(table_name)
    if table is None:
        raise ValueError(f"{table_name} table not found")

    from java.util import HashMap

    # Helper to attempt update for a specific round type
    def try_update(r_type):
        criteria = HashMap()
        criteria.put("Event_ptr", event_ptr)
        # In RELAY table it's Relay_no, in ENTRY it's Ath_no
        id_col = "Relay_no" if is_relay else "Ath_no"
        criteria.put(id_col, athlete_id)

        # Often we want to match heat/lane too to be safe
        if heat > 0:
            col = "Pre_heat" if r_type == "P" else ("Fin_heat" if r_type == "F" else "Sem_heat")
            criteria.put(col, heat)
        if lane > 0:
            col = "Pre_lane" if r_type == "P" else ("Fin_lane" if r_type == "F" else "Sem_lane")
            criteria.put(col, lane)

        c = table.getDefaultCursor()
        if c.findFirstRow(criteria):
            row = c.getCurrentRow()

            # Update status (Map to MM internal codes)
            mm_stat = status
            if status == "DQ":
                mm_stat = "Q"
            elif status == "SCR":
                mm_stat = "R"

            stat_col = "Pre_stat" if r_type == "P" else ("Fin_stat" if r_type == "F" else "Sem_stat")
            row.put(stat_col, mm_stat)

            # Update DQ code if provided
            if dq_code:
                code_col = "Pre_dqcode" if r_type == "P" else ("Fin_dqcode" if r_type == "F" else "Sem_dqcode")
                row.put(code_col, dq_code)

            table.updateRow(row)
            logger.info(
                f"Updated DQ status for {'Relay' if is_relay else 'Athlete'} {athlete_id} in Event {event_ptr} (Round {r_type})"
            )
            return True
        return False

    # 1. Try provided round type
    if try_update(round_type):
        return True

    # 2. Try common fallbacks if initial attempt failed
    fallbacks = ["F", "P"] if round_type not in ["F", "P"] else (["F"] if round_type == "P" else ["P"])
    for f in fallbacks:
        if try_update(f):
            return True

    logger.warning(
        f"Could not find entry for {'Relay' if is_relay else 'Athlete'} {athlete_id} in Event {event_ptr} (Heat {heat}, Lane {lane}) across all rounds"
    )
    return False


def add_memorized_report(db, **kwargs):
    """
    Adds a report definition to MemorizedReports table.
    Expects keywords matching the 100 column names in the table.
    """
    # Ensure mandatory fields or defaults if needed
    # (Though kwargs should ideally have everything)
    _add_row(db, "MemorizedReports", **kwargs)
    return True
