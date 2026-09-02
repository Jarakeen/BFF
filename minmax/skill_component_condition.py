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
_ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
}


class SkillComponentConditionType(str, Enum):
    TARGET_HEALTH_BELOW_PERCENT = "target_health_below_percent"
    SELF_HEALTH_BELOW_PERCENT = "self_health_below_percent"


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
_SELF_HEALTH_THRESHOLD_RE = re.compile(
    r"\b(?:your|the\s+caster(?:'s)?|caster(?:'s)?)\s+health\s+(?:drops?|falls?|is)\s+"
    r"(?:below|under|less\s+than)\s+(\d+(?:\.\d+)?)\s*%\b",
    flags=re.IGNORECASE,
)
_ORDINAL_HIT_RE = re.compile(
    r"\b(first|second|third|fourth|fifth|sixth)\s+(?:hit|attack|strike)\b",
    flags=re.IGNORECASE,
)


def _condition_from_match(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    match: re.Match[str],
    condition_type: SkillComponentConditionType = SkillComponentConditionType.TARGET_HEALTH_BELOW_PERCENT,
) -> tuple[SkillComponentCondition, ...]:
    percent = float(match.group(1))
    if not (0.0 < percent <= 100.0):
        return ()
    return (
        SkillComponentCondition(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            condition_type=condition_type,
            threshold=percent / 100.0,
            evidence=match.group(0),
        ),
    )


def _component_segment(text: str, coefficient_number: int) -> str:
    """Return the forward clause owned by ``$coefficient_number``."""

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
    end = len(text) if current_index + 1 >= len(placeholders) else placeholders[current_index + 1].start()
    return text[start:end].strip()


def explicit_ordinal_condition_owner(text: str) -> int | None:
    """Return a component number when source text explicitly names its hit ordinal.

    This is intentionally narrow. It recognizes only direct wording such as
    ``the second hit`` / ``third attack`` in the same sentence as a supported
    target-health threshold. It never infers ordinal ownership from prose order alone.
    """

    normalized = " ".join(str(text or "").split())
    for sentence in re.split(r"(?<=[.;])\s+", normalized):
        threshold = _HEALTH_THRESHOLD_RE.search(sentence)
        ordinal = _ORDINAL_HIT_RE.search(sentence)
        if threshold is not None and ordinal is not None:
            return _ORDINALS[ordinal.group(1).casefold()]
    return None


def extract_explicit_ordinal_component_conditions(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    source_text: str,
) -> tuple[SkillComponentCondition, ...]:
    """Extract a target-health condition explicitly assigned to an ordinal hit/attack."""

    normalized = " ".join(str(source_text or "").split())
    for sentence in re.split(r"(?<=[.;])\s+", normalized):
        ordinal = _ORDINAL_HIT_RE.search(sentence)
        threshold = _HEALTH_THRESHOLD_RE.search(sentence)
        if ordinal is None or threshold is None:
            continue
        if _ORDINALS[ordinal.group(1).casefold()] != int(coefficient_number):
            continue
        return _condition_from_match(
            skill_rank_id=skill_rank_id,
            coefficient_number=coefficient_number,
            match=threshold,
        )
    return ()


def extract_explicit_component_conditions(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentCondition, ...]:
    """Extract only explicit, normalized coefficient-owned conditions."""

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    segment = _component_segment(text, int(coefficient_number))
    if not segment:
        return ()

    self_match = _SELF_HEALTH_THRESHOLD_RE.search(segment)
    if self_match is not None:
        return _condition_from_match(
            skill_rank_id=skill_rank_id,
            coefficient_number=coefficient_number,
            match=self_match,
            condition_type=SkillComponentConditionType.SELF_HEALTH_BELOW_PERCENT,
        )

    target_match = _HEALTH_THRESHOLD_RE.search(segment)
    if target_match is None:
        return ()

    return _condition_from_match(
        skill_rank_id=skill_rank_id,
        coefficient_number=coefficient_number,
        match=target_match,
    )
