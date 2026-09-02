from __future__ import annotations

"""Canonical Phase 6 dynamic damage-scaling semantics for skill components."""

import re
from dataclasses import dataclass
from enum import Enum


class SkillComponentDamageScalingType(str, Enum):
    ACCUMULATED_DAMAGE = "accumulated_damage"
    PER_TICK_INCREMENT = "per_tick_increment"


@dataclass(frozen=True)
class SkillComponentDamageScaling:
    skill_rank_id: int
    coefficient_number: int
    scaling_type: SkillComponentDamageScalingType
    evidence: str
    max_bonus_fraction: float | None = None
    increment_fraction: float | None = None
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if int(self.skill_rank_id) <= 0:
            raise ValueError("skill_rank_id must be positive")
        if int(self.coefficient_number) <= 0:
            raise ValueError("coefficient_number must be positive")
        if not str(self.evidence).strip():
            raise ValueError("evidence must be non-empty")

        if self.scaling_type is SkillComponentDamageScalingType.ACCUMULATED_DAMAGE:
            if self.max_bonus_fraction is None or not 0 < float(self.max_bonus_fraction):
                raise ValueError("accumulated damage scaling requires positive max_bonus_fraction")
            if self.increment_fraction is not None:
                raise ValueError("accumulated damage scaling cannot carry increment_fraction")
        elif self.scaling_type is SkillComponentDamageScalingType.PER_TICK_INCREMENT:
            if self.increment_fraction is None or not 0 < float(self.increment_fraction):
                raise ValueError("per-tick scaling requires positive increment_fraction")
            if self.max_bonus_fraction is not None:
                raise ValueError("per-tick scaling cannot carry max_bonus_fraction")


_ACCUMULATED_DAMAGE_RE = re.compile(
    r"\bincreases?\s+based\s+on\s+the\s+amount\s+of\s+damage\b"
    r"[^.;]{0,140}?\bup\s+to\s+(?P<percent>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_PER_TICK_INCREMENT_RE = re.compile(
    r"\bincreases?\s+by\s+(?P<percent>\d+(?:\.\d+)?)\s*%\s+per\s+tick\b",
    re.IGNORECASE,
)


def extract_explicit_component_damage_scaling(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentDamageScaling, ...]:
    """Extract only explicit dynamic damage-scaling rules from owned component text.

    This records the relationship and numeric scaling only. Tick number, accumulated
    damage state, duration completion, and current combat state remain later-phase
    concerns.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    accumulated = _ACCUMULATED_DAMAGE_RE.search(text)
    if accumulated is not None:
        return (
            SkillComponentDamageScaling(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                scaling_type=SkillComponentDamageScalingType.ACCUMULATED_DAMAGE,
                max_bonus_fraction=float(accumulated.group("percent")) / 100.0,
                evidence=accumulated.group(0),
            ),
        )

    per_tick = _PER_TICK_INCREMENT_RE.search(text)
    if per_tick is not None:
        return (
            SkillComponentDamageScaling(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                scaling_type=SkillComponentDamageScalingType.PER_TICK_INCREMENT,
                increment_fraction=float(per_tick.group("percent")) / 100.0,
                evidence=per_tick.group(0),
            ),
        )

    return ()
