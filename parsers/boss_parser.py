from pathlib import Path
import re

from models.boss import Boss, Mechanic


class BossParser:

    def parse(self, path: Path) -> Boss:

        text = path.read_text(encoding="utf-8")

        # Extract metadata first
        trial = self.extract_trial(text)
        order = self.extract_order(text)

        # Build the Boss object
        boss = Boss(
            archive_no=self.generate_archive_number(
                trial,
                order
            ),

            name=self.extract_name(text),

            trial=trial,

            boss_order=order,
        )

        # Fill in the remaining sections
        boss.mechanics = self.extract_mechanics(text)
        boss.hardmode_mechanics = self.extract_hardmode_mechanics(text)
        boss.dialogue = self.extract_dialogue(text)
        boss.notes = self.extract_notes(text)

        return boss




def extract_section(
    self,
    text: str,
    start: str,
    end: str | None = None,
    ) -> str:
    """
    Returns all text between two section headings.

    Example:
        extract_section(text,
                        "Skills and Abilities",
                        "Dialogue")
    """

    start_match = re.search(re.escape(start), text)

    if not start_match:
        return ""

    start_index = start_match.end()

    if end:

        end_match = re.search(
            re.escape(end),
            text[start_index:]
        )

        if end_match:
            end_index = start_index + end_match.start()
            return text[start_index:end_index].strip()

    return text[start_index:].strip()

def extract_name(self, text: str) -> str:
    """
    Extract the boss name from a UESP page.
    """

    match = re.search(
        r"Online:(.+?)\n",
        text
    )

    if match:
        return match.group(1).strip()

    return "Unknown Boss"

def extract_trial(self, text: str) -> str:
    """
    Extract the trial/location name from the UESP page.
    """

    match = re.search(
        r"Location\s+([^\n,]+)",
        text
    )

    if match:
        return match.group(1).strip()

    return ""

def extract_order(self, text: str) -> int:
    """
    Extract the boss order from the Foundry header.
    """

    match = re.search(
        r"Boss Order:\s*(\d+)",
        text
    )

    if match:
        return int(match.group(1))

    return 0

def extract_mechanics(self, text: str) -> list[Mechanic]:

    mechanics = []

    section = self.extract_section(
        text,
        "Skills and Abilities",
        "Hard Mode"
    )

    lines = section.splitlines()

    current_name = None
    description = []

    for line in lines:

        line = line.rstrip()

        if not line:
            continue

        # New mechanic names have no indentation
        if line and not line.startswith(" "):

            # Save the previous mechanic
            if current_name:

                mechanics.append(
                    Mechanic(
                        name=current_name,
                        description=" ".join(description).strip()
                    )
                )

            current_name = line.strip()
            description = []

        else:

            description.append(line.strip())

    # Save the last mechanic
    if current_name:

        mechanics.append(
            Mechanic(
                name=current_name,
                description=" ".join(description).strip()
            )
        )

    mechanic = self.analyze_mechanic(mechanic)

    mechanics.append(mechanic)


    def analyze_mechanic(self, mechanic: Mechanic) -> Mechanic:

        text = mechanic.description.lower()

        if "interrupt" in text:
            mechanic.interruptible = True

        if "block" in text:
            mechanic.blockable = True

        if "dodge" in text:
            mechanic.dodgeable = True

        if "cleanse" in text:
            mechanic.cleanseable = True

        if "frost damage" in text:
            mechanic.damage_type = "Frost"

        elif "fire damage" in text:
            mechanic.damage_type = "Fire"

        elif "poison damage" in text:
            mechanic.damage_type = "Poison"  

        elif "oblivion damage" in text:
            mechanic.damage_type = "Oblivion"  

        elif "shock damage" in text:
            mechanic.damage_type = "Shock"     

        if "taunt" in text:
            mechanic.roles.append = "Tank"
     
        if "healer" in text:
            mechanic.roles.append = "Healer"

        if "spread" in text:
            mechanic.roles.append = "Group"   

        if "instantly kills" in text:
            mechanic.priority = 10

        elif "high damage" in text:
            mechanic.priority = 8

        elif "moderate damage" in text:
            mechanic.priority = 5    

    return mechanic

def extract_hardmode_mechanics(self, text: str) -> list[Mechanic]:

    mechanics = []

    section = self.extract_section(
        text,
        "Hard Mode",
        "Dialogue"
        )

    lines = section.splitlines()

    current_name = None
    description = []

    for line in lines:

        line = line.rstrip()

        if not line:
            continue

        if self.is_heading(line):

            if current_name:

                mechanic = Mechanic(
                    name=current_name,
                    description=" ".join(description).strip()
                )

                mechanics.append(
                    self.analyze_mechanic(mechanic)
                )

            current_name = line.strip()
            description = []

        else:

            description.append(line.strip())

    if current_name:

        mechanic = Mechanic(
            name=current_name,
            description=" ".join(description).strip()
        )

        mechanics.append(
            self.analyze_mechanic(mechanic)
        )

    return mechanics

def extract_dialogue(self, text: str) -> list[str]:

    dialogue = []

    section = self.extract_section(
        text,
        "Dialogue",
        "Notes"
    )

    for line in section.splitlines():

        line = line.strip()

        if not line:
            continue

        dialogue.append(line)

    return dialogue

def extract_notes(self, text: str) -> list[str]:
    """
    Extract the Notes section from the page.
    """

    section = self.extract_section(
        text,
        "Notes"
        )

    notes = []

    for line in section.splitlines():

        line = line.strip()

        if not line:
            continue

        notes.append(line)

    return notes

def extract_archive_number(
    self,
    trial: str,
    boss_order: int
) -> str:

    abbreviations = {

        "Rockgrove": "RG",

        "Lucent Citadel": "LC",

        "Sunspire": "SS",

        "Kyne's Aegis": "KA",

        "Sanity's Edge": "SE",

        "Maw of Lorkhaj": "MOL",

        "Aetherian Archive": "AA",

        "Hel Ra Citadel": "HRC",

        "Asylum Sanctorium": "AS",

        "Cloudrest": "CR",
    }

    trial_code = abbreviations.get(
        trial,
        "UNK"
    )

    return f"TR-{trial_code}-{boss_order:03d}" 

