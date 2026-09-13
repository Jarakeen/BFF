from __future__ import annotations

"""Proof-safe screening for unmapped gear bonuses in recovery objectives.

This service does not project recovery math. It only proves that an unmapped set
bonus cannot change the requested recovery stat and therefore may be ignored by
Extreme named-gear relevance. Any direct recovery mutation, recovery named buff,
or global equipment-state mutation remains a blocker for later mechanic review.
"""

from dataclasses import dataclass
import re

from minmax.eso_markup import normalize_eso_markup


_RECOVERY_RESOURCE_BY_OBJECTIVE = {
    "health_recovery": "health",
    "magicka_recovery": "magicka",
    "stamina_recovery": "stamina",
}

_GLOBAL_EQUIPMENT_HAZARDS = (
    "disable all other item set bonuses",
    "unable to swap between your primary and backup weapon sets",
    "two mundus stone boons",
)


@dataclass(frozen=True)
class ExtremeGearSetRecoveryObjectiveScreeningResult:
    objective_key: str
    proven_irrelevant: bool
    recovery_hazards: tuple[str, ...] = ()
    global_equipment_hazards: tuple[str, ...] = ()

    @property
    def blockers(self) -> tuple[str, ...]:
        return (*self.recovery_hazards, *self.global_equipment_hazards)


class ExtremeGearSetRecoveryObjectiveScreeningService:
    """Conservatively prove an unmapped bonus irrelevant to one recovery stat."""

    @staticmethod
    def _normalized(description: str) -> str:
        text = normalize_eso_markup(str(description or "")).text
        return " ".join(text.casefold().split())

    @classmethod
    def review(
        cls,
        description: str,
        objective_key: str,
    ) -> ExtremeGearSetRecoveryObjectiveScreeningResult:
        key = str(objective_key or "").strip().casefold()
        resource = _RECOVERY_RESOURCE_BY_OBJECTIVE.get(key)
        if resource is None:
            raise KeyError(f"unreviewed Extreme recovery screening objective: {objective_key!r}")

        text = cls._normalized(description)
        hazards: list[str] = []

        # Direct target-stat references are always relevant, whether the effect
        # increases, decreases, scales, stacks, or is conditional.
        if re.search(rf"\b{re.escape(resource)}\s+recovery\b", text):
            hazards.append(f"{resource.title()} Recovery reference")

        # ESO also compresses a shared stat list into one trailing noun, for
        # example "Health, Magicka, and Stamina Recovery".  Accept ordinary,
        # Oxford-comma, and/or list grammar, then retain the row if the requested
        # resource is one of the members governed by the trailing "Recovery".
        shared_recovery = re.search(
            r"\b(?P<body>(?:health|magicka|stamina)"
            r"(?:(?:\s*,\s*|\s*,?\s+(?:and|or)\s+)(?:health|magicka|stamina)){1,2})"
            r"\s+recovery\b",
            text,
        )
        if (
            shared_recovery is not None
            and re.search(rf"\b{re.escape(resource)}\b", shared_recovery.group("body"))
        ):
            hazards.append(f"shared {resource.title()} Recovery list reference")

        # Fortitude/Intellect/Endurance are named recovery modifiers. Retain only
        # the buff family relevant to the requested resource.
        relevant_buffs = {
            "health": ("minor fortitude", "major fortitude"),
            "magicka": ("minor intellect", "major intellect"),
            "stamina": ("minor endurance", "major endurance"),
        }[resource]
        for phrase in relevant_buffs:
            if phrase in text:
                hazards.append(f"{phrase.title()} recovery modifier")

        global_hazards = tuple(
            phrase for phrase in _GLOBAL_EQUIPMENT_HAZARDS if phrase in text
        )
        final_hazards = tuple(dict.fromkeys(hazards))
        return ExtremeGearSetRecoveryObjectiveScreeningResult(
            objective_key=key,
            proven_irrelevant=not final_hazards and not global_hazards,
            recovery_hazards=final_hazards,
            global_equipment_hazards=global_hazards,
        )


__all__ = [
    "ExtremeGearSetRecoveryObjectiveScreeningResult",
    "ExtremeGearSetRecoveryObjectiveScreeningService",
]
