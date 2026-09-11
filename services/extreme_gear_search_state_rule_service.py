from __future__ import annotations

"""Review gear mechanics that mutate the legal Extreme search space.

These are not ordinary stat effects.  They change which build states may exist or
which other search axes are legal.  Keep them explicit so the named-gear relevance
denominator can classify them without pretending the global search already knows
how to execute the mutated state.
"""

from dataclasses import dataclass
from enum import Enum

from minmax.eso_markup import normalize_eso_markup
from minmax.gear_sets import GearSetBonus


class ExtremeGearSearchStateRule(str, Enum):
    ONE_BAR_ONLY = "one_bar_only"
    SUPPRESSES_OTHER_SET_BONUSES = "suppresses_other_set_bonuses"
    ALLOWS_TWO_MUNDUS = "allows_two_mundus"


@dataclass(frozen=True)
class ExtremeGearSearchStateRuleEvidence:
    set_name: str
    rule: ExtremeGearSearchStateRule
    retains_max_resource_candidate: bool
    evidence_text: str


class ExtremeGearSearchStateRuleService:
    """Recognize reviewed named-set search-space mutations and nothing else."""

    @staticmethod
    def _text(bonuses: tuple[GearSetBonus, ...]) -> str:
        values: list[str] = []
        for bonus in bonuses:
            raw = normalize_eso_markup(str(bonus.description or "")).text
            text = " ".join(raw.split())
            if text:
                values.append(text)
        return " ".join(values)

    @classmethod
    def review(
        cls,
        set_name: str,
        bonuses: tuple[GearSetBonus, ...],
    ) -> ExtremeGearSearchStateRuleEvidence | None:
        name = str(set_name or "").strip()
        text = cls._text(bonuses)
        folded = text.casefold()

        if (
            name == "Oakensoul Ring"
            and "unable to swap between your primary and backup weapon sets" in folded
        ):
            return ExtremeGearSearchStateRuleEvidence(
                set_name=name,
                rule=ExtremeGearSearchStateRule.ONE_BAR_ONLY,
                retains_max_resource_candidate=False,
                evidence_text=text,
            )

        if (
            name == "Torc of the Last Ayleid King"
            and "disable all other item set bonuses" in folded
        ):
            return ExtremeGearSearchStateRuleEvidence(
                set_name=name,
                rule=ExtremeGearSearchStateRule.SUPPRESSES_OTHER_SET_BONUSES,
                retains_max_resource_candidate=False,
                evidence_text=text,
            )

        if (
            name == "Twice-Born Star"
            and "two mundus stone boons at the same time" in folded
        ):
            return ExtremeGearSearchStateRuleEvidence(
                set_name=name,
                rule=ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS,
                retains_max_resource_candidate=True,
                evidence_text=text,
            )

        return None


__all__ = [
    "ExtremeGearSearchStateRule",
    "ExtremeGearSearchStateRuleEvidence",
    "ExtremeGearSearchStateRuleService",
]
