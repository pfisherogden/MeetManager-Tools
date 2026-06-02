from mm_to_json.reporting.cts_writer import CTSScoreboardWriter


def test_generate_event_scb(tmp_path):
    event = {
        "eventNum": 13,
        "eventDesc": "Girls 6 & under 25 Yard Freestyle",
        "entries": [{"name": "Lilly Prater", "teamCode": "DP", "heat": 1, "lane": 3}],
    }

    writer = CTSScoreboardWriter({}, [event])
    out_path = tmp_path / "E013.scb"
    writer.generate_event_scb(event, str(out_path))

    assert out_path.exists()
    content = out_path.read_text(encoding="cp1252")
    lines = content.splitlines()

    # Header
    assert lines[0] == "#13 GIRLS 6 & UNDER 25 YARD FREESTYLE"

    # Lilly Prater line (Lane 3)
    # Lanes 1, 2 are blank
    assert lines[1] == " " * 38
    assert lines[2] == " " * 38
    # Lane 3
    lilly_line = lines[3]
    assert lilly_line.startswith("Lilly Prater")
    assert "--DP" in lilly_line
    assert len(lilly_line) == 38


def test_generate_dolphin_events(tmp_path):
    events = [
        {"eventNum": 1, "eventDesc": "Event 1", "entries": [{"heat": 2}]},
        {"eventNum": 2, "eventDesc": "Event 2", "entries": [{"heat": 1}]},
    ]

    writer = CTSScoreboardWriter({}, events)
    out_path = tmp_path / "events.csv"
    writer.generate_dolphin_events(str(out_path))

    assert out_path.exists()
    content = out_path.read_text(encoding="cp1252")
    lines = content.splitlines()

    assert lines[0] == "1,EVENT 1,2,1,A"
    assert lines[1] == "2,EVENT 2,1,1,A"
