import json
from pathlib import Path


SOURCE_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "raw"
    / "eso_hub_skill_data.json"
)


def main():

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    records = data["skills"]

    matches = [
        (
            index,
            record,
        )
        for index, record in enumerate(records)
        if str(
            record.get("skill_name", "")
        ).strip().casefold()
        == "executioner"
    ]

    print("=" * 60)
    print(" EXECUTIONER DUPLICATE CHECK")
    print("=" * 60)

    print()
    print(
        f"Records found: {len(matches)}"
    )

    for index, record in matches:

        print()
        print(
            f"RECORD {index}"
        )

        print(
            f"  Name: {record.get('skill_name')}"
        )

        print(
            f"  URL:  {record.get('eso_hub_url')}"
        )

        print(
            f"  Weapon: {record.get('weapon')}"
        )

        for field in (
            "buffs",
            "debuffs",
            "status_effects",
            "modifying_sets",
            "champion_points",
        ):

            value = record.get(
                field,
                [],
            )

            print(
                f"  {field}: "
                f"{len(value) if isinstance(value, list) else value}"
            )

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()