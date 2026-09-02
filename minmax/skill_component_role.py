from __future__ import annotations

"""Canonical Phase 6 roles for explicit secondary ability components.

A role describes what a coefficient contributes relative to the rest of the
same ability. It does not describe trigger timing, cadence, cooldowns, or
current combat state.
"""

import re
from dataclasses import dataclass
from enum import Enum


class SkillComponentRoleType(str, Enum):
    ADDITIONAL_DAMAGE = "additional_damage"
    ADDITIONAL_HEAL = "additional_heal"


@dataclass(frozen=True)
class SkillComponentRole:
    skill_rank_id: int
    coefficient_number: int
    role_type: SkillComponentRoleType
    evidence: str
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if int(self.skill_rank_id) <= 0:
            raise ValueError("skill_rank_id must be positive")
        if int(self.coefficient_number) <= 0:
            raise ValueError("coefficient_number must be positive")
        if not str(self.evidence).strip():
            raise ValueError("evidence must be non-empty")


_ANY_PLACEHOLDER_RE = re.compile(r"\$(\d+)(?!\d)")
_ADDITIONAL_DAMAGE_RE = re.compile(
    r"\badditional(?:ly)?\b[^.;]{0,90}?\$(?P<number>\d+)(?!\d)[^.;]{0,60}?\bdamage\b",
    re.IGNORECASE,
)
_ALSO_HEAL_RE = re.compile(
    r"\balso\b[^.;]{0,90}?\bheal(?:s|ed|ing)?\b[^.;]{0,70}?\$(?P<number>\d+)(?!\d)",
    re.IGNORECASE,
)
_ADDITIONAL_HEAL_RE = re.compile(
    r"\badditional(?:ly)?\b[^.;]{0,90}?\$(?P<number>\d+)(?!\d)(?:\s+health)?",
    re.IGNORECASE,
)


def _match_for_component(pattern: re.Pattern[str], text: str, coefficient_number: int) -> re.Match[str] | None:
    for match in pattern.finditer(text):
        if int(match.group("number")) == int(coefficient_number):
            return match
    return None


def extract_explicit_component_roles(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
    effect_kind: str | None,
) -> tuple[SkillComponentRole, ...]:
    """Extract explicit same-ability secondary roles without trigger inference.

    Additional damage is accepted only when the source contains another
    coefficient placeholder in the same text. This deliberately excludes
    single-coefficient triggered add-on damage such as "next Light Attack"
    effects, whose activation semantics belong to Phase 7.
    """

    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    number = int(coefficient_number)

    if effect_kind == "damage":
        match = _match_for_component(_ADDITIONAL_DAMAGE_RE, text, number)
        placeholders = {int(found.group(1)) for found in _ANY_PLACEHOLDER_RE.finditer(text)}
        if match is not None and any(other != number for other in placeholders):
            return (
                SkillComponentRole(
                    skill_rank_id=int(skill_rank_id),
                    coefficient_number=number,
                    role_type=SkillComponentRoleType.ADDITIONAL_DAMAGE,
                    evidence=match.group(0),
                ),
            )

    if effect_kind == "heal":
        match = _match_for_component(_ALSO_HEAL_RE, text, number)
        if match is None:
            match = _match_for_component(_ADDITIONAL_HEAL_RE, text, number)
        if match is not None:
            return (
                SkillComponentRole(
                    skill_rank_id=int(skill_rank_id),
                    coefficient_number=number,
                    role_type=SkillComponentRoleType.ADDITIONAL_HEAL,
                    evidence=match.group(0),
                ),
            )

    return ()
