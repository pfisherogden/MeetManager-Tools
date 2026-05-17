from mm_to_json.reporting.meet_event_writer import MeetEventWriter


def test_generate_ev3_header():
    meet_info = {
        "Meet_name1": "Test Meet",
        "Meet_location": "Test Pool",
        "Meet_start": "2026-06-01",
        "Meet_end": "2026-06-01",
        "Calc_date": "2026-06-01",
        "Meet_city": "Pleasanton",
        "Meet_state": "CA",
        "Meet_zip": "94566",
        "Meet_hostlsc": "CC",
        "indmax_perath": 3,
        "relmax_perath": 2,
        "entrymax_total": 4,
    }

    writer = MeetEventWriter(meet_info=meet_info, sessions=[], events=[], scoring=[])
    header = writer._generate_ev3_header()

    # Check key components in the semicolon-delimited string
    parts = header.split(";")
    assert parts[0] == "Test Meet"
    assert parts[1] == "Test Pool"
    assert "06/01/2026" in parts[2]
    assert parts[26] == "Pleasanton"
    assert parts[27] == "CA"
    assert parts[30] == "CC"


def test_generate_ev3_event_record():
    event = {
        "Event_no": 5,
        "Event_ptr": 5,
        "Ind_rel": "R",
        "Event_sex": "G",
        "Low_age": 9,
        "High_Age": 10,
        "Event_dist": 100,
        "Event_stroke": "E",
        "Num_prelanes": 8,
        "Session": 1,
    }

    writer = MeetEventWriter(meet_info={}, sessions=[], events=[], scoring=[])
    record = writer._generate_ev3_event_record(event, sess_order=1)

    parts = record.split(";")
    assert parts[0] == "5"  # Event No
    assert parts[3] == "1"  # Session
    assert parts[4] == "R"  # Relay
    assert parts[5] == "G"  # Girls
    assert parts[6] == "9"  # Low Age
    assert parts[7] == "10"  # High Age
    assert parts[8] == "100"  # Distance
    assert parts[9] == "E"  # Stroke
    assert parts[21] == "1"  # Sess Order


def test_generate_hyv_header():
    meet_info = {"Meet_name1": "Test Meet", "Meet_start": "2026-06-01", "Meet_location": "Test Pool"}
    writer = MeetEventWriter(meet_info=meet_info, sessions=[], events=[], scoring=[])
    header = writer._generate_hyv_header()

    parts = header.split(";")
    assert parts[0] == "Test Meet"
    assert "06/01/2026" in parts[1]
    assert parts[5] == "Test Pool"


def test_generate_hyv_event_record():
    event = {
        "Event_no": 13,
        "Ind_rel": "I",
        "Event_sex": "F",
        "Low_age": 0,
        "High_Age": 6,
        "Event_dist": 25,
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

    import os
    import zipfile

    output_path = str(tmp_path / "test_export.zip")
    writer = MeetEventWriter(meet_info=meet_info, sessions=[], events=events, scoring=[])
    writer.write_to_zip(output_path)

    assert os.path.exists(output_path)

    with zipfile.ZipFile(output_path, "r") as zipf:
        namelist = zipf.namelist()
        assert len(namelist) == 2
        assert any(n.endswith(".ev3") for n in namelist)
        assert any(n.endswith(".hyv") for n in namelist)

        # Verify content of EV3
        ev3_name = [n for n in namelist if n.endswith(".ev3")][0]
        content = zipf.read(ev3_name).decode("utf-8")
        assert "Test Meet" in content
        assert "1;1;F;1;I;F;0;18;50;A" in content
