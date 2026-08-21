from dataclasses import dataclass


@dataclass(frozen=True)
class GearSet:
    id: int
    name: str
    category: str | None
    max_equip_count: int | None


@dataclass(frozen=True)
class GearSetBonus:
    id: int
    set_id: int
    piece_count: int
    description: str
