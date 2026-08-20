from dataclasses import dataclass, field
from typing import Iterable

from .build_gear import BuildGearSet
from .effects import Effect


@dataclass
class Build:
    name: str = "Unnamed Build"

    base_stats: dict[str, float] = field(default_factory=dict)
    race_id: int | None = None
    gear_sets: list[BuildGearSet] = field(default_factory=list)
    effects: list[Effect] = field(default_factory=list)

    def add_effect(self, effect: Effect) -> None:
        self.effects.append(effect)

    def add_effects(self, effects: Iterable[Effect]) -> None:
        self.effects.extend(effects)

    def add_gear_set(self, set_id: int, piece_count: int) -> None:
        self.gear_sets.append(
            BuildGearSet(
                set_id=set_id,
                piece_count=piece_count,
            )
        )

    def set_race(self, race_id: int) -> None:
        self.race_id = race_id