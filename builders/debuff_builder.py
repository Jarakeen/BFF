from pathlib import Path
import json
import re


class DebuffBuilder:
    """Builds buffs.json from the raw buff data."""

    PATTERN = re.compile(
        r"(Major|Minor)\s+([A-Za-z]+)"
    )

    def __init__(self, data_directory: Path):
        self.data_directory = Path(data_directory)

    def load_raw(self) -> str:
        """Load the raw buff text file."""

        raw_file = self.data_directory / "debuff.txt"

        with open(raw_file, "r", encoding="utf-8") as f:
            return f.read()

    def parse(self, text: str) -> list[dict]:

        buffs = []

        current_effect = None
        current_buff = None

        for raw_line in text.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            #
            # Skip headers
            #

            if line in (
                "Debuffs",
                "Debuff Name \tType \tDescription \tSources \tIcon",
            ):
                continue

            #
            # New effect
            #

            if "\t" not in raw_line:

                current_effect = line

                continue

            #
            # Split columns
            #

            columns = [
                c.strip()
                for c in raw_line.split("\t")
                if c.strip()
            ]

            if not columns:
                continue

            #
            # Major / Minor row
            #

            if columns[0] in ("Major", "Minor"):

                current_buff = self.create_buff(
                    columns[0],
                    current_effect,
                )

                if len(columns) > 1:
                    current_buff["description"] = columns[1]

                if len(columns) > 2:
                    source_type = columns[2].lower()

                    if source_type in current_buff["sources"]:

                        current_buff["sources"][source_type] = [
                            s.strip()
                            for s in columns[3].split(",")
                        ]

                if len(columns) > 4:
                    current_buff["icon"] = columns[4]

                buffs.append(current_buff)

                continue
            #
            # Continuation rows
            #

            if current_buff and columns[0] in (
                "Abilities",
                "Sets",
                "Potions",
                "Scribing",
                "Champion",
                "Verses",
            ):

                source = columns[0].lower()

                if source in current_buff["sources"]:

                    if len(columns) > 1:

                        current_buff["sources"][source].extend(
                            [
                                s.strip()
                                for s in columns[1].split(",")
                            ]
                        )

                continue    

            #
            # Remove duplicates and sort the sources
            #
            for buff in buffs:

                for key in buff["sources"]:

                    buff["sources"][key] = sorted(
                        set(buff["sources"][key])
                    )

        return buffs



    def write(self, buffs: list[dict]) -> None:
        """Write Debuffs.json."""

        output = self.data_directory / "debuffs.json"

        with open(output, "w", encoding="utf-8") as f:
            json.dump(
                buffs,
                f,
                indent=4,
                ensure_ascii=False,
            )

    def build(self) -> None:
        """Run the builder."""

        raw = self.load_raw()

        buffs = self.parse(raw)

        self.write(buffs)

        print(f"Built {len(buffs)} buffs.")

    def create_buff(self, tier: str, effect: str) -> dict:
        return {
            "name": f"{tier} {effect}",
            "tier": tier,
            "effect": effect,
            "description": "",
            "icon": "",
            "sources": {
                "abilities": [],
                "sets": [],
                "potions": [],
                "scribing": [],
                "champion": [],
                "verses": []
            }
        }    


print("Loaded:", __file__)
print("Has build:", hasattr(DebuffBuilder, "build"))    