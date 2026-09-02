from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class SkillComponentUtilityEffectType(str, Enum):
    STUN = "stun"
    IMMOBILIZE = "immobilize"
    MOVEMENT_SPEED_REDUCTION = "movement_speed_reduction"
    MOVEMENT_SPEED_INCREASE = "movement_speed_increase"
    KNOCKBACK = "knockback"
    PULL = "pull"
    TAUNT = "taunt"
    INTERRUPT_IMMUNITY = "interrupt_immunity"


@dataclass(frozen=True)
class SkillComponentUtilityEffect:
    skill_rank_id: int
    coefficient_number: int
    effect_type: SkillComponentUtilityEffectType
    evidence: str
    magnitude_fraction: float | None = None
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if int(self.skill_rank_id) <= 0:
            raise ValueError("skill_rank_id must be positive")
        if int(self.coefficient_number) <= 0:
            raise ValueError("coefficient_number must be positive")
        if not str(self.evidence).strip():
            raise ValueError("evidence must be non-empty")
        if self.magnitude_fraction is not None and not 0 < float(self.magnitude_fraction) <= 1:
            raise ValueError("magnitude_fraction must be in (0, 1]")
        if self.effect_type not in {
            SkillComponentUtilityEffectType.MOVEMENT_SPEED_REDUCTION,
            SkillComponentUtilityEffectType.MOVEMENT_SPEED_INCREASE,
        } and self.magnitude_fraction is not None:
            raise ValueError("only movement-speed effects may carry magnitude_fraction")


_SPEED_REDUCTION_RE = re.compile(
    r"\b(?:reduce|reduces|reduced|reducing)\b[^.;]{0,50}?\bmovement\s+speed\b"
    r"[^.;]{0,30}?\bby\s+(?P<percent>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_SPEED_INCREASE_RE = re.compile(
    r"\b(?:increase|increases|increased|increasing)\b[^.;]{0,50}?\bmovement\s+speed\b"
    r"[^.;]{0,30}?\bby\s+(?P<percent>\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)


def _first_evidence(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(text)
    return match.group(0).strip() if match is not None else None


def extract_explicit_component_utility_effects(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentUtilityEffect, ...]:
    """Extract explicit non-temporal utility effects from one owned component segment.

    Utility nouns used only as conditions or prior-state references do not count.
    For example, ``if the stun lasts`` and ``after the stun ends`` describe the
    context in which the coefficient occurs; they do not prove that the component
    itself applies a stun.

    Duration, cadence, trigger frequency, chance, and current state are deliberately
    excluded from this Phase 6 primitive.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    results: list[SkillComponentUtilityEffect] = []

    speed_reduction = _SPEED_REDUCTION_RE.search(text)
    if speed_reduction is not None:
        results.append(
            SkillComponentUtilityEffect(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                effect_type=SkillComponentUtilityEffectType.MOVEMENT_SPEED_REDUCTION,
                magnitude_fraction=float(speed_reduction.group("percent")) / 100.0,
                evidence=speed_reduction.group(0),
            )
        )

    speed_increase = _SPEED_INCREASE_RE.search(text)
    if speed_increase is not None:
        results.append(
            SkillComponentUtilityEffect(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                effect_type=SkillComponentUtilityEffectType.MOVEMENT_SPEED_INCREASE,
                magnitude_fraction=float(speed_increase.group("percent")) / 100.0,
                evidence=speed_increase.group(0),
            )
        )

    simple_patterns: tuple[tuple[SkillComponentUtilityEffectType, re.Pattern[str]], ...] = (
        (
            SkillComponentUtilityEffectType.STUN,
            re.compile(
                r"\b(?:stuns|stunned|stunning)\b|(?:^|\b(?:and|then|to)\s+)stun\b",
                re.IGNORECASE,
            ),
        ),
        (
            SkillComponentUtilityEffectType.IMMOBILIZE,
            re.compile(
                r"\b(?:immobilizes|immobilized|immobilizing)\b|(?:^|\b(?:and|then|to)\s+)immobilize\b",
                re.IGNORECASE,
            ),
        ),
        (
            SkillComponentUtilityEffectType.KNOCKBACK,
            re.compile(
                r"\b(?:knockback|knock(?:s|ed|ing)?\s+(?:\w+\s+){0,2}?back)\b",
                re.IGNORECASE,
            ),
        ),
        (
            SkillComponentUtilityEffectType.PULL,
            re.compile(r"\b(?:pulls|pulled|pulling)\b|(?:^|\b(?:and|then|to)\s+)pull\b", re.IGNORECASE),
        ),
        (
            SkillComponentUtilityEffectType.TAUNT,
            re.compile(r"\b(?:taunts|taunted|taunting)\b|(?:^|\b(?:and|then|to)\s+)taunt\b", re.IGNORECASE),
        ),
        (
            SkillComponentUtilityEffectType.INTERRUPT_IMMUNITY,
            re.compile(
                r"\b(?:grant(?:s|ed|ing)?|gain(?:s|ed|ing)?|provide(?:s|d|ing)?)\b"
                r"[^.;]{0,45}?\binterrupt\s+immunity\b",
                re.IGNORECASE,
            ),
        ),
    )
    for effect_type, pattern in simple_patterns:
        evidence = _first_evidence(text, pattern)
        if evidence is None:
            continue
        results.append(
            SkillComponentUtilityEffect(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                effect_type=effect_type,
                evidence=evidence,
            )
        )

    return tuple(results)
