import numpy as np
import pandas as pd

from mm_to_json.mm_to_json import MmToJsonConverter


def reproduce():
    # Mock table data with explicit np.nan
    df_team = pd.DataFrame([{"Team_no": 1, "Team_abbr": "KS", "Team_short": np.nan, "Team_lsc": "TV"}])

    converter = MmToJsonConverter(table_data={})
    converter.tables = {"Team": df_team}
    converter.schema_type = "A"

    # Trigger cache build
    name = converter.get_team_name(1)

    print(f"Team Name for ID 1: '{name}'")
    if "nan" in name.lower():
        print("REPRODUCED: Team name contains 'nan'")
    elif name == "KS-TV":
        print("SUCCESS: Team name is correctly resolved to abbreviation-lsc")
    else:
        print(f"OTHER: Team name is '{name}'")


if __name__ == "__main__":
    reproduce()
