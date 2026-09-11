from __future__ import annotations

"""Materialize legal skill witnesses for Extreme max-resource runtime conditions.

This service owns bar/runtime witness placement only.  It performs no stat math and
never activates a gear condition merely because that condition exists in the global
denominator.  Callers provide the condition markers required by one concrete
candidate; this layer then proves and materializes the skill-dependent subset:

* ``armor_ability_slotted`` -> a canonical Armor active compatible with an armor
  weight actually worn by the build;
* ``pet_active`` -> a canonical pet-producing active from a class skill line carried
  by the selected Extreme class route;
* ``transformed`` -> a canonical transformation Ultimate. Werewolf Transformation
  is a legal universal route when available and explicitly marks the hypothetical
  build as Werewolf; otherwise a class-line transformation must belong to the route.

Normal skill slots and the Ultimate slot remain separate.  When a required witness
must displace an existing active-bar skill, that displacement is retained as explicit
evidence so downstream canonical scoring sees the real bar tradeoff rather than an
imaginary extra slot.
"""

from dataclasses import dataclass
from pathlib import Path

from models.build_model import BAR_SKILL_COUNT, PlayerBuild
from services.extreme_heal_class_route_service import (
    ExtremeHealClassRoute,
    canonical_class_skill_line_id,
)
from services.extreme_resource_runtime_skill_witness_catalog_service import (
    ExtremeResourceRuntimeSkillWitness,
    ExtremeResourceRuntimeSkillWitnessCatalogService,
)


_SKILL_CONDITIONS = frozenset(
    {
        "armor_ability_slotted",
        "pet_active",
        "transformed",
    }
)
_ARMOR_LINE_BY_WEIGHT = {
    "light": "light_armor",
    "medium": "medium_armor",
    "heavy": "heavy_armor",
}


@dataclass(frozen=True)
class ExtremeResourceRuntimeSkillWitnessMaterialization:
    build: PlayerBuild
    requested_conditions: tuple[str, ...]
    active_conditions: tuple[str, ...]
    witnesses: tuple[tuple[str, str], ...]
    displaced_skills: tuple[tuple[int, str], ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def projection_complete(self) -> bool:
        return bool(
            not self.unresolved
            and set(self.requested_conditions).issubset(set(self.active_conditions))
        )


class ExtremeResourceRuntimeSkillWitnessMaterializationService:
    """Place exact skill/runtime witnesses onto one materialized Extreme build."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        catalog_service: ExtremeResourceRuntimeSkillWitnessCatalogService | None = None,
    ) -> None:
        if database_path is None and catalog_service is None:
            raise ValueError("database_path or catalog_service is required")
        self.catalog_service = catalog_service or ExtremeResourceRuntimeSkillWitnessCatalogService(
            database_path  # type: ignore[arg-type]
        )

    @staticmethod
    def _normalize(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    str(value or "").strip()
                    for value in values
                    if str(value or "").strip() in _SKILL_CONDITIONS
                },
                key=str.casefold,
            )
        )

    @staticmethod
    def _route_lines(route: ExtremeHealClassRoute) -> frozenset[str]:
        return frozenset(
            canonical_class_skill_line_id(line)
            for line in route.equipped_skill_lines
        )

    @staticmethod
    def _worn_armor_lines(build: PlayerBuild) -> frozenset[str]:
        lines: set[str] = set()
        for entry in build.Armor.values():
            weight = str(entry.get("Weight", "") or "").strip().casefold()
            line = _ARMOR_LINE_BY_WEIGHT.get(weight)
            if line:
                lines.add(line)
        return frozenset(lines)

    @staticmethod
    def _is_ultimate(witness: ExtremeResourceRuntimeSkillWitness) -> bool:
        return "ultimate" in str(witness.skill_type or "").casefold()

    @staticmethod
    def _bar(build: PlayerBuild, active_bar: str) -> list[str]:
        values = list(
            build.BackBarSkills
            if str(active_bar or "front").strip().casefold() == "back"
            else build.FrontBarSkills
        )
        values = values[: BAR_SKILL_COUNT + 1]
        values += [""] * (BAR_SKILL_COUNT + 1 - len(values))
        return values

    @staticmethod
    def _write_bar(build: PlayerBuild, active_bar: str, skills: list[str]) -> None:
        if str(active_bar or "front").strip().casefold() == "back":
            build.BackBarSkills = skills
        else:
            build.FrontBarSkills = skills

    @staticmethod
    def _choose_normal_slot(skills: list[str], reserved: set[int]) -> int | None:
        for index in range(BAR_SKILL_COUNT):
            if index not in reserved and not str(skills[index] or "").strip():
                return index
        for index in range(BAR_SKILL_COUNT - 1, -1, -1):
            if index not in reserved:
                return index
        return None

    @staticmethod
    def _pick_armor(
        rows: tuple[ExtremeResourceRuntimeSkillWitness, ...],
        worn_lines: frozenset[str],
    ) -> ExtremeResourceRuntimeSkillWitness | None:
        eligible = tuple(
            row
            for row in rows
            if canonical_class_skill_line_id(row.skill_line) in worn_lines
            and "ultimate" not in str(row.skill_type or "").casefold()
        )
        return eligible[0] if eligible else None

    @staticmethod
    def _pick_pet(
        rows: tuple[ExtremeResourceRuntimeSkillWitness, ...],
        route_lines: frozenset[str],
    ) -> ExtremeResourceRuntimeSkillWitness | None:
        eligible = tuple(
            row
            for row in rows
            if canonical_class_skill_line_id(row.skill_line) in route_lines
        )
        if not eligible:
            return None
        return sorted(
            eligible,
            key=lambda row: (
                "ultimate" in str(row.skill_type or "").casefold(),
                row.skill_line.casefold(),
                row.name.casefold(),
            ),
        )[0]

    @staticmethod
    def _pick_transformation(
        rows: tuple[ExtremeResourceRuntimeSkillWitness, ...],
        route_lines: frozenset[str],
    ) -> tuple[ExtremeResourceRuntimeSkillWitness | None, bool]:
        werewolf = tuple(
            row
            for row in rows
            if canonical_class_skill_line_id(row.skill_line) == "werewolf"
        )
        if werewolf:
            return werewolf[0], True
        route_rows = tuple(
            row
            for row in rows
            if canonical_class_skill_line_id(row.skill_line) in route_lines
        )
        return (route_rows[0], False) if route_rows else (None, False)

    def materialize(
        self,
        *,
        build: PlayerBuild,
        route: ExtremeHealClassRoute,
        required_conditions: tuple[str, ...],
        active_bar: str = "front",
    ) -> ExtremeResourceRuntimeSkillWitnessMaterialization:
        requested = self._normalize(required_conditions)
        result = PlayerBuild.from_dict(build.to_dict())
        if not requested:
            return ExtremeResourceRuntimeSkillWitnessMaterialization(
                build=result,
                requested_conditions=(),
                active_conditions=(),
                witnesses=(),
            )

        catalog = self.catalog_service.build()
        unresolved: list[str] = list(catalog.unresolved) if not catalog.denominator_proven else []
        active: set[str] = set()
        witness_rows: list[tuple[str, str]] = []
        displaced: list[tuple[int, str]] = []
        route_lines = self._route_lines(route)
        worn_lines = self._worn_armor_lines(result)
        skills = self._bar(result, active_bar)
        reserved_normal_slots: set[int] = set()

        def place(condition: str, witness: ExtremeResourceRuntimeSkillWitness) -> bool:
            if condition == "transformed" or self._is_ultimate(witness):
                old = str(skills[BAR_SKILL_COUNT] or "").strip()
                if old and old.casefold() != witness.name.casefold():
                    displaced.append((BAR_SKILL_COUNT, old))
                skills[BAR_SKILL_COUNT] = witness.name
                active.add(condition)
                witness_rows.append((condition, witness.name))
                return True
            slot = self._choose_normal_slot(skills, reserved_normal_slots)
            if slot is None:
                unresolved.append(f"{condition} has no legal normal active-bar slot")
                return False
            old = str(skills[slot] or "").strip()
            if old and old.casefold() != witness.name.casefold():
                displaced.append((slot, old))
            skills[slot] = witness.name
            reserved_normal_slots.add(slot)
            active.add(condition)
            witness_rows.append((condition, witness.name))
            return True

        if "armor_ability_slotted" in requested:
            witness = self._pick_armor(catalog.armor_abilities, worn_lines)
            if witness is None:
                unresolved.append(
                    "armor_ability_slotted has no canonical Armor witness compatible with worn armor weights"
                )
            else:
                place("armor_ability_slotted", witness)

        if "pet_active" in requested:
            witness = self._pick_pet(catalog.pet_abilities, route_lines)
            if witness is None:
                unresolved.append(
                    "pet_active has no canonical pet witness on the selected Extreme class route"
                )
            else:
                place("pet_active", witness)

        if "transformed" in requested:
            witness, werewolf = self._pick_transformation(
                catalog.transformation_ultimates,
                route_lines,
            )
            if witness is None:
                unresolved.append(
                    "transformed has no canonical Werewolf or route-compatible transformation Ultimate witness"
                )
            elif place("transformed", witness) and werewolf:
                result.Werewolf = True
                result.Vampire = False

        self._write_bar(result, active_bar, skills)
        return ExtremeResourceRuntimeSkillWitnessMaterialization(
            build=result,
            requested_conditions=requested,
            active_conditions=tuple(sorted(active, key=str.casefold)),
            witnesses=tuple(witness_rows),
            displaced_skills=tuple(displaced),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeResourceRuntimeSkillWitnessMaterialization",
    "ExtremeResourceRuntimeSkillWitnessMaterializationService",
]
