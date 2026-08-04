from dataclasses import dataclass, field


@dataclass
class Mechanic:
    name: str
    description: str
    damage: str = ""
    counter: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class Boss:
    archive_no: str

    name: str
    trial: str
    boss_order: int

    mechanics: list[Mechanic] = field(default_factory=list)
    hardmode_mechanics: list[Mechanic] = field(default_factory=list)

    dialogue: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)