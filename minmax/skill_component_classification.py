from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SkillEffectKind(str, Enum):
    DAMAGE = "damage"
    HEAL = "heal"
    SHIELD = "shield"
    UTILITY = "utility"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SkillComponentClassification:
    """Verified identity for one coefficient-bearing skill component.

    Classification is deliberately keyed below the whole-skill level because
    one ESO ability can contain multiple mechanically different components
    (for example an initial direct hit plus a DoT).  Optional fields remain
    ``None`` when the imported evidence does not prove them.
    """

    skill_rank_id: int
    coefficient_number: int
    effect_kind: SkillEffectKind = SkillEffectKind.UNKNOWN
    damage_type: str | None = None
    is_dot: bool | None = None
    is_aoe: bool | None = None
    can_crit: bool | None = None
    source: str = ""
    confidence: float | None = None

    @property
    def is_damage(self) -> bool:
        return self.effect_kind is SkillEffectKind.DAMAGE

    @property
    def is_complete_damage_identity(self) -> bool:
        return (
            self.is_damage
            and self.damage_type is not None
            and self.is_dot is not None
            and self.is_aoe is not None
            and self.can_crit is not None
        )
