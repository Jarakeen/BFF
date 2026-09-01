from __future__ import annotations

"""Canonical Phase 6 conditions attached to coefficient-bearing skill components.

Phase 6 records what condition is explicitly stated by the component-local
source text. It does not evaluate whether that condition is currently true;
combat-state evaluation belongs to later phases.
"""

import re
from dataclasses import dataclass
from enum import Enum


_ANY_PLACEHOLDER_RE = re.compile(r"\$(\d+)(?!\d)")


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


def _component_segment(text: str, coefficient_number: int) -> str:
    """Return the forward clause owned by ``$coefficient_number``.

    Single-placeholder fragments keep their full local sentence so conditions
    written before the scalar remain available. Multi-placeholder fragments are
    stricter: each component owns wording from its own placeholder forward until
    the next placeholder, preventing one coefficient from inheriting another
    component's condition.
    """

    placeholders = list(_ANY_PLACEHOLDER_RE.finditer(text))
    matches = [
        (index, match)
        for index, match in enumerate(placeholders)
        if int(match.group(1)) == int(coefficient_number)
    ]
    if not matches:
        return ""
    if len(placeholders) == 1:
        return text

    current_index, current = matches[0]
    start = current.start()
    end = (
        len(text)
        if current_index + 1 >= len(placeholders)
        else placeholders[current_index + 1].start()
    )
    return text[start:end].strip()


def extract_explicit_component_conditions(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentCondition, ...]:
    """Extract only explicit, normalized coefficient-owned conditions.

    Generic words such as ``if`` or ``after`` are not interpreted without a
    supported mechanical condition pattern. In multi-placeholder source text,
    condition ownership is scoped to the current coefficient's forward clause.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    segment = _component_segment(text, int(coefficient_number))
    if not segment:
        return ()

    match = _HEALTH_THRESHOLD_RE.search(segment)
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
