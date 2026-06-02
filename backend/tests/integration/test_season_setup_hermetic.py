import os
import sys
from unittest.mock import patch

# Add src and current dir to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../../src"))
sys.path.append(os.path.join(os.path.dirname(__file__), "../../scripts/season_setup"))
sys.path.append(os.path.dirname(__file__))

from mock_mdb_generator import generate_mock_mdb
from season_transformer import SeasonTransformer


def test_season_transformer_with_mock_generator():
    """Verify that SeasonTransformer works correctly with randomized but structured data."""
    data = generate_mock_mdb(seed=123)
    transformer = SeasonTransformer(data)

    # Check initial state
    assert len(transformer.table_data.get("athlete", [])) > 0
    assert len(transformer.table_data.get("Session", [])) == 2

    # 1. Purge
    transformer.purge_data(preserve_team_abbr="DP")
    assert len(transformer.table_data.get("athlete", [])) == 0
    assert len(transformer.table_data.get("Entry", [])) == 0

    # 2. Update
    transformer.update_meet(
        name="2026 Season Opener",
        start_date="2026-05-30",
        lanes=8,
        location="Host Pool",
        age_up="2026-06-01",
        entry_open="2025-06-01",
        entry_deadline="2026-05-26",
    )
    # Check by finding the actual key in the normalized table_data
    meet_key = transformer._get_all_table_keys("meet")[0]
    meet = transformer.table_data[meet_key][0]
    # Find name column (case-insensitive)
    name_val = None
    for k, v in meet.items():
        if str(k).lower() == "meet_name1":
            name_val = v
    assert name_val == "2026 Season Opener"

    # 3. Consolidate Sessions
    transformer.consolidate_sessions(is_champs=False)
    session_key = transformer._get_all_table_keys("session")[0]
    assert len(transformer.table_data[session_key]) == 1

    # Check Sessitem mapping
    sessitem_key = transformer._get_all_table_keys("sessitem")[0]
    assert len(transformer.table_data[sessitem_key]) == 10  # All 10 events should be mapped


def test_season_transformer_case_insensitivity():
    """Verify transformer handles inconsistent casing in keys/columns."""
    data = {"meet": [{"MEET_NAME1": "Template"}], "TEAM": [{"TCode": "DP", "TName": "Del Prado"}]}
    transformer = SeasonTransformer(data)

    transformer.update_meet(name="New Meet", start_date="2026-01-01", lanes=6)
    assert transformer.table_data["meet"][0]["MEET_NAME1"] == "New Meet"

    transformer.ensure_team_exists("CW", "Castlewood")
    assert len(transformer.table_data["TEAM"]) == 2
    assert any(
        str(v).upper() == "CW"
        for t in transformer.table_data["TEAM"]
        for k, v in t.items()
        if str(k).lower() == "tcode"
    )


@patch("generate_season.restore_db")
def test_generate_season_logic_hermetic(mock_restore, tmp_path):
    """Verify the high-level generation logic using mocks and generator."""
    from generate_season import generate

    # Create a dummy template file so os.path.exists passes
    dummy_template = tmp_path / "mock_template.mdb"
    dummy_template.write_text("dummy")

    template_data = generate_mock_mdb()

    # We need to mock MmToJsonConverter and its export_full_schema
    with patch("generate_season.MmToJsonConverter") as mock_converter:
        instance = mock_converter.return_value
        instance.export_full_schema.return_value = {
            "tables": {
                tname: {
                    "rows": rows,
                    "columns": [{"name": k, "type": "TEXT"} for k in rows[0].keys()] if rows else [],
                    "indexes": [],
                }
                for tname, rows in template_data.items()
            }
        }

        output_dir = tmp_path / "output"
        with patch(
            "generate_season.load_schedule",
            return_value=[
                {
                    "date": "2026-05-30",
                    "name": "FAST vs Del Prado",
                    "host": "Del Prado Cabana Club",
                    "is_champs": False,
                    "home": "FAST",
                    "away": "DP",
                }
            ],
        ):
            generate(str(dummy_template), str(output_dir), 2026)

    assert mock_restore.called
    _, target_path = mock_restore.call_args[0]
    assert "2026-05-30 FAST vs Del Prado-v5-final.mdb" in target_path
