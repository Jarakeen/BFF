from pathlib import Path
import json
import re


class BuffBuilder:
    """Builds buff.json from the raw buff data."""

    PATTERN = re.compile(
        r"(Major|Minor)\s+([A-Za-z]+)"
    )

    def __init__(self, data_directory: Path):
        self.data_directory = Path(data_directory)

    def load_raw(self) -> str:
        """Load the raw buff text file."""

        raw_file = self.data_directory / "buff.txt"

        with open(raw_file, "r", encoding="utf-8") as f:
            return f.read()

    def parse(self, text: str) -> list[dict]:

        buff = []

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
                "Buff",
                "Buff Name \tType \tDescription \tSources \tIcon",
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

                if len(columns) > 3:
                    source_type = columns[2].lower()

                    if source_type in current_buff["relationships"]["granted_by"]:

                        current_buff["relationships"]["granted_by"][source_type] = [
                            s.strip()
                            for s in columns[3].split(",")
                        ]

                if len(columns) > 4:
                    current_buff["icon"] = columns[4]

                buff.append(current_buff)

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

                if source in current_buff["relationships"]["granted_by"]:

                    if len(columns) > 1:

                        current_buff["relationships"]["granted_by"][source].extend(
                            [
                                s.strip()
                                for s in columns[1].split(",")
                            ]
                        )

                continue    

        #
        # Normalize
        #

        for buff in buff:

            granted = buff["relationships"]["granted_by"]

            for key in granted:

                granted[key] = sorted(
                    set(granted[key])
                )

        return buff



    def write(self, buff: list[dict]) -> None:
        """Write buff.json."""

        output = self.data_directory / "buff.json"

        with open(output, "w", encoding="utf-8") as f:
            json.dump(
                buff,
                f,
                indent=4,
                ensure_ascii=False,
            )

    def build(self) -> None:
        """Run the builder."""

        raw = self.load_raw()

        buff = self.parse(raw)
        print(json.dumps(buff[0], indent=4))
        self.write(buff)

        print(f"Built {len(buff)} buff.")

    def create_buff(self, tier: str, effect: str) -> dict:
        print(f"Creating: {tier} {effect}")
        record_id = (
            f"buff_{tier.lower()}_{effect.lower()}"
            .replace(" ", "_")
        )

        return {

            #
            # Universal Fields
            #

            "id": record_id,

            "type": "buff",

            "name": f"{tier} {effect}",

            "description": "",

            "icon": "",

            #
            # Buff-specific
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
print("Has build:", hasattr(BuffBuilder, "build"))    