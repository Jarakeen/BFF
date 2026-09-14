from __future__ import annotations

"""Classify non-static passive mechanics shared by Extreme Recovery objectives."""

from dataclasses import dataclass
from enum import Enum
import re

from minmax.eso_markup import normalize_eso_markup
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord

_SUPPORTED = {"health_recovery", "magicka_recovery", "stamina_recovery"}
_RESOURCE_BY_OBJECTIVE = {
    "health_recovery": "health",
    "magicka_recovery": "magicka",
    "stamina_recovery": "stamina",
}
_LABEL = {
    "health_recovery": "health recovery",
    "magicka_recovery": "magicka recovery",
    "stamina_recovery": "stamina recovery",
}
_RESOURCE_LIST_RECOVERY = re.compile(
    r"(?P<resources>(?:health|magicka|stamina)(?:(?:\s*,\s*|\s+and\s+|\s*,\s*and\s+)(?:health|magicka|stamina)){1,2})\s+recovery",
    flags=re.IGNORECASE,
)


class ExtremeRecoveryPassiveBranchKind(str, Enum):
    STATIC_PERCENT = "static_percent"
    CONDITIONAL_FLAT = "conditional_flat"
    CONDITIONAL_PERCENT = "conditional_percent"
    SCALING_RECOVERY = "scaling_recovery"
    NEGATIVE_ONLY = "negative_only"


@dataclass(frozen=True)
class ExtremeRecoveryPassiveBranch:
    passive: ExtremePlayerSkillRecord
    objective_key: str
    kind: ExtremeRecoveryPassiveBranchKind
    can_raise_self: bool
    flat_ceiling: float | None = None
    percent_ceiling: float | None = None
    condition: str | None = None


class ExtremeRecoveryPassiveSpecialBranchService:
    @staticmethod
    def _text(value: str) -> str:
        return " ".join(normalize_eso_markup(str(value or "")).text.casefold().split())

    @classmethod
    def mentions_objective_recovery(cls, value: str, objective_key: str) -> bool:
        objective = str(objective_key or "").strip().casefold()
        if objective not in _SUPPORTED:
            raise KeyError(f"unsupported Recovery objective: {objective_key!r}")
        text = cls._text(value)
        label = _LABEL[objective]
        if label in text:
            return True
        resource = _RESOURCE_BY_OBJECTIVE[objective]
        for match in _RESOURCE_LIST_RECOVERY.finditer(text):
            resources = {
                token
                for token in re.findall(r"health|magicka|stamina", match.group("resources"), flags=re.IGNORECASE)
            }
            if resource in {item.casefold() for item in resources}:
                return True
        return False

    @classmethod
    def classify(
        cls,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
    ) -> ExtremeRecoveryPassiveBranch | None:
        objective = str(objective_key or "").strip().casefold()
        if objective not in _SUPPORTED:
            raise KeyError(f"unsupported Recovery objective: {objective_key!r}")

        text = cls._text(passive.description)
        label = _LABEL[objective]
        if not cls.mentions_objective_recovery(text, objective):
            return None

        if objective == "health_recovery" and re.search(r"health recovery\s*:\s*-[0-9%/\-]+", text):
            values = [float(value) for value in re.findall(r"-(\d+(?:\.\d+)?)%", text)]
            return ExtremeRecoveryPassiveBranch(
                passive=passive,
                objective_key=objective,
                kind=ExtremeRecoveryPassiveBranchKind.NEGATIVE_ONLY,
                can_raise_self=False,
                percent_ceiling=max(values) if values else None,
                condition="vampire_stage",
            )

        if "home keeps" in text and "recovery" in text:
            percents = [float(value) for value in re.findall(r"(\d+(?:\.\d+)?)%", text)]
            if percents:
                return ExtremeRecoveryPassiveBranch(
                    passive=passive,
                    objective_key=objective,
                    kind=ExtremeRecoveryPassiveBranchKind.CONDITIONAL_PERCENT,
                    can_raise_self=True,
                    percent_ceiling=max(percents),
                    condition="home_keeps",
                )

        # Canonical Recovery passives use several resource-list orderings, including
        # "Health, Stamina, and Magicka Recovery" and "Magicka and Stamina Recovery".
        # Unconditional percentage clauses are static semantics even when the generic
        # projector has not yet normalized that exact wording.
        static_percent = re.search(
            r"increases your .*recovery by\s+(\d+(?:\.\d+)?)%",
            text,
        )
        if static_percent and not any(
            marker in text
            for marker in (
                "while ",
                "when ",
                "whenever ",
                "after ",
                "for each ",
                "for every ",
                "per slotted",
                "home keeps",
            )
        ):
            return ExtremeRecoveryPassiveBranch(
                passive=passive,
                objective_key=objective,
                kind=ExtremeRecoveryPassiveBranchKind.STATIC_PERCENT,
                can_raise_self=True,
                percent_ceiling=float(static_percent.group(1)),
                condition=None,
            )

        target_up_to = re.search(
            rf"{re.escape(label)} by up to\s+(\d+(?:\.\d+)?)",
            text,
        )
        if target_up_to:
            return ExtremeRecoveryPassiveBranch(
                passive=passive,
                objective_key=objective,
                kind=ExtremeRecoveryPassiveBranchKind.CONDITIONAL_FLAT,
                can_raise_self=True,
                flat_ceiling=float(target_up_to.group(1)),
                condition="runtime_condition_required",
            )

        # Conditional shared-Recovery passives may put the amount after the noun
        # phrase rather than before it, e.g. Undead Confederate: "your Health,
        # Magicka, and Stamina Recovery is increased by 155".  Capture the proven
        # ceiling while preserving the runtime condition instead of flattening it
        # into an always-on static contribution.
        conditional_increased_by = re.search(
            r"recovery\s+(?:is|are)\s+increased by\s+(\d+(?:\.\d+)?)",
            text,
        )
        if conditional_increased_by:
            return ExtremeRecoveryPassiveBranch(
                passive=passive,
                objective_key=objective,
                kind=ExtremeRecoveryPassiveBranchKind.CONDITIONAL_FLAT,
                can_raise_self=True,
                flat_ceiling=float(conditional_increased_by.group(1)),
                condition="runtime_condition_required",
            )

        shared_fixed = re.search(
            r"(?:and\s+)?(\d+(?:\.\d+)?)\s+(?:health|magicka|stamina)(?:\s*,\s*|\s+and\s+|\s*,\s*and\s+)(?:health|magicka|stamina)(?:(?:\s*,\s*|\s+and\s+|\s*,\s*and\s+)(?:health|magicka|stamina))?\s+recovery",
            text,
        )
        if shared_fixed:
            return ExtremeRecoveryPassiveBranch(
                passive=passive,
                objective_key=objective,
                kind=ExtremeRecoveryPassiveBranchKind.CONDITIONAL_FLAT,
                can_raise_self=True,
                flat_ceiling=float(shared_fixed.group(1)),
                condition="runtime_condition_required",
            )

        # Known Recovery semantics whose maximum depends on another canonical owner
        # (slot count, Ultimate spend, Max Resource, etc.). Semantic identity is
        # proven here, but no numeric ceiling is invented.
        scaling_markers = (
            "per slotted",
            "for each",
            "for every",
            "ultimate spent",
            "based on your max",
            "based on your maximum",
            "equal to",
        )
        if any(marker in text for marker in scaling_markers):
            return ExtremeRecoveryPassiveBranch(
                passive=passive,
                objective_key=objective,
                kind=ExtremeRecoveryPassiveBranchKind.SCALING_RECOVERY,
                can_raise_self=True,
                condition="external_ceiling_required",
            )

        return None


__all__ = [
    "ExtremeRecoveryPassiveBranch",
    "ExtremeRecoveryPassiveBranchKind",
    "ExtremeRecoveryPassiveSpecialBranchService",
]
