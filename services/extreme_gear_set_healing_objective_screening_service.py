from __future__ import annotations

"""Proof-safe screening for unmapped gear bonuses in healing-sheet objectives.

This service owns no healing arithmetic. It answers one narrow question: can an
unmapped set-bonus description modify the wearer's character-sheet Healing Done or
Critical Healing stat?

A heal event is not a Healing Done mutation. Likewise, text such as ``when your
healing critically strikes`` is trigger language, not a Critical Healing modifier.
Those mechanics remain the responsibility of the proc/runtime gear family rather
than blocking ordinary five-piece sheet-stat screening.

Direct Healing Done / Critical Healing modifiers, named Mending modifiers, and
global equipment-state mutations remain fail-closed. Bonuses that explicitly
exclude the wearer (for example, effects granted only to nearby group members not
wearing the set) are proven irrelevant to self-H1 even if they mention one of the
target healing stats. Hostile Heal Absorption is likewise not the wearer's Healing
Done stat: text that applies Heal Absorption to enemies and negates their incoming
healing belongs to the hostile runtime/debuff family.

Absence of relevant language alone is still not enough: the description must
contain positive evidence of a recognized mechanic family before it can be proven
irrelevant.
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

_HEALING_DONE_STAT = re.compile(r"\bhealing\s+done\b", re.IGNORECASE)
_CRITICAL_HEALING_STAT = re.compile(r"\bcritical\s+healing\b", re.IGNORECASE)
_WEARER_EXCLUDED_GROUP = re.compile(
    r"\bgroup members?\b[^.;]{0,120}\bnot wearing\b",
    re.IGNORECASE,
)
_HOSTILE_HEAL_ABSORPTION = re.compile(
    r"\bheal absorption\b.*\b(?:enemy|enemies|all enemies)\b|"
    r"\b(?:enemy|enemies|all enemies)\b.*\bheal absorption\b|"
    r"\bheal absorption\b.*\bnegat(?:e|es|ing)\b.*\bhealing\b",
    re.IGNORECASE,
)

# Positive evidence that the description belongs to some concrete mechanic family.
# This does not mean that mechanic is fully modeled. It only prevents semantically
# opaque text from being pruned merely because it lacks healing-stat vocabulary.
_RECOGNIZED_MECHANIC_WORD = re.compile(
    r"\b(?:heal|heals|healed|healing|damage|critical|resistance|armor|shield|ward|"
    r"penetration|magicka|stamina|health|recovery|resource|movement|speed|sprint|"
    r"sneak|dodge|roll|block|blocking|ultimate|weapon|spell|attack|enemy|enemies|target|"
    r"status|effect|disease|poison|flame|frost|shock|bleed|physical|magic|"
    r"oblivion|bash|interrupt|taunt|cooldown|cost|duration|stack|stacks|pet|"
    r"companion|snare|immobilize|invisible|stealth|synergy|buff|debuff|group|absorption)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtremeGearSetHealingObjectiveScreeningResult:
    objective_key: str
    proven_irrelevant: bool
    healing_hazards: tuple[str, ...] = ()
    global_equipment_hazards: tuple[str, ...] = ()
    unrelated_mechanic_evidence: tuple[str, ...] = ()
    wearer_excluded: bool = False
    hostile_heal_absorption: bool = False

    @property
    def blockers(self) -> tuple[str, ...]:
        return (*self.healing_hazards, *self.global_equipment_hazards)


class ExtremeGearSetHealingObjectiveScreeningService:
    """Conservatively prove an unmapped bonus irrelevant to one healing sheet stat."""

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
        wearer_excluded = bool(_WEARER_EXCLUDED_GROUP.search(text))
        hostile_heal_absorption = bool(_HOSTILE_HEAL_ABSORPTION.search(text))
        hazards: list[str] = []

        # Explicit target exclusion wins for self-H1: a modifier granted only to
        # other group members cannot alter the wearer's sheet stat. Hostile Heal
        # Absorption also targets enemy incoming healing rather than the wearer's
        # character-sheet Healing Done stat.
        target_irrelevant = wearer_excluded or hostile_heal_absorption
        if not target_irrelevant:
            if key == "healing_done":
                if _HEALING_DONE_STAT.search(text):
                    hazards.append("direct Healing Done modifier reference")
                if "minor mending" in text or "major mending" in text:
                    hazards.append("Mending healing modifier reference")
            elif _CRITICAL_HEALING_STAT.search(text):
                hazards.append("direct Critical Healing modifier reference")

        global_hazards = tuple(
            phrase for phrase in _GLOBAL_EQUIPMENT_HAZARDS if phrase in text
        )
        mechanic_matches = tuple(
            dict.fromkeys(
                match.group(0).casefold()
                for match in _RECOGNIZED_MECHANIC_WORD.finditer(text)
            )
        )
        final_hazards = tuple(dict.fromkeys(hazards))
        proven_irrelevant = bool(
            (target_irrelevant or mechanic_matches)
            and not final_hazards
            and not global_hazards
        )
        return ExtremeGearSetHealingObjectiveScreeningResult(
            objective_key=key,
            proven_irrelevant=proven_irrelevant,
            healing_hazards=final_hazards,
            global_equipment_hazards=global_hazards,
            unrelated_mechanic_evidence=mechanic_matches,
            wearer_excluded=wearer_excluded,
            hostile_heal_absorption=hostile_heal_absorption,
        )


__all__ = [
    "ExtremeGearSetHealingObjectiveScreeningResult",
    "ExtremeGearSetHealingObjectiveScreeningService",
]
