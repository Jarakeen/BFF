from __future__ import annotations

"""Canonical Phase 6 trigger relationships for coefficient-local skill components.

Phase 6 records what event makes a component eligible to occur. Phase 7 owns
runtime event detection, timing windows, cadence, cooldowns, and trigger counts.
"""

from dataclasses import dataclass
from enum import Enum


class SkillComponentTriggerType(str, Enum):
    ABILITY_TRIGGERED = "ability_triggered"
    LIGHT_ATTACK = "light_attack"
    HEAVY_ATTACK = "heavy_attack"
    LIGHT_OR_HEAVY_ATTACK = "light_or_heavy_attack"
    EFFECT_ENDED = "effect_ended"
    STUN_ENDED = "stun_ended"
    STUN_FULL_DURATION = "stun_full_duration"
    TARGET_TAKES_DAMAGE = "target_takes_damage"
    ENEMY_DIES_AFTER_STRIKE = "enemy_dies_after_strike"
    DAMAGE_OVER_TIME_EFFECT_ENDED = "damage_over_time_effect_ended"


@dataclass(frozen=True)
class SkillComponentTriggerRelationship:
    skill_rank_id: int
    coefficient_number: int
    trigger_type: SkillComponentTriggerType
    evidence: str
    condition: str | None = None
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not self.evidence:
            raise ValueError("evidence must preserve the source wording")
