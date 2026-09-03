from __future__ import annotations

"""Small exact difficulty vocabulary for Phase 10 encounter evaluation."""

from enum import Enum


class EncounterDifficulty(str, Enum):
    NORMAL = "normal"
    VETERAN = "veteran"
    HARDMODE = "hardmode"


_ALIASES = {
    "normal": EncounterDifficulty.NORMAL,
    "veteran": EncounterDifficulty.VETERAN,
    "vet": EncounterDifficulty.VETERAN,
    "hardmode": EncounterDifficulty.HARDMODE,
    "hard mode": EncounterDifficulty.HARDMODE,
    "hard_mode": EncounterDifficulty.HARDMODE,
    "hm": EncounterDifficulty.HARDMODE,
}


def normalize_encounter_difficulty(
    value: EncounterDifficulty | str,
) -> EncounterDifficulty:
    if isinstance(value, EncounterDifficulty):
        return value
    key = " ".join(str(value or "").strip().casefold().replace("_", " ").split())
    try:
        return _ALIASES[key]
    except KeyError as exc:
        raise ValueError(f"Unsupported encounter difficulty: {value!r}") from exc
