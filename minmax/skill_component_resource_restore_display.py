from __future__ import annotations

"""Phase 6 semantics for coefficient placeholders that display resource restores.

These rows describe the current amount produced by an explicit static restore
rule. They do not evaluate build counts, Max Resources, triggers, cooldowns, or
current combat state.
"""

import re
from dataclasses import dataclass
from enum import Enum


class SkillComponentRestoreDisplayResource(str, Enum):
    HEALTH = "health"
    MAGICKA = "magicka"
    STAMINA = "stamina"


class SkillComponentRestoreDisplayBasis(str, Enum):
    FLAT_PER_UNIT = "flat_per_unit"
    PERCENT_MAX_RESOURCE = "percent_max_resource"


class SkillComponentRestoreDisplayDriver(str, Enum):
    HEAVY_ARMOR_PIECES_EQUIPPED = "heavy_armor_pieces_equipped"


@dataclass(frozen=True)
class SkillComponentResourceRestoreDisplay:
    skill_rank_id: int
    coefficient_number: int
    resources: tuple[SkillComponentRestoreDisplayResource, ...]
    basis: SkillComponentRestoreDisplayBasis
    evidence: str
    amount_per_unit: float | None = None
    amount_fraction: float | None = None
    driver: SkillComponentRestoreDisplayDriver | None = None
    source: str = "coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not self.resources:
            raise ValueError("resources must be non-empty")
        if not self.evidence:
            raise ValueError("evidence must be non-empty")
        if self.basis is SkillComponentRestoreDisplayBasis.FLAT_PER_UNIT:
            if self.amount_per_unit is None or self.amount_per_unit <= 0:
                raise ValueError("flat-per-unit displays require positive amount_per_unit")
            if self.driver is None:
                raise ValueError("flat-per-unit displays require a count driver")
            if self.amount_fraction is not None:
                raise ValueError("flat-per-unit displays do not carry amount_fraction")
        elif self.basis is SkillComponentRestoreDisplayBasis.PERCENT_MAX_RESOURCE:
            if self.amount_fraction is None or not (0.0 < self.amount_fraction <= 1.0):
                raise ValueError("percent-Max-resource displays require amount_fraction in (0, 1]")
            if self.amount_per_unit is not None or self.driver is not None:
                raise ValueError("percent-Max-resource displays do not carry count metadata")


_CURRENT_BONUS_RE = re.compile(r"\bcurrent\s+bonus\s*:\s*(?P<body>[^.;]+)", re.IGNORECASE)


def _placeholder_resource(body: str, coefficient_number: int) -> SkillComponentRestoreDisplayResource | None:
    match = re.search(
        rf"\${int(coefficient_number)}(?!\d)\s*(health|magicka|stamina)\b",
        body,
        re.IGNORECASE,
    )
    if match is None:
        return None
    return SkillComponentRestoreDisplayResource(match.group(1).casefold())


def extract_explicit_component_resource_restore_display(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    component_text: str,
) -> tuple[SkillComponentResourceRestoreDisplay, ...]:
    text = " ".join(str(component_text or "").split())
    if not text:
        return ()

    current_matches = tuple(_CURRENT_BONUS_RE.finditer(text))
    if not current_matches:
        return ()

    # Undaunted Command shape: an explicit percent of Max Health/Stamina/Magicka
    # followed by one current-value placeholder for each resource.
    percent_match = re.search(
        r"\b(?:restore|restores)\s+(?P<percent>\d+(?:\.\d+)?)\s*%\s+of\s+your\s+max\s+"
        r"health\s*,\s*stamina\s*,\s*and\s*magicka\b",
        text,
        re.IGNORECASE,
    )
    if percent_match is not None:
        percent = float(percent_match.group("percent"))
        if 0.0 < percent <= 100.0:
            for current in current_matches:
                resource = _placeholder_resource(current.group("body"), coefficient_number)
                if resource is None:
                    continue
                return (
                    SkillComponentResourceRestoreDisplay(
                        skill_rank_id=int(skill_rank_id),
                        coefficient_number=int(coefficient_number),
                        resources=(resource,),
                        basis=SkillComponentRestoreDisplayBasis.PERCENT_MAX_RESOURCE,
                        amount_fraction=percent / 100.0,
                        evidence=f"{percent_match.group(0)}; {current.group(0)}",
                    ),
                )

    # Constitution shape: a flat restore to two coordinated resources for every
    # Heavy Armor piece, followed later by one placeholder showing the aggregate.
    constitution = re.search(
        r"\b(?:restore|restores)\s+(?P<amount>\d+(?:\.\d+)?)\s+magicka\s+and\s+stamina\s+"
        r"when\s+you\s+take\s+damage\s+for\s+each\s+piece\s+of\s+heavy\s+armor\s+equipped\b",
        text,
        re.IGNORECASE,
    )
    if constitution is not None:
        placeholder = re.search(
            rf"\bcurrent\s+bonus\s*:\s*\${int(coefficient_number)}(?!\d)\b",
            text[constitution.end():],
            re.IGNORECASE,
        )
        if placeholder is not None:
            amount = float(constitution.group("amount"))
            if amount > 0.0:
                return (
                    SkillComponentResourceRestoreDisplay(
                        skill_rank_id=int(skill_rank_id),
                        coefficient_number=int(coefficient_number),
                        resources=(
                            SkillComponentRestoreDisplayResource.MAGICKA,
                            SkillComponentRestoreDisplayResource.STAMINA,
                        ),
                        basis=SkillComponentRestoreDisplayBasis.FLAT_PER_UNIT,
                        amount_per_unit=amount,
                        driver=SkillComponentRestoreDisplayDriver.HEAVY_ARMOR_PIECES_EQUIPPED,
                        evidence=f"{constitution.group(0)}; {placeholder.group(0)}",
                    ),
                )

    return ()
