from __future__ import annotations

"""Canonical Phase 6 consequences for conditioned skill components.

Phase 6 records what a supported condition does to a component. It does not
resolve trigger timing, current combat state, uptime, or interpolation across an
``up to`` damage-scaling range; those belong to later phases.
"""

import re
from dataclasses import dataclass
from enum import Enum

from .skill_component_condition import SkillComponentCondition


class SkillComponentConditionalConsequenceType(str, Enum):
    ACTIVATES_COMPONENT = "activates_component"
    AMPLIFIES_DAMAGE = "amplifies_damage"


@dataclass(frozen=True)
class SkillComponentConditionalConsequence:
    skill_rank_id: int
    coefficient_number: int
    consequence_type: SkillComponentConditionalConsequenceType
    condition: SkillComponentCondition
    maximum_bonus_fraction: float | None
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if self.maximum_bonus_fraction is not None and self.maximum_bonus_fraction < 0.0:
            raise ValueError("maximum_bonus_fraction cannot be negative")
        if not self.evidence:
            raise ValueError("evidence must preserve the source wording")


_DAMAGE_AMPLIFICATION_RE = re.compile(
    r"\b(?:deal(?:s|ing)?\s+)?up\s+to\s+(\d+(?:\.\d+)?)\s*%\s+more\s+damage\b",
    flags=re.IGNORECASE,
)


def extract_explicit_conditional_consequences(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    condition: SkillComponentCondition,
    component_text: str,
    effect_kind: str | None,
) -> tuple[SkillComponentConditionalConsequence, ...]:
    """Extract only explicit consequence facts for one conditioned component.

    Damage amplification requires direct ``up to N% more damage`` wording.
    Otherwise a supported damage/heal/shield component with an explicit
    condition is represented as condition-gated activation. Temporal trigger
    details remain unresolved for Phase 7.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    amplification = _DAMAGE_AMPLIFICATION_RE.search(text)
    if effect_kind == "damage" and amplification is not None:
        bonus_percent = float(amplification.group(1))
        return (
            SkillComponentConditionalConsequence(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                consequence_type=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
                condition=condition,
                maximum_bonus_fraction=bonus_percent / 100.0,
                evidence=amplification.group(0),
            ),
        )

    if effect_kind in {"damage", "heal", "shield"}:
        return (
            SkillComponentConditionalConsequence(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                consequence_type=SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT,
                condition=condition,
                maximum_bonus_fraction=None,
                evidence=condition.evidence,
            ),
        )

    return ()
