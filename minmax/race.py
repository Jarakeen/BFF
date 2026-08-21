from dataclasses import dataclass


@dataclass(frozen=True)
class Race:
    id: int
    name: str
    alliance: str | None
    association: str | None


@dataclass(frozen=True)
class RaceStat:
    id: int
    race_id: int
    stat: str
    value: int