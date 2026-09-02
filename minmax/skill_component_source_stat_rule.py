from __future__ import annotations

"""Phase 6 stat rules recovered from raw placeholder-aligned source sentences.

Some UESP skill rows retain ``<<N>>`` in ``raw_description`` while the matching
``coef_description`` prose contains a literal value instead of ``$N``. The raw
placeholder establishes which mechanic belongs to the coefficient slot; the
coefficientized display prose supplies the current literal magnitude.
"""

import re
from dataclasses import dataclass
from enum import Enum

from .stat_ids import StatId


class SkillComponentSourceStatRuleDriver(str, Enum):
    DUAL_WIELD_MACES_EQUIPPED = "dual_wield_maces_equipped"
    GRAVELORD_ABILITY_SLOTTED = "gravelord_ability_slotted"


class SkillComponentSourceStatRuleBasis(str, Enum):
    FLAT_PER_UNIT = "flat_per_unit"
    CONDITIONAL_FRACTION = "conditional_fraction"


@dataclass(frozen=True)
class SkillComponentSourceStatRule:
    skill_rank_id: int
    coefficient_number: int
    stats: tuple[StatId, ...]
    driver: SkillComponentSourceStatRuleDriver
    amount_basis: SkillComponentSourceStatRuleBasis
    amount: float
    evidence: str
    target_health_below_fraction: float | None = None
    required_min_count: int = 1
    source: str = "raw_description+coef_description"

    def __post_init__(self) -> None:
        if self.skill_rank_id <= 0:
            raise ValueError("skill_rank_id must be positive")
        if self.coefficient_number <= 0:
            raise ValueError("coefficient_number must be positive")
        if not self.stats:
            raise ValueError("stats must be non-empty")
        if self.amount <= 0:
            raise ValueError("amount must be positive")
        if self.required_min_count <= 0:
            raise ValueError("required_min_count must be positive")
        if self.target_health_below_fraction is not None and not (
            0.0 < self.target_health_below_fraction <= 1.0
        ):
            raise ValueError("target_health_below_fraction must be in (0, 1]")
        if not self.evidence:
            raise ValueError("evidence must be non-empty")


_COLOR_TAG_RE = re.compile(r"\|c[0-9a-fA-F]{6}|\|r")
_GRAVELORD_SLOT_HEADER_RE = re.compile(
    r"\bwith\s+(?:a\s+)?gravelord\s+ability\s+slotted\b",
    re.IGNORECASE,
)


def _strip_color_tags(text: str) -> str:
    return _COLOR_TAG_RE.sub("", str(text or ""))


def _sentences(text: str) -> tuple[str, ...]:
    normalized = " ".join(str(text or "").split())
    return tuple(part.strip() for part in re.split(r"(?<=[.;])\s+", normalized) if part.strip())


def _raw_placeholder_sentence(raw_description: str, coefficient_number: int) -> str | None:
    placeholder = re.compile(rf"<<\s*{int(coefficient_number)}\s*>>")
    return next(
        (sentence for sentence in _sentences(raw_description) if placeholder.search(sentence)),
        None,
    )


def extract_source_mapped_stat_rule(
    *,
    skill_rank_id: int,
    coefficient_number: int,
    raw_description: str,
    coef_description: str,
    desc_header: str = "",
) -> tuple[SkillComponentSourceStatRule, ...]:
    raw_sentence = _raw_placeholder_sentence(raw_description, coefficient_number)
    if raw_sentence is None:
        return ()

    raw_lower = raw_sentence.casefold()
    # UESP's raw and coefficientized strings do not always preserve identical
    # sentence boundaries. The raw sentence is therefore used only to prove slot
    # ownership; the distinctive literal-valued mechanic is located in the full
    # color-normalized display text.
    display = " ".join(_strip_color_tags(coef_description).split())

    if re.search(
        rf"\beach\s+mace\s+increases\s+your\s+offensive\s+penetration\s+by\s+"
        rf"<<\s*{int(coefficient_number)}\s*>>",
        raw_lower,
        re.IGNORECASE,
    ):
        amount_match = re.search(
            r"\beach\s+mace\s+increases\s+your\s+offensive\s+penetration\s+by\s+(\d+(?:\.\d+)?)",
            display,
            re.IGNORECASE,
        )
        if amount_match is None:
            return ()
        return (
            SkillComponentSourceStatRule(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                stats=(StatId.PHYSICAL_PENETRATION, StatId.SPELL_PENETRATION),
                driver=SkillComponentSourceStatRuleDriver.DUAL_WIELD_MACES_EQUIPPED,
                amount_basis=SkillComponentSourceStatRuleBasis.FLAT_PER_UNIT,
                amount=float(amount_match.group(1)),
                evidence=amount_match.group(0),
            ),
        )

    death_match = re.search(
        rf"\bincreases\s+your\s+critical\s+strike\s+chance\s+against\s+enemies\s+under\s+"
        rf"(?P<threshold>\d+(?:\.\d+)?)\s*%\s+health\s+by\s+"
        rf"<<\s*{int(coefficient_number)}\s*>>",
        raw_lower,
        re.IGNORECASE,
    )
    if death_match is not None:
        amount_match = re.search(
            r"\bincreases\s+your\s+critical\s+strike\s+chance\s+against\s+enemies\s+under\s+"
            r"\d+(?:\.\d+)?\s*%\s+health\s+by\s+(?P<amount>\d+(?:\.\d+)?)\s*%",
            display,
            re.IGNORECASE,
        )
        if amount_match is None:
            return ()
        if _GRAVELORD_SLOT_HEADER_RE.search(str(desc_header or "")) is None:
            return ()
        return (
            SkillComponentSourceStatRule(
                skill_rank_id=int(skill_rank_id),
                coefficient_number=int(coefficient_number),
                stats=(StatId.CRITICAL_CHANCE,),
                driver=SkillComponentSourceStatRuleDriver.GRAVELORD_ABILITY_SLOTTED,
                amount_basis=SkillComponentSourceStatRuleBasis.CONDITIONAL_FRACTION,
                amount=float(amount_match.group("amount")) / 100.0,
                target_health_below_fraction=float(death_match.group("threshold")) / 100.0,
                evidence=f"{desc_header}: {amount_match.group(0)}".strip(": "),
            ),
        )

    return ()
