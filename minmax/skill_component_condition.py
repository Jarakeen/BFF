from __future__ import annotations

"""Canonical Phase 6 conditions attached to coefficient-bearing skill components.

Phase 6 records what condition is explicitly stated by the component-local
source text. It does not evaluate whether that condition is currently true;
combat-state evaluation belongs to later phases.
"""

import re
from dataclasses import dataclass
from enum import Enum


class SkillComponentConditionType(str, Enum):
    TARGET_HEALTH_BELOW_PERCENT = "target_health_below_percent"


@dataclass(frozen=True)
class SkillComponentCondition:
    skill_rank_id: int
    coefficient_number: int
    condition_type: SkillComponentConditionType
    threshold: float
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not (0.0 < self.threshold <= 1.0):
            raise ValueError("threshold must be a fraction in (0, 1]")
        if not self.evidence:
            raise ValueError("evidence must preserve the source wording")


_HEALTH_THRESHOLD_RE = re.compile(
    r"\b(?:below|under|less\s+than)\s+(\d+(?:\.\d+)?)\s*%\s+(?:of\s+)?(?:their|the\s+target(?:'s)?|target|enemy(?:'s)?|its)?\s*health\b",
    flags=re.IGNORECASE,
)


def extract_explicit_component_conditions(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentCondition, ...]:
    """Extract only explicit, normalized component-local conditions.

    The caller must supply text already scoped to the coefficient component.
    This function deliberately does not interpret generic words such as ``if``
    or ``after`` without a supported mechanical condition pattern.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    match = _HEALTH_THRESHOLD_RE.search(text)
    if match is None:
        return ()

    percent = float(match.group(1))
    if not (0.0 < percent <= 100.0):
        return ()

    return (
        SkillComponentCondition(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            condition_type=SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
            threshold=percent / 100.0,
            evidence=match.group(0),
        ),
    )
