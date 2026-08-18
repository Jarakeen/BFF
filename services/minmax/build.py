from dataclasses import dataclass, field
from typing import Iterable

from .effects import Effect


@dataclass
class Build:
    name: str = "Unnamed Build"

    base_stats: dict[str, float] = field(default_factory=dict)
    effects: list[Effect] = field(default_factory=list)

    def add_effect(self, effect: Effect) -> None:
        self.effects.append(effect)

    def add_effects(self, effects: Iterable[Effect]) -> None:
        self.effects.extend(effects)