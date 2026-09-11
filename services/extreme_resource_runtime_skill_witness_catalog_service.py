from __future__ import annotations

"""Canonical skill witnesses for Extreme max-resource runtime conditions.

This service owns identity/evidence only. It inventories the canonical player-skill
universe for the three runtime condition families that require an actual skill or
transformation witness before a conditional gear bonus may be activated:

* ``armor_ability_slotted`` -> a bar-eligible active from an Armor skill line;
* ``pet_active`` -> an active whose canonical identity/description proves a combat pet;
* ``transformed`` -> a canonical transformation Ultimate/form witness.

It performs no stat arithmetic and does not choose a winning candidate. Candidate
legality/materialization remains a separate layer so the global denominator cannot
silently grant a skill the selected build cannot actually slot.
"""

from dataclasses import dataclass
from pathlib import Path
import re

from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)


@dataclass(frozen=True)
class ExtremeResourceRuntimeSkillWitness:
    condition: str
    skill_id: int
    base_ability_id: int | None
    ability_id: int
    name: str
    skill_line: str
    skill_type: str
    description: str

    @property
    def identity(self) -> tuple[object, ...]:
        return (
            self.condition,
            self.skill_id,
            self.base_ability_id,
            self.ability_id,
            self.name,
            self.skill_line,
        )


@dataclass(frozen=True)
class ExtremeResourceRuntimeSkillWitnessCatalog:
    armor_abilities: tuple[ExtremeResourceRuntimeSkillWitness, ...]
    pet_abilities: tuple[ExtremeResourceRuntimeSkillWitness, ...]
    transformation_ultimates: tuple[ExtremeResourceRuntimeSkillWitness, ...]
    active_skills_reviewed: int
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()


class ExtremeResourceRuntimeSkillWitnessCatalogService:
    """Inventory canonical skill witnesses for remaining gear runtime conditions."""

    ARMOR_ABILITY = "armor_ability_slotted"
    PET_ACTIVE = "pet_active"
    TRANSFORMED = "transformed"

    # Reviewed semantic identities from the canonical 216-active denominator.
    # These are names, not volatile numeric ability ids.  Each creates a combat pet
    # that can satisfy ESO's "while you have a pet active" condition at a snapshot.
    _REVIEWED_PET_SKILL_NAMES = frozenset(
        {
            "feral guardian",
            "summon storm atronach",
            "summon unstable familiar",
            "summon winged twilight",
            "summon shade",
        }
    )
    _PET_CREATURE = r"(?:familiar|clannfear|twilight|(?:storm\s+)?atronach|grizzly|bear|guardian|shade)"
    _PET_DIRECT_SUMMON_RE = re.compile(
        rf"\bsummon\s+(?:(?:a|an|your)\s+)?(?:\w+\s+){{0,3}}{_PET_CREATURE}\b",
        re.IGNORECASE,
    )
    _PET_COMPANION_RE = re.compile(
        rf"\b{_PET_CREATURE}\b",
        re.IGNORECASE,
    )
    _PET_PERSISTENCE_MARKERS = (
        "fight at your side",
        "fight by your side",
        "remains until killed or unsummoned",
        "remain until killed or unsummoned",
        "once summoned",
    )
    _TRANSFORMATION_LINES = frozenset({"werewolf", "bone tyrant", "vampire"})

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        skill_universe_service: ExtremeSkillUniverseService | None = None,
    ) -> None:
        if database_path is None and skill_universe_service is None:
            raise ValueError("database_path or skill_universe_service is required")
        self.skill_universe_service = skill_universe_service or ExtremeSkillUniverseService(
            database_path  # type: ignore[arg-type]
        )

    @staticmethod
    def _is_ultimate(row: ExtremePlayerSkillRecord) -> bool:
        return "ultimate" in str(row.skill_type or "").casefold()

    @staticmethod
    def _player_active(row: ExtremePlayerSkillRecord) -> bool:
        return bool(row.is_player and not row.is_passive and str(row.name or "").strip())

    @classmethod
    def _concrete(cls, row: ExtremePlayerSkillRecord) -> bool:
        return bool(cls._player_active(row) and row.max_rank_ability_id is not None)

    @classmethod
    def _is_pet_witness(cls, row: ExtremePlayerSkillRecord) -> bool:
        if not cls._concrete(row):
            return False
        name = " ".join(str(row.name or "").casefold().split())
        if name in cls._REVIEWED_PET_SKILL_NAMES:
            return True

        text = " ".join(str(row.description or "").casefold().split())
        if not text or cls._PET_COMPANION_RE.search(text) is None:
            return False
        # Fallback for future canonical rows whose identity has not yet joined the
        # reviewed name set. Environmental constructs such as Grave Grasp's
        # patches/claws contain no reviewed creature marker and remain excluded.
        if cls._PET_DIRECT_SUMMON_RE.search(text) is not None:
            return True
        return any(marker in text for marker in cls._PET_PERSISTENCE_MARKERS)

    @classmethod
    def _is_transformation_witness(cls, row: ExtremePlayerSkillRecord) -> bool:
        if not cls._player_active(row):
            return False
        name = " ".join(str(row.name or "").casefold().split())
        text = " ".join(str(row.description or "").casefold().split())
        line = " ".join(str(row.skill_line or "").casefold().split())
        has_transform_evidence = bool(
            "transformation" in name
            or "transform into" in text
            or "transform yourself" in text
            or (line == "werewolf" and "transform" in text)
        )
        if not has_transform_evidence:
            return False
        # Normal rows must identify themselves as Ultimates. Some canonical
        # transformation rows are sparse in skill_rank/skill_type; for the known
        # transformation skill lines, explicit transformation identity is enough
        # to preserve the witness while downstream bar legality still owns slot 5.
        return cls._is_ultimate(row) or line in cls._TRANSFORMATION_LINES

    @staticmethod
    def _witness(condition: str, row: ExtremePlayerSkillRecord) -> ExtremeResourceRuntimeSkillWitness:
        observational_id = row.max_rank_ability_id or row.base_ability_id or row.skill_id
        if observational_id is None:
            raise ValueError(f"runtime skill witness lacks any ability identity: {row.name}")
        return ExtremeResourceRuntimeSkillWitness(
            condition=condition,
            skill_id=int(row.skill_id),
            base_ability_id=(int(row.base_ability_id) if row.base_ability_id is not None else None),
            ability_id=int(observational_id),
            name=row.name,
            skill_line=row.skill_line,
            skill_type=row.skill_type,
            description=row.description,
        )

    @staticmethod
    def _ordered(rows: list[ExtremeResourceRuntimeSkillWitness]) -> tuple[ExtremeResourceRuntimeSkillWitness, ...]:
        unique = {row.identity: row for row in rows}
        return tuple(
            sorted(
                unique.values(),
                key=lambda row: (row.skill_line.casefold(), row.name.casefold(), row.ability_id),
            )
        )

    def build(self) -> ExtremeResourceRuntimeSkillWitnessCatalog:
        actives = tuple(self.skill_universe_service.actives())
        armor: list[ExtremeResourceRuntimeSkillWitness] = []
        pets: list[ExtremeResourceRuntimeSkillWitness] = []
        transformations: list[ExtremeResourceRuntimeSkillWitness] = []

        for row in actives:
            if self._concrete(row):
                if row.domain is ExtremeSkillDomain.ARMOR and not self._is_ultimate(row):
                    armor.append(self._witness(self.ARMOR_ABILITY, row))
                if self._is_pet_witness(row):
                    pets.append(self._witness(self.PET_ACTIVE, row))
            if self._is_transformation_witness(row):
                transformations.append(self._witness(self.TRANSFORMED, row))

        armor_rows = self._ordered(armor)
        pet_rows = self._ordered(pets)
        transformation_rows = self._ordered(transformations)
        unresolved: list[str] = []
        if not actives:
            unresolved.append("Canonical active-skill universe is empty for runtime witness audit")
        if not armor_rows:
            unresolved.append("No canonical Armor active witness is available for armor_ability_slotted")
        if not pet_rows:
            unresolved.append("No canonical summon witness is available for pet_active")
        if not transformation_rows:
            unresolved.append("No canonical transformation Ultimate witness is available for transformed")

        return ExtremeResourceRuntimeSkillWitnessCatalog(
            armor_abilities=armor_rows,
            pet_abilities=pet_rows,
            transformation_ultimates=transformation_rows,
            active_skills_reviewed=len(actives),
            denominator_proven=bool(actives) and not unresolved,
            unresolved=tuple(unresolved),
        )


__all__ = [
    "ExtremeResourceRuntimeSkillWitness",
    "ExtremeResourceRuntimeSkillWitnessCatalog",
    "ExtremeResourceRuntimeSkillWitnessCatalogService",
]
