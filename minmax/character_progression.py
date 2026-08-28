from __future__ import annotations

from dataclasses import dataclass


MAX_ATTRIBUTE_POINTS = 64
MAX_CHAMPION_POINTS = 3600
MAX_SLOTTED_PER_TREE = 4


@dataclass(frozen=True)
class AttributeAllocation:
    """The character's fixed pool of level-up attribute points."""

    health: int = 0
    magicka: int = 0
    stamina: int = 0

    def __post_init__(self) -> None:
        values = (self.health, self.magicka, self.stamina)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise TypeError("attribute allocations must be integers")
        if any(value < 0 for value in values):
            raise ValueError("attribute allocations cannot be negative")
        if self.total > MAX_ATTRIBUTE_POINTS:
            raise ValueError(f"attribute allocation cannot exceed {MAX_ATTRIBUTE_POINTS} points")

    @property
    def total(self) -> int:
        return self.health + self.magicka + self.stamina

    @property
    def is_complete(self) -> bool:
        return self.total == MAX_ATTRIBUTE_POINTS


@dataclass(frozen=True)
class ChampionPointState:
    """Purchased and active CP state relevant to calculation, not CP earning speed."""

    total: int = 0
    blue_slotted: int = 0
    red_slotted: int = 0
    green_slotted: int = 0

    def __post_init__(self) -> None:
        values = (self.total, self.blue_slotted, self.red_slotted, self.green_slotted)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise TypeError("champion point values must be integers")
        if self.total < 0 or self.total > MAX_CHAMPION_POINTS:
            raise ValueError(f"champion points must be between 0 and {MAX_CHAMPION_POINTS}")
        if any(value < 0 or value > MAX_SLOTTED_PER_TREE for value in values[1:]):
            raise ValueError(f"no CP tree may have more than {MAX_SLOTTED_PER_TREE} slotted abilities")


@dataclass(frozen=True)
class CharacterProgression:
    """Progression state needed by MinMax; acquisition mechanics are intentionally excluded."""

    level: int = 50
    attributes: AttributeAllocation = AttributeAllocation()
    champion_points: ChampionPointState = ChampionPointState()

    def __post_init__(self) -> None:
        if isinstance(self.level, bool) or not isinstance(self.level, int):
            raise TypeError("level must be an integer")
        if self.level < 1 or self.level > 50:
            raise ValueError("character level must be between 1 and 50")
