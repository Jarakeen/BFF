from __future__ import annotations

"""Canonical Phase 6 healing derived from the actor's missing Health.

This module records only the explicit healing amount relationship. Cadence,
channel duration, trigger state, and combat-state evaluation remain later-phase
concerns.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SkillComponentMissingHealthHealing:
    skill_rank_id: int
    coefficient_number: int
    fraction: float
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not (0.0 < self.fraction <= 1.0):
            raise ValueError("fraction must be in (0, 1]")
        if not self.evidence:
            raise ValueError("evidence must preserve source wording")


_MISSING_HEALTH_HEAL_RE = re.compile(
    r"\b(?:heal|heals|healing|healed)\b[^.;]{0,50}?"
    r"(?P<percent>\d+(?:\.\d+)?)\s*%\s+of\s+(?:your\s+)?missing\s*health\b",
    flags=re.IGNORECASE,
)


def extract_explicit_missing_health_healing(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentMissingHealthHealing, ...]:
    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    match = _MISSING_HEALTH_HEAL_RE.search(text)
    if match is None:
        return ()

    percent = float(match.group("percent"))
    if not (0.0 < percent <= 100.0):
        return ()

    return (
        SkillComponentMissingHealthHealing(
            skill_rank_id=int(skill_rank_id),
            coefficient_number=int(coefficient_number),
            fraction=percent / 100.0,
            evidence=match.group(0),
        ),
    )
