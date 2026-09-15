from __future__ import annotations

"""Proof-safe screening for unmapped gear bonuses in healing-sheet objectives.

This service owns no healing arithmetic. It only proves that an unmapped set bonus
cannot modify the requested character-sheet healing stat. Direct healing/heal
language remains a blocker for ``healing_done`` because ESO descriptions use many
forms for healing modifiers and proc heals. For ``critical_healing`` the screen is
narrower: both critical and healing language must be present before the unmapped
bonus can plausibly modify Critical Healing.

This does not classify proc heals as irrelevant to Extreme MOST Actual Heal. It
only classifies whether an unmapped description can modify the sheet objective
used for ordinary-set candidate discovery. Proc-heal candidacy remains owned by
runtime/proc mechanic coverage.
"""

from dataclasses import dataclass
import re

from minmax.eso_markup import normalize_eso_markup


_GLOBAL_EQUIPMENT_HAZARDS = (
    "disable all other item set bonuses",
    "unable to swap between your primary and backup weapon sets",
    "two mundus stone boons",
    "effectiveness of your weapon traits",
)

_HEAL_WORD = re.compile(r"\bheal(?:s|ed|ing)?\b|\bhealing\b", re.IGNORECASE)
_CRITICAL_WORD = re.compile(r"\bcritical(?:ly)?\b", re.IGNORECASE)


@dataclass(frozen=True)
class ExtremeGearSetHealingObjectiveScreeningResult:
    objective_key: str
    proven_irrelevant: bool
    healing_hazards: tuple[str, ...] = ()
    global_equipment_hazards: tuple[str, ...] = ()

    @property
    def blockers(self) -> tuple[str, ...]:
        return (*self.healing_hazards, *self.global_equipment_hazards)


class ExtremeGearSetHealingObjectiveScreeningService:
    """Conservatively prove an unmapped bonus irrelevant to one healing stat."""

    @staticmethod
    def _normalized(description: str) -> str:
        text = normalize_eso_markup(str(description or "")).text
        return " ".join(text.casefold().split())

    @classmethod
    def review(
        cls,
        description: str,
        objective_key: str,
    ) -> ExtremeGearSetHealingObjectiveScreeningResult:
        key = str(objective_key or "").strip().casefold()
        if key not in {"healing_done", "critical_healing"}:
            raise KeyError(
                f"unreviewed Extreme healing screening objective: {objective_key!r}"
            )

        text = cls._normalized(description)
        hazards: list[str] = []
        has_heal = bool(_HEAL_WORD.search(text))
        has_critical = bool(_CRITICAL_WORD.search(text))

        if key == "healing_done":
            if has_heal:
                hazards.append("unmapped healing language may modify Healing Done or represent a heal proc")
            if "minor mending" in text or "major mending" in text:
                hazards.append("Mending healing modifier reference")
        elif has_heal and has_critical:
            hazards.append("unmapped critical-healing language")

        global_hazards = tuple(
            phrase for phrase in _GLOBAL_EQUIPMENT_HAZARDS if phrase in text
        )
        final_hazards = tuple(dict.fromkeys(hazards))
        return ExtremeGearSetHealingObjectiveScreeningResult(
            objective_key=key,
            proven_irrelevant=not final_hazards and not global_hazards,
            healing_hazards=final_hazards,
            global_equipment_hazards=global_hazards,
        )


__all__ = [
    "ExtremeGearSetHealingObjectiveScreeningResult",
    "ExtremeGearSetHealingObjectiveScreeningService",
]
