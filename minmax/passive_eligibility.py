from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


CLASS_SKILL_LINES: dict[str, tuple[str, ...]] = {
    "arcanist": ("Herald of the Tome", "Soldier of Apocrypha", "Curative Runeforms"),
    "dragonknight": ("Ardent Flame", "Draconic Power", "Earthen Heart"),
    "necromancer": ("Grave Lord", "Bone Tyrant", "Living Death"),
    "nightblade": ("Assassination", "Shadow", "Siphoning"),
    "sorcerer": ("Daedric Summoning", "Dark Magic", "Storm Calling"),
    "templar": ("Aedric Spear", "Dawn's Wrath", "Restoring Light"),
    "warden": ("Animal Companions", "Green Balance", "Winter's Embrace"),
}


@dataclass(frozen=True)
class PassiveEligibility:
    """Character-level gate for which passive skill lines may be considered.

    This class deliberately answers eligibility only. It does not parse passive
    descriptions, decide whether an effect is unconditional, or apply stat
    changes. Those responsibilities belong to later Phase 3 resolution layers.
    """

    eso_class: str
    owned_skill_lines: tuple[str, ...] = ()

    @staticmethod
    def _dedupe(values: Iterable[str]) -> tuple[str, ...]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            name = str(value or "").strip()
            key = name.casefold()
            if not name or key in seen:
                continue
            seen.add(key)
            result.append(name)
        return tuple(result)

    @property
    def class_skill_lines(self) -> tuple[str, ...]:
        return CLASS_SKILL_LINES.get(str(self.eso_class or "").strip().casefold(), ())

    @property
    def eligible_skill_lines(self) -> tuple[str, ...]:
        return self._dedupe((*self.class_skill_lines, *self.owned_skill_lines))

    def owns(self, skill_line: str) -> bool:
        requested = str(skill_line or "").strip().casefold()
        return bool(requested) and any(
            line.casefold() == requested for line in self.eligible_skill_lines
        )

    @classmethod
    def from_character_record(cls, character: dict | None) -> "PassiveEligibility":
        character = character if isinstance(character, dict) else {}
        owned = character.get("owned_skill_lines") or ()
        if not isinstance(owned, (list, tuple, set)):
            owned = ()
        return cls(
            eso_class=str(character.get("eso_class", "") or ""),
            owned_skill_lines=cls._dedupe(str(value or "") for value in owned),
        )
