from dataclasses import dataclass, field


# --------------------------------------------------
# Mechanics
# --------------------------------------------------

@dataclass
class Mechanic:
    name: str
    description: str

    aliases: list[str] = field(default_factory=list)

    damage_type: str = ""

    interruptible: bool = False
    blockable: bool = False
    dodgeable: bool = False
    cleanseable: bool = False

    priority: int = 0

    tags: list[str] = field(default_factory=list)


# --------------------------------------------------
# Health
# --------------------------------------------------

@dataclass
class Health:
    normal: int = 0
    veteran: int = 0
    hardmode: int = 0


# --------------------------------------------------
# Dialogue
# --------------------------------------------------

@dataclass
class DialogueGroup:
    trigger: str
    lines: list[str] = field(default_factory=list)


# --------------------------------------------------
# Boss
# --------------------------------------------------

@dataclass
class Boss:
    archive_no: str

    name: str

    trial: str
    arena: str = ""

    race: str = ""
    faction: str = ""
    condition: str = ""

    boss_order: int = 0

    health: Health = field(default_factory=Health)

    mechanics: list[Mechanic] = field(default_factory=list)
    hardmode_mechanics: list[Mechanic] = field(default_factory=list)

    dialogue: list[DialogueGroup] = field(default_factory=list)

    notes: list[str] = field(default_factory=list)

    quests: list[str] = field(default_factory=list)