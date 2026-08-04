import re

from models.boss import Mechanic
from parsers.section_parser import SectionParser


class MechanicsParser(SectionParser):
    """
    Parses the Skills and Abilities section of a boss page.
    """

    def parse(self, text: str) -> list[Mechanic]:

        section = self.extract_section(
            text,
            "Skills and Abilities",
            "Hard Mode",
        )

        return self.parse_section(section)

    def parse_hardmode(self, text: str) -> list[Mechanic]:

        section = self.extract_section(
            text,
            "Hard Mode",
            "Dialogue",
        )

        return self.parse_section(section)

    # --------------------------------------------------
    # Section Parsing
    # --------------------------------------------------

    def parse_section(
        self,
        section: str,
    ) -> list[Mechanic]:

        mechanics = []

        current_name = None
        description = []

        for line in section.splitlines():

            if not line.strip():
                continue

            if self.is_heading(line):

                if current_name:

                    mechanics.append(
                        self.build_mechanic(
                            current_name,
                            description,
                        )
                    )

                current_name = line.strip()
                description = []

            else:

                description.append(line.strip())

        if current_name:

            mechanics.append(
                self.build_mechanic(
                    current_name,
                    description,
                )
            )

        return mechanics

    # --------------------------------------------------
    # Mechanic Builder
    # --------------------------------------------------

    def build_mechanic(
        self,
        name: str,
        description: list[str],
    ) -> Mechanic:

        names = [
            n.strip()
            for n in name.split("/")
        ]

        mechanic = Mechanic(
            name=names[0],
            aliases=names[1:],
            description=" ".join(description),
        )

        return self.analyze(mechanic)

    # --------------------------------------------------
    # Analysis
    # --------------------------------------------------

    def analyze(
        self,
        mechanic: Mechanic,
    ) -> Mechanic:

        text = mechanic.description.lower()

        mechanic.interruptible = "interrupt" in text
        mechanic.blockable = "block" in text
        mechanic.dodgeable = "dodge" in text
        mechanic.cleanseable = "cleanse" in text

        self.find_damage_type(mechanic)

        self.generate_tags(mechanic)

        self.calculate_priority(mechanic)

        return mechanic

    # --------------------------------------------------
    # Damage
    # --------------------------------------------------

    def find_damage_type(
        self,
        mechanic: Mechanic,
    ):

        text = mechanic.description.lower()

        damage_types = {

            "physical": "Physical",
            "fire": "Fire",
            "frost": "Frost",
            "shock": "Shock",
            "poison": "Poison",
            "oblivion": "Oblivion",
        }

        for keyword, damage in damage_types.items():

            if f"{keyword} damage" in text:

                mechanic.damage_type = damage

                return

    # --------------------------------------------------
    # Tags
    # --------------------------------------------------

    def generate_tags(
        self,
        mechanic: Mechanic,
    ):

        if mechanic.damage_type:

            mechanic.tags.append(
                mechanic.damage_type.lower()
            )

        if mechanic.interruptible:

            mechanic.tags.append("interrupt")

        if mechanic.blockable:

            mechanic.tags.append("block")

        if mechanic.dodgeable:

            mechanic.tags.append("dodge")

        if mechanic.cleanseable:

            mechanic.tags.append("cleanse")

    # --------------------------------------------------
    # Priority
    # --------------------------------------------------

    def calculate_priority(
        self,
        mechanic: Mechanic,
    ):

        text = mechanic.description.lower()

        if "one-shot" in text:

            mechanic.priority = 10

        elif "instantly kills" in text:

            mechanic.priority = 10

        elif "very high" in text:

            mechanic.priority = 8

        elif "high" in text:

            mechanic.priority = 7

        elif "moderate" in text:

            mechanic.priority = 5