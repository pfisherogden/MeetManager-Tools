import os
import zipfile

from mm_to_json.reporting.meet_event_writer import MeetEventWriter


def test_generate_ev3_header():
    meet_info = {
        "Meet_name1": "Test Meet",
        "Meet_location": "Test Pool",
        "Meet_start": 1779044881084,  # Some timestamp
        "Meet_end": 1779044881084,
        "Calc_date": "2026-06-01",
        "Meet_city": "Pleasanton",
        "Meet_state": "CA",
        "Meet_zip": "94566",
        "Meet_hostlsc": "CC",
        "indmax_perath": 3,
        "relmax_perath": 2,
        "entrymax_total": 4,
        "entry_deadline": "2026-05-26",
    }

    writer = MeetEventWriter(meet_info=meet_info, sessions=[], events=[], scoring=[])
    header = writer._generate_ev3_header()

    # Check key components in the semicolon-delimited string
    parts = header.split(";")
    assert parts[0] == "Test Meet"
    assert parts[1] == "Test Pool"
    assert parts[5] == "YO"
    assert parts[6] == "0"
    assert parts[9] == "Created by Hy-Tek's MEET MANAGER"
    assert parts[11] == "7.0Gb"
    assert parts[13] == "3" # indmax_perath (legacy/duplicated)
    assert parts[18] == "4" # entrymax_total
    assert parts[19] == "3" # indmax_perath
    assert parts[20] == "2" # relmax_perath
    assert parts[21] == "1" # relmaxscorers_perteam

    assert parts[23] == "05/26/2026"  # entry_deadline

    assert parts[26] == "Pleasanton"
    assert parts[30] == "CC"


def test_generate_ev3_event_record():
    event = {
        "Event_no": 5,
        "Event_ptr": 5,
        "Ind_rel": "R",
        "Event_sex": "G",
        "Low_age": 9,
        "High_Age": 10,
        "Event_dist": 100.0,
        "Event_stroke": "E",
        "Session": 1,
    }

    writer = MeetEventWriter(meet_info={}, sessions=[], events=[], scoring=[])
    record = writer._generate_ev3_event_record(event, sess_order=1)

    parts = record.split(";")
    assert parts[0] == "5"  # Event No
    assert parts[3] == "1"  # Session
    assert parts[4] == "R"  # Relay
    assert parts[5] == "G"  # Girls
    assert parts[8] == "100"  # Distance (should be integer)
    assert parts[9] == "E"  # Stroke
    assert parts[10] == "0"
    assert parts[21] == "1"  # Sess Order
    assert parts[22] == "1"  # Session No
    assert parts[24] == "09:00AM"  # Default time
    assert parts[29] == "4*>"  # Relay size with trailer


def test_generate_hyv_header():
    meet_info = {"Meet_name1": "Test Meet", "Meet_start": "2026-06-01", "Meet_location": "Test Pool"}
    writer = MeetEventWriter(meet_info=meet_info, sessions=[], events=[], scoring=[])
    header = writer._generate_hyv_header()

    parts = header.split(";")
    assert parts[0] == "Test Meet"
    assert "06/01/2026" in parts[1]
    assert parts[5] == "Test Pool"
    assert parts[8] == "7.0Gb"


def test_generate_hyv_event_record():
    event = {
        "Event_no": 13,
        "Ind_rel": "I",
        "Event_sex": "F",
        "Low_age": 0,
        "High_Age": 6,
        "Event_dist": 25.0,
        "Event_stroke": "A",
    }
    writer = MeetEventWriter(meet_info={}, sessions=[], events=[], scoring=[])
    record = writer._generate_hyv_event_record(event)

    parts = record.split(";")
    assert parts[0] == "13"
    assert parts[2] == "F"
    assert parts[3] == "I"
    assert parts[4] == "0"
    assert parts[5] == "6"
    assert parts[6] == "25"
    assert parts[7] == "1"  # Stroke A -> 1 (Free)


def test_write_to_zip(tmp_path):
    meet_info = {"Meet_name1": "Test Meet", "Meet_start": "2026-06-01"}
    events = [
        {
            "Event_no": 1,
            "Session": 1,
            "Ind_rel": "I",
            "Event_sex": "F",
            "Low_age": 0,
            "High_Age": 18,
            "Event_dist": 50,
            "Event_stroke": "A",
        }
    ]

    output_path = str(tmp_path / "test_export.zip")
    writer = MeetEventWriter(meet_info=meet_info, sessions=[], events=events, scoring=[])
    writer.write_to_zip(output_path)

    assert os.path.exists(output_path)

    with zipfile.ZipFile(output_path, "r") as zipf:
        namelist = zipf.namelist()
        assert len(namelist) == 2

        # Verify content of EV3
        ev3_name = [n for n in namelist if n.endswith(".ev3")][0]
        content = zipf.read(ev3_name).decode("utf-8")
        assert "Test Meet" in content
        # 1;1;F;1;I;F;0;18;50;A;0
        assert "1;1;F;1;I;F;0;18;50;A;0" in content
