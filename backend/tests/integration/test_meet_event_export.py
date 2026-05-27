import os
import zipfile

from season_transformer import SeasonTransformer  # noqa: I001

from mm_to_json.reporting.meet_event_writer import MeetEventWriter  # noqa: I001


def test_full_export_flow(tmp_path):
    # 1. Start with raw MDB-like data
    table_data = {
        "MEET": [{"Meet_name1": "Champs 2026", "Meet_start": "2026-07-18", "Meet_numlanes": 10}],
        "TEAM": [{"TCode": "DP", "TName": "Del Prado Stingrays"}],
        "MTEVENT": [
            {
                "MtEvent": 1,
                "Event_no": 1,
                "Event_stroke": "E",
                "Ind_rel": "R",
                "Event_sex": "G",
                "Low_age": 0,
                "High_Age": 18,
                "Event_dist": 100,
                "Num_prelanes": 10,
                "Session": 0,
            },
            {
                "MtEvent": 2,
                "Event_no": 2,
                "Event_stroke": "A",
                "Ind_rel": "I",
                "Event_sex": "B",
                "Low_age": 0,
                "High_Age": 18,
                "Event_dist": 50,
                "Num_prelanes": 10,
                "Session": 0,
            },
        ],
        "Session": [],
        "Sessitem": [],
    }

    # 2. Transform (Season Setup Logic)
    transformer = SeasonTransformer(table_data)
    transformer.update_meet(name="TVSL Championships", start_date="2026-07-18", lanes=10, is_champs=True)
    transformer.consolidate_sessions(is_champs=True)

    # 3. Export
    transformed_data = transformer.table_data
    writer = MeetEventWriter(
        meet_info=transformed_data["MEET"][0],
        sessions=transformed_data["Session"],
        events=transformed_data["MTEVENT"],
        scoring=[],  # Not strictly needed for EV3
    )

    zip_path = str(tmp_path / "Champs_Export.zip")
    writer.write_to_zip(zip_path)

    # 4. Verify ZIP
    assert os.path.exists(zip_path)
    with zipfile.ZipFile(zip_path, "r") as zipf:
        ev3_name = [n for n in zipf.namelist() if n.endswith(".ev3")][0]
        content = zipf.read(ev3_name).decode("utf-8")

        # Verify meet info
        assert "TVSL Championships" in content

        # Verify header fields (exact indices)
        header = content.split("\r\n")[0]
        h_parts = header.split(";")
        assert h_parts[5] == "YO"
        assert h_parts[9] == "Created by Hy-Tek's MEET MANAGER"
        assert h_parts[11] == "7.0Gb"
        
        # Rule 12 Registration Limits (Definitive verification of entire flow)
        assert h_parts[13] == "3"  # indmax_perath (legacy)
        assert h_parts[18] == "4"  # entrymax_total
        assert h_parts[19] == "3"  # indmax_perath
        assert h_parts[20] == "2"  # relmax_perath
        assert h_parts[21] == "1"  # relmaxscorers_perteam

        # Verify session mapping (Med Relays -> Session 1)
        # 1;1;F;1;R;G;0;18;100;E;0
        assert "1;1;F;1;R;G;0;18;100;E;0" in content
        # Verify Freestyle -> Session 2
        # 2;2;F;2;I;B;0;18;50;A;0
        assert "2;2;F;2;I;B;0;18;50;A;0" in content

        # Verify relay size (4) and individual size (0)
        # Event 1 is relay, sess order 1
        assert ";1;1;1;09:00AM;Y;0;0;0;4*>" in content
        # Event 2 is individual, sess order 1
        assert ";2;1;1;09:36AM;Y;0;0;0;0*>" in content
