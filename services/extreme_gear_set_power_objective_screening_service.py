from __future__ import annotations

"""Proof-safe screening for unmapped gear bonuses in sheet-power objectives.

This service owns no Weapon or Spell Damage arithmetic. It only proves that an
unmapped set bonus cannot change the requested character-sheet power stat.
Damage or healing that merely scales *from* Weapon/Spell Damage is therefore
irrelevant, while direct self-stat changes, relevant named buffs, weapon-trait
changes, and global equipment-state mutations remain explicit blockers.
"""

from dataclasses import dataclass
import re

from minmax.eso_markup import normalize_eso_markup


_POWER_BUFFS_BY_OBJECTIVE = {
    "weapon_damage": ("minor brutality", "major brutality", "minor courage", "major courage"),
    "spell_damage": ("minor sorcery", "major sorcery", "minor courage", "major courage"),
}

_GLOBAL_EQUIPMENT_HAZARDS = (
    "disable all other item set bonuses",
    "unable to swap between your primary and backup weapon sets",
    "two mundus stone boons",
    "effectiveness of your weapon traits",
)

_TARGET_POWER = r"(?:weapon(?:\s+and\s+spell)?|spell(?:\s+and\s+weapon)?)\s+damage"
_SELF_CHANGE = re.compile(
    rf"\b(?:increase(?:s|d|ing)?|gain(?:s|ed|ing)?|grant(?:s|ed|ing)?|adds?)\b"
    rf"[^.;]{{0,100}}?\b{_TARGET_POWER}\b"
    rf"|\b(?:your\s+)?{_TARGET_POWER}\b[^.;]{{0,40}}?\b"
    rf"(?:increase(?:s|d|ing)?|gain(?:s|ed|ing)?|grant(?:s|ed|ing)?|adds?)\b",
    re.IGNORECASE,
)
_SCALING_CLAUSE = re.compile(
    r"(?:the\s+)?(?:damage|healing|effect)\s+scales?\s+off(?:\s+of)?\s+"
    r"(?:the\s+higher\s+of\s+)?(?:your\s+)?weapon\s+or\s+spell\s+damage"
    r"(?:\s+increases?\s+by\s+\d+(?:\.\d+)?%\s+per\s+stack)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtremeGearSetPowerObjectiveScreeningResult:
    objective_key: str
    proven_irrelevant: bool
    power_hazards: tuple[str, ...] = ()
    global_equipment_hazards: tuple[str, ...] = ()

    @property
    def blockers(self) -> tuple[str, ...]:
        return (*self.power_hazards, *self.global_equipment_hazards)


class ExtremeGearSetPowerObjectiveScreeningService:
    """Conservatively prove an unmapped bonus irrelevant to one sheet-power stat."""

    @staticmethod
    def _normalized(description: str) -> str:
        text = normalize_eso_markup(str(description or "")).text
        return " ".join(text.casefold().split())

    @classmethod
    def review(
        cls,
        description: str,
        objective_key: str,
    ) -> ExtremeGearSetPowerObjectiveScreeningResult:
        key = str(objective_key or "").strip().casefold()
        relevant_buffs = _POWER_BUFFS_BY_OBJECTIVE.get(key)
        if relevant_buffs is None:
            raise KeyError(f"unreviewed Extreme power screening objective: {objective_key!r}")

        text = cls._normalized(description)
        hazards: list[str] = []

        # A scaling source consumes sheet power; it does not mutate sheet power.
        # The direct-change grammar intentionally looks for the player's stat,
        # while enemy/attacker reductions are not matched as self-stat gains.
        direct_text = _SCALING_CLAUSE.sub("", text)
        if _SELF_CHANGE.search(direct_text):
            hazards.append("direct self Weapon/Spell Damage mutation")

        for phrase in relevant_buffs:
            if phrase in text:
                hazards.append(f"{phrase.title()} power modifier")

        global_hazards = tuple(
            phrase for phrase in _GLOBAL_EQUIPMENT_HAZARDS if phrase in text
        )
        final_hazards = tuple(dict.fromkeys(hazards))
        return ExtremeGearSetPowerObjectiveScreeningResult(
            objective_key=key,
            proven_irrelevant=not final_hazards and not global_hazards,
            power_hazards=final_hazards,
            global_equipment_hazards=global_hazards,
        )


__all__ = [
    "ExtremeGearSetPowerObjectiveScreeningResult",
    "ExtremeGearSetPowerObjectiveScreeningService",
]
