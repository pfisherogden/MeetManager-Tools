from mm_to_json.reporting.cts_writer import CTSScoreboardWriter


def test_generate_event_scb(tmp_path):
    event = {
        "eventNum": 13,
        "eventDesc": "Girls 6 & under 25 Yard Freestyle",
        "entries": [
            {
                "name": "Lilly Prater",
                "firstName": "Lilly",
                "lastName": "Prater",
                "initial": "J",
                "teamCode": "DP",
                "rawTeamCode": "DP   ",
                "heat": 1,
                "lane": 3,
                "isRelay": False,
            }
        ],
    }

    writer = CTSScoreboardWriter({}, [event])
    out_path = tmp_path / "E013.scb"
    writer.generate_event_scb(event, str(out_path), 1)

    assert out_path.exists()
    content = out_path.read_bytes()

    # Verify line endings are CRLF
    assert b"\r\n" in content

    lines = content.split(b"\r\n")

    # Header (abbreviated)
    assert lines[0].decode("cp1252") == "#13 GIRLS 6&U 25 FREE"

    # Lanes 1, 2 are blank with "--" separator
    blank_lane = " " * 20 + "--" + " " * 16
    assert lines[1].decode("cp1252") == blank_lane
    assert lines[2].decode("cp1252") == blank_lane

    # Lane 3 (Lilly Prater formatted)
    lilly_line = lines[3].decode("cp1252")
    assert lilly_line.startswith("PRATER, LILLY J")
    assert "--DP" in lilly_line
    assert len(lilly_line) == 38


def test_generate_event_scb_relay(tmp_path):
    event = {
        "eventNum": 1,
        "eventDesc": "Girls 6 & under 100 Yard Medley Relay",
        "entries": [
            {
                "name": "Castlewood Barracudas A",
                "teamCode": "CB",
                "rawTeamCode": "CB",
                "relayLtr": "A",
                "heat": 1,
                "lane": 3,
                "isRelay": True,
            }
        ],
    }

    writer = CTSScoreboardWriter({}, [event])
    out_path = tmp_path / "E001.scb"
    writer.generate_event_scb(event, str(out_path), 1)

    assert out_path.exists()
    content = out_path.read_bytes()
    lines = content.split(b"\r\n")

    # Header
    assert lines[0].decode("cp1252") == "#1 GIRLS 6&U 100 MEDLEY RELAY"

    # Lane 3
    relay_line = lines[3].decode("cp1252")
    assert relay_line.startswith("CB A")
    assert "--CB" in relay_line
    assert len(relay_line) == 38


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
