from __future__ import annotations

"""Canonical Phase 6 trigger relationships for coefficient-local skill components.

Phase 6 records what event makes a component eligible to occur. Phase 7 owns
runtime event detection, timing windows, cadence, cooldowns, and trigger counts.
"""

import re
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


def _contains_placeholder(text: str, coefficient_number: int) -> bool:
    return re.search(rf"\${int(coefficient_number)}(?!\d)", text) is not None


def _condition_from_text(text: str) -> str | None:
    if re.search(r"\bwhile\s+transformed\b", text, re.IGNORECASE):
        return "while_transformed"
    return None


def extract_explicit_component_trigger_relationships(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentTriggerRelationship, ...]:
    """Extract explicit event -> component relationships from canonical wording.

    The extractor intentionally records only the event identity. Durations,
    trigger windows, cadence, cooldowns, and current event state are Phase 7.
    Generic connective words such as ``when`` and ``after`` are not sufficient;
    each promotion must match a concrete event phrase.
    """

    text = " ".join(str(component_text or "").split())
    if not text or not _contains_placeholder(text, coefficient_number):
        return ()

    placeholder = rf"\${int(coefficient_number)}(?!\d)"
    condition = _condition_from_text(text)
    patterns: tuple[tuple[SkillComponentTriggerType, str], ...] = (
        (
            SkillComponentTriggerType.DAMAGE_OVER_TIME_EFFECT_ENDED,
            rf"\bwhen\s+(?:your|their)\b[^.;]{{0,80}}?damage\s+over\s+time\s+effects?\s+end\b[^.;]{{0,140}}?{placeholder}",
        ),
        (
            SkillComponentTriggerType.STUN_FULL_DURATION,
            rf"\bif\s+the\s+stun\s+lasts\s+the\s+full\s+duration\b[^.;]{{0,120}}?{placeholder}|{placeholder}[^.;]{{0,80}}?\bif\s+the\s+stun\s+lasts\s+the\s+full\s+duration\b",
        ),
        (
            SkillComponentTriggerType.STUN_ENDED,
            rf"\bafter\s+the\s+stun\s+ends\b[^.;]{{0,160}}?{placeholder}",
        ),
        (
            SkillComponentTriggerType.ENEMY_DIES_AFTER_STRIKE,
            rf"{placeholder}[^.;]{{0,100}}?\bif\s+the\s+enemy\s+dies\b[^.;]{{0,100}}?\bbeing\s+struck\b",
        ),
        (
            SkillComponentTriggerType.TARGET_TAKES_DAMAGE,
            rf"{placeholder}[^.;]{{0,100}}?\beach\s+time\s+(?:they|the\s+target)\s+take(?:s)?\s+damage\b",
        ),
        (
            SkillComponentTriggerType.LIGHT_OR_HEAVY_ATTACK,
            rf"\b(?:light\s+attacks?\s+and\s+(?:fully-charged\s+)?heavy\s+attacks?|light\s+and\s+heavy\s+attacks?)\b[^.;]{{0,180}}?{placeholder}",
        ),
        (
            SkillComponentTriggerType.HEAVY_ATTACK,
            rf"\b(?:fully-charged\s+)?heavy\s+attacks?\b[^.;]{{0,160}}?{placeholder}",
        ),
        (
            SkillComponentTriggerType.LIGHT_ATTACK,
            rf"\blight\s+attacks?\b[^.;]{{0,160}}?{placeholder}",
        ),
        (
            SkillComponentTriggerType.ABILITY_TRIGGERED,
            rf"\bwhen\s+triggered\b[^.;]{{0,180}}?{placeholder}",
        ),
        (
            SkillComponentTriggerType.EFFECT_ENDED,
            rf"\b(?:when|after)\s+the\s+(?:effect|shield)\s+ends\b[^.;]{{0,180}}?{placeholder}",
        ),
    )

    for trigger_type, pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match is None:
            continue
        return (
            SkillComponentTriggerRelationship(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                trigger_type=trigger_type,
                evidence=match.group(0),
                condition=condition,
            ),
        )

    return ()
