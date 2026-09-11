from __future__ import annotations

"""Canonical skill witnesses for Extreme max-resource runtime conditions.

This service owns identity/evidence only.  It inventories the canonical player-skill
universe for the three runtime condition families that require an actual skill or
transformation witness before a conditional gear bonus may be activated:

* ``armor_ability_slotted`` -> a bar-eligible active from an Armor skill line;
* ``pet_active`` -> an active whose canonical description explicitly summons a pet;
* ``transformed`` -> a transformation Ultimate.

It performs no stat arithmetic and does not choose a winning candidate.  Candidate
legality/materialization remains a separate layer so the global denominator cannot
silently grant a skill the selected build cannot actually slot.
"""

from dataclasses import dataclass
from pathlib import Path

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
    def _concrete(row: ExtremePlayerSkillRecord) -> bool:
        return bool(row.max_rank_ability_id is not None and row.is_player and not row.is_passive)

    @classmethod
    def _is_pet_witness(cls, row: ExtremePlayerSkillRecord) -> bool:
        if not cls._concrete(row):
            return False
        text = " ".join(str(row.description or "").casefold().split())
        if not text:
            return False
        # ESO summon abilities consistently identify the summon in the canonical
        # max-rank tooltip.  This deliberately requires explicit summon wording;
        # class/skill-line membership alone is not evidence that a pet is active.
        return "summon" in text and any(
            marker in text
            for marker in (
                "pet",
                "familiar",
                "clannfear",
                "twilight",
                "atronach",
                "bear",
                "guardian",
                "companion",
                "shade",
                "blastbones",
                "skeletal",
            )
        )

    @classmethod
    def _is_transformation_witness(cls, row: ExtremePlayerSkillRecord) -> bool:
        if not cls._concrete(row) or not cls._is_ultimate(row):
            return False
        name = " ".join(str(row.name or "").casefold().split())
        text = " ".join(str(row.description or "").casefold().split())
        line = " ".join(str(row.skill_line or "").casefold().split())
        return bool(
            "transformation" in name
            or "transform into" in text
            or "transform yourself" in text
            or (line == "werewolf" and "transform" in text)
        )

    @staticmethod
    def _witness(condition: str, row: ExtremePlayerSkillRecord) -> ExtremeResourceRuntimeSkillWitness:
        if row.max_rank_ability_id is None:
            raise ValueError(f"runtime skill witness lacks max-rank ability identity: {row.name}")
        return ExtremeResourceRuntimeSkillWitness(
            condition=condition,
            skill_id=int(row.skill_id),
            base_ability_id=(int(row.base_ability_id) if row.base_ability_id is not None else None),
            ability_id=int(row.max_rank_ability_id),
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
            if not self._concrete(row):
                continue
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
