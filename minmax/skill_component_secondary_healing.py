from __future__ import annotations

"""Canonical Phase 6 secondary healing relationships for skill components.

This module describes healing whose amount is explicitly derived from damage
caused/dealt by the same coefficient-bearing component. It does not evaluate
triggers, cadence, stack state, or combat state.
"""

import re
from dataclasses import dataclass
from enum import Enum


class SecondaryHealingBasis(str, Enum):
    DAMAGE_DEALT = "damage_dealt"


@dataclass(frozen=True)
class SkillComponentSecondaryHealing:
    skill_rank_id: int
    coefficient_number: int
    basis: SecondaryHealingBasis
    fraction: float | None
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if self.fraction is not None and not (0.0 < self.fraction <= 1.0):
            raise ValueError("fraction must be in (0, 1]")
        if not self.evidence:
            raise ValueError("evidence must preserve source wording")


_PERCENT_DAMAGE_HEAL_RE = re.compile(
    r"\b(?:heal|heals|healing)\b[^.;]{0,50}?"
    r"(?P<percent>\d+(?:\.\d+)?)\s*%\s+of\s+(?:the\s+)?damage\s+(?:dealt|done|caused)\b",
    flags=re.IGNORECASE,
)
_FULL_DAMAGE_HEAL_RE = re.compile(
    r"\b(?:heal|heals|healing)\b[^.;]{0,30}?for\s+(?:the\s+)?damage\s+(?:dealt|done|caused)\b",
    flags=re.IGNORECASE,
)


def extract_explicit_secondary_healing(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentSecondaryHealing, ...]:
    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    percent_match = _PERCENT_DAMAGE_HEAL_RE.search(text)
    if percent_match is not None:
        percent = float(percent_match.group("percent"))
        if not (0.0 < percent <= 100.0):
            return ()
        return (
            SkillComponentSecondaryHealing(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                basis=SecondaryHealingBasis.DAMAGE_DEALT,
                fraction=percent / 100.0,
                evidence=percent_match.group(0),
            ),
        )

    full_match = _FULL_DAMAGE_HEAL_RE.search(text)
    if full_match is not None:
        return (
            SkillComponentSecondaryHealing(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                basis=SecondaryHealingBasis.DAMAGE_DEALT,
                fraction=1.0,
                evidence=full_match.group(0),
            ),
        )

    return ()
