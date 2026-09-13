from __future__ import annotations

"""Classify non-static Health Recovery passive mechanics for Extreme proof work.

The generic passive projector deliberately refuses to flatten runtime-dependent
passives into static contributions. This service owns only the small semantic gap
for Health Recovery so those passives can be carried into later runtime/route
proofs without being treated as unknown mechanics.
"""

from dataclasses import dataclass
from enum import Enum
import re

from minmax.eso_markup import normalize_eso_markup
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord


class ExtremeHealthRecoveryPassiveBranchKind(str, Enum):
    CONDITIONAL_FLAT = "conditional_flat"
    CONDITIONAL_PERCENT = "conditional_percent"
    NEGATIVE_ONLY = "negative_only"


@dataclass(frozen=True)
class ExtremeHealthRecoveryPassiveBranch:
    passive: ExtremePlayerSkillRecord
    kind: ExtremeHealthRecoveryPassiveBranchKind
    can_raise_self: bool
    flat_ceiling: float | None = None
    percent_ceiling: float | None = None
    condition: str | None = None


class ExtremeHealthRecoveryPassiveSpecialBranchService:
    """Description-driven classifier with fail-closed fallback."""

    @staticmethod
    def _text(description: str) -> str:
        return " ".join(
            normalize_eso_markup(str(description or "")).text.casefold().split()
        )

    @classmethod
    def classify(
        cls,
        passive: ExtremePlayerSkillRecord,
    ) -> ExtremeHealthRecoveryPassiveBranch | None:
        text = cls._text(passive.description)
        if "health recovery" not in text and not (
            "health" in text and "magicka" in text and "stamina recovery" in text
        ):
            return None

        # Vampire-stage recovery penalties are strictly non-positive for a
        # maximize objective. Keeping them explicit proves they cannot win.
        if re.search(r"health recovery\s*:\s*-[0-9%/\-]+", text):
            values = [float(value) for value in re.findall(r"-(\d+(?:\.\d+)?)%", text)]
            ceiling = max(values) if values else None
            return ExtremeHealthRecoveryPassiveBranch(
                passive=passive,
                kind=ExtremeHealthRecoveryPassiveBranchKind.NEGATIVE_ONLY,
                can_raise_self=False,
                percent_ceiling=ceiling,
                condition="vampire_stage",
            )

        # Emperor Domination uses an explicit Home Keep table ending at 100%.
        if "home keeps" in text and "recovery" in text:
            percents = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)%", text)]
            if percents:
                return ExtremeHealthRecoveryPassiveBranch(
                    passive=passive,
                    kind=ExtremeHealthRecoveryPassiveBranchKind.CONDITIONAL_PERCENT,
                    can_raise_self=True,
                    percent_ceiling=max(percents),
                    condition="home_keeps",
                )

        # Conditional flat ceilings that are stated directly in the tooltip.
        up_to = re.search(
            r"health recovery by up to\s+(\d+(?:\.\d+)?)",
            text,
        )
        if up_to:
            return ExtremeHealthRecoveryPassiveBranch(
                passive=passive,
                kind=ExtremeHealthRecoveryPassiveBranchKind.CONDITIONAL_FLAT,
                can_raise_self=True,
                flat_ceiling=float(up_to.group(1)),
                condition="runtime_condition_required",
            )

        # Shared fixed recovery reward, e.g. Sphere of Influence.
        shared = re.search(
            r"(?:and\s+)?(\d+(?:\.\d+)?)\s+health,?\s+magicka,?\s+(?:and\s+)?stamina recovery",
            text,
        )
        if shared:
            return ExtremeHealthRecoveryPassiveBranch(
                passive=passive,
                kind=ExtremeHealthRecoveryPassiveBranchKind.CONDITIONAL_FLAT,
                can_raise_self=True,
                flat_ceiling=float(shared.group(1)),
                condition="runtime_condition_required",
            )

        return None


__all__ = [
    "ExtremeHealthRecoveryPassiveBranch",
    "ExtremeHealthRecoveryPassiveBranchKind",
    "ExtremeHealthRecoveryPassiveSpecialBranchService",
]
