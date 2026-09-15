from __future__ import annotations

"""Proof-safe screening for unmapped gear bonuses in healing-sheet objectives.

This service owns no healing arithmetic. It only proves that an unmapped set bonus
cannot modify the requested character-sheet healing stat. Direct healing/heal
language remains a blocker for ``healing_done`` because ESO descriptions use many
forms for healing modifiers and proc heals. For ``critical_healing`` the screen is
narrower: both critical and healing language must be present before the unmapped
bonus can plausibly modify Critical Healing.

Absence of healing vocabulary is not enough to prove irrelevance. The description
must also contain positive evidence of a recognized unrelated mechanic family.
Opaque or semantically unclassified text remains unresolved and therefore fails
closed.

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

# A healing-sheet screen may prune only when the raw description positively
# identifies some non-healing mechanic family. These markers do not claim that
# the mechanic itself is understood; they only establish that the description is
# not semantically opaque. Relevant healing/proc hazards still fail closed below.
_UNRELATED_MECHANIC_WORD = re.compile(
    r"\b(?:damage|resistance|armor|shield|ward|penetration|magicka|stamina|health|"
    r"recovery|resource|movement|speed|sprint|sneak|dodge|roll|block|blocking|"
    r"ultimate|weapon|spell|attack|enemy|target|status|effect|disease|poison|"
    r"flame|frost|shock|bleed|physical|magic|oblivion|bash|interrupt|taunt|"
    r"cooldown|cost|duration|stack|stacks|pet|companion|crowd control|snare|"
    r"immobilize|invisible|stealth)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtremeGearSetHealingObjectiveScreeningResult:
    objective_key: str
    proven_irrelevant: bool
    healing_hazards: tuple[str, ...] = ()
    global_equipment_hazards: tuple[str, ...] = ()
    unrelated_mechanic_evidence: tuple[str, ...] = ()

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
                hazards.append(
                    "unmapped healing language may modify Healing Done or represent a heal proc"
                )
            if "minor mending" in text or "major mending" in text:
                hazards.append("Mending healing modifier reference")
        elif has_heal and has_critical:
            hazards.append("unmapped critical-healing language")

        global_hazards = tuple(
            phrase for phrase in _GLOBAL_EQUIPMENT_HAZARDS if phrase in text
        )
        unrelated_matches = tuple(
            dict.fromkeys(match.group(0).casefold() for match in _UNRELATED_MECHANIC_WORD.finditer(text))
        )
        final_hazards = tuple(dict.fromkeys(hazards))
        proven_irrelevant = bool(
            unrelated_matches and not final_hazards and not global_hazards
        )
        return ExtremeGearSetHealingObjectiveScreeningResult(
            objective_key=key,
            proven_irrelevant=proven_irrelevant,
            healing_hazards=final_hazards,
            global_equipment_hazards=global_hazards,
            unrelated_mechanic_evidence=unrelated_matches,
        )


__all__ = [
    "ExtremeGearSetHealingObjectiveScreeningResult",
    "ExtremeGearSetHealingObjectiveScreeningService",
]
