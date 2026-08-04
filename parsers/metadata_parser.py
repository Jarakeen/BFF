import re
from pathlib import Path

from models.boss import Boss, Health

class MetadataParser:

    def parse(self, text: str) -> Boss:

        trial = self.extract_trial(text)
        order = self.extract_order(text)

        return Boss(

            archive_no=self.generate_archive_number(
                trial,
                order
            ),

            name=self.extract_name(text),

            trial=trial,

            arena=self.extract_arena(text),

            race=self.extract_race(text),

            faction=self.extract_faction(text),

            condition=self.extract_condition(text),

            boss_order=self.extract_order(text),
        )

    def generate_archive_number(
        self,
        trial: str,
        boss_order: int,
    ) -> str:

        abbreviations = {

            "Rockgrove": "RG",
            "Lucent Citadel": "LC",
            "Sunspire": "SS",
            "Kyne's Aegis": "KA",
            "Sanity's Edge": "SE",
            "Cloudrest": "CR",
            "Maw of Lorkhaj": "MOL",
            "Aetherian Archive": "AA",
            "Hel Ra Citadel": "HRC",
            "Asylum Sanctorium": "AS",
            "Halls of Fabrication": "HOF",
            "Dreadsail Reef": "DR",
            "Ossein Cage": "OC",
        }

        trial_code = abbreviations.get(
            trial,
            "UNK",
        )

        return f"TR-{trial_code}-{boss_order:03d}"

    

    def extract_name(self, text: str) -> str:

        for line in text.splitlines():

            line = line.strip()

            if line:
                return line

        return "Unknown"

    def extract_trial(self, text: str) -> str:

        match = re.search(
            r"Location\s+([^,\n]+)",
            text,
        )

        if match:
            return match.group(1).strip()

        return ""

    def extract_arena(self, text: str) -> str:

        match = re.search(
            r"Location\s+[^,\n]+,\s*([^\n]+)",
            text,
        )

        if match:
            return match.group(1).strip()

        return ""

    def extract_race(self, text: str) -> str:

        match = re.search(
            r"Race\s+([^\n]+)",
            text,
        )

        if match:
            return match.group(1).strip()

        return ""

    def extract_faction(self, text: str) -> str:

        match = re.search(
            r"Faction\(s\)\s+([^\n]+)",
            text,
        )

        if match:
            return match.group(1).strip()

        return ""

    def extract_condition(self, text: str) -> str:

        match = re.search(
            r"Condition\s+([^\n]+)",
            text,
        )

        if match:
            return match.group(1).strip()

        return ""

    def extract_order(self, text: str) -> int:

        match = re.search(
            r"Boss Order:\s*(\d+)",
            text,
        )

        if match:
            return int(match.group(1))

        return 0

                

            