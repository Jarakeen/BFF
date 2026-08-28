from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from .base_character_state import BaseCharacterState
from .character_progression import CharacterProgression

if TYPE_CHECKING:
    from .core_stat_calculator import CoreStatState


class CombatEnvironment(str, Enum):
    PVE = "pve"
    PVP = "pvp"


class ScalingRule(str, Enum):
    HEALTH = "health"
    MAGICKA = "magicka"
    STAMINA = "stamina"
    HIGHEST_RESOURCE = "highest_resource"
    HIGHEST_ATTRIBUTE = "highest_attribute"
    FIXED = "fixed"

    def resolve(self, state: BaseCharacterState) -> int:
        if self is ScalingRule.HEALTH:
            return state.max_health
        if self is ScalingRule.MAGICKA:
            return state.max_magicka
        if self is ScalingRule.STAMINA:
            return state.max_stamina
        if self is ScalingRule.HIGHEST_RESOURCE:
            return max(state.max_magicka, state.max_stamina)
        if self is ScalingRule.HIGHEST_ATTRIBUTE:
            return max(state.max_health, state.max_magicka, state.max_stamina)
        if self is ScalingRule.FIXED:
            return 0
        raise ValueError(f"unsupported scaling rule: {self}")


@dataclass(frozen=True)
class BuildCalculationContext:
    """Immutable calculation snapshot for one character/build evaluation."""

    character_id: str
    build_id: str
    progression: CharacterProgression
    character_state: BaseCharacterState
    core_state: CoreStatState | None = None
    environment: CombatEnvironment = CombatEnvironment.PVE
    target_type: str = "monster"
    target_resistance: float | None = None
    target_count: int = 1
    fight_duration: float | None = None
    selected_skills: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.character_id.strip():
            raise ValueError("character_id is required")
        if not self.build_id.strip():
            raise ValueError("build_id is required")
        if self.target_count < 1:
            raise ValueError("target_count must be at least 1")
        if self.fight_duration is not None and self.fight_duration <= 0:
            raise ValueError("fight_duration must be positive when supplied")

    def resolve_scaling(self, rule: ScalingRule) -> int:
        return rule.resolve(self.character_state)
