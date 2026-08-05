# builders/debuff_builder.py
from pathlib import Path
import json
import re
from services.paths import RAW_DATA, PROCESSED

input_file = RAW_DATA / "debuff.txt"

class DebuffBuilder:
    """Builds debuff.json from the raw debuff data."""
   
    PATTERN = re.compile(
        r"(Major|Minor)\s+([A-Za-z]+)"
    )

    def __init__(self, data_directory: Path):
        self.data_directory = Path(data_directory)

    def load_raw(self) -> str:
        """Load the raw debuff text file."""

        # input_file = self.data_directory / "debuff.txt"

        with open(input_file, "r", encoding="utf-8") as f:
            return f.read()

    def parse(self, text: str) -> list[dict]:

        debuff = []

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
                "deBuff",
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

                current_debuff = self.create_debuff(
                    columns[0],
                    current_effect,
                )

                if len(columns) > 1:
                    current_debuff["description"] = columns[1]

                if len(columns) > 3:
                    source_type = columns[2].lower()

                    if source_type in current_debuff["relationships"]["granted_by"]:

                        current_debuff["relationships"]["granted_by"][source_type] = [
                            s.strip()
                            for s in columns[3].split(",")
                        ]

                if len(columns) > 4:
                    current_debuff["icon"] = columns[4]

                debuff.append(current_debuff)

                continue
            #
            # Continuation rows
            #

            if current_debuff and columns[0] in (
                "Abilities",
                "Sets",
                "Potions",
                "Scribing",
                "Champion",
                "Verses",
            ):

                source = columns[0].lower()

                if source in current_debuff["relationships"]["granted_by"]:

                    if len(columns) > 1:

                        current_debuff["relationships"]["granted_by"][source].extend(
                            [
                                s.strip()
                                for s in columns[1].split(",")
                            ]
                        )

                continue    

        #
        # Normalize
        #

        for debuff in debuff:

            granted = debuff["relationships"]["granted_by"]

            for key in granted:

                granted[key] = sorted(
                    set(granted[key])
                )

        return debuff



    def write(self, debuff: list[dict]) -> None:
        """Write debuff.json."""

        output = PROCESSED / "debuff.json"

        with open(output, "w", encoding="utf-8") as f:
            json.dump(
                debuff,
                f,
                indent=4,
                ensure_ascii=False,
            )

    def build(self) -> None:
        """Run the builder."""

        raw = self.load_raw()

        debuff = self.parse(raw)
        print(json.dumps(debuff[0], indent=4))
        self.write(debuff)

        print(f"Built {len(debuff)} debuff.")

    def create_debuff(self, tier: str, effect: str) -> dict:
        print(f"Creating: {tier} {effect}")
        record_id = (
            f"debuff_{tier.lower()}_{effect.lower()}"
            .replace(" ", "_")
        )

        return {

            #
            # Universal Fields
            #

            "id": record_id,

            "type": "debuff",

            "name": f"{tier} {effect}",

            "description": "",

            "icon": "",

            #
            # Debuff-specific
            #

            "tier": tier,

            "effect_name": effect,

            #
            # Relationships
            #

            "relationships": {

                "granted_by": {
                    "abilities": [],
                    "sets": [],
                    "potions": [],
                    "scribing": [],
                    "champion": [],
                    "verses": []
                }

            }
        }


print("Loaded:", __file__)
print("Has build:", hasattr(DebuffBuilder, "build"))     