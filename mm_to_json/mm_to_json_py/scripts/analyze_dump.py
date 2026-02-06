import json


def analyze():
    with open("tests/Singers23_raw_dump.json", "r") as f:
        data = json.load(f)

    t = data["tables"].get("Athlete")
    if not t:
        print("Athlete table not found")
        return

    print("Athlete Columns:")
    for col in t["columns"]:
        print(f"{col['name']}: {col['type']}")


if __name__ == "__main__":
    analyze()
