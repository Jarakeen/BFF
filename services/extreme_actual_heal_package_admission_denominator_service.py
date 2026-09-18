from __future__ import annotations

"""E2 H1 package-admission denominator for special gear families.

This proof layer is deliberately narrower than package scoring. It asks whether
special sets that have a standing or package-owned H1 consequence are admitted by
an exhaustive package-discovery path. Purely conditional rows remain owned by the
explicit runtime/proc scenario layer and are not required in the standing search.
"""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_actual_heal_arena_weapon_package_service import (
    ExtremeActualHealArenaWeaponPackageService,
)
from services.extreme_actual_heal_monster_package_service import (
    ExtremeActualHealMonsterPackageService,
)
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)
from services.extreme_actual_heal_non_ring_mythic_package_service import (
    ExtremeActualHealNonRingMythicPackageService,
)
from services.extreme_actual_heal_special_gear_denominator_service import (
    ExtremeActualHealSpecialGearDenominatorService,
)


@dataclass(frozen=True)
class ExtremeActualHealPackageAdmissionFamily:
    family: str
    expected: tuple[str, ...]
    admitted: tuple[str, ...]

    @property
    def missing(self) -> tuple[str, ...]:
        admitted = {name.casefold() for name in self.admitted}
        return tuple(name for name in self.expected if name.casefold() not in admitted)

    @property
    def unexpected(self) -> tuple[str, ...]:
        expected = {name.casefold() for name in self.expected}
        return tuple(name for name in self.admitted if name.casefold() not in expected)

    @property
    def proven(self) -> bool:
        return not self.missing and not self.unexpected


@dataclass(frozen=True)
class ExtremeActualHealPackageAdmissionDenominator:
    families: tuple[ExtremeActualHealPackageAdmissionFamily, ...]

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(
            f"{row.family}:{name}"
            for row in self.families
            for name in row.missing
        )

    @property
    def unexpected(self) -> tuple[str, ...]:
        return tuple(
            f"{row.family}:{name}"
            for row in self.families
            for name in row.unexpected
        )

    @property
    def denominator_proven(self) -> bool:
        return bool(self.families) and all(row.proven for row in self.families)


class ExtremeActualHealPackageAdmissionDenominatorService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.special = ExtremeActualHealSpecialGearDenominatorService(self.database_path)
        self.arena = ExtremeActualHealArenaWeaponPackageService(self.database_path)
        self.monster = ExtremeActualHealMonsterPackageService(self.database_path)
        self.ring_mythic = ExtremeActualHealMythicPackageService(self.database_path)
        self.slot_mythic = ExtremeActualHealNonRingMythicPackageService(self.database_path)

    @staticmethod
    def _standing_or_package(row) -> bool:
        return bool(row.relevant_objectives or row.package_objectives)

    def _expected_arena_weapons(self, rows) -> tuple[str, ...]:
        return tuple(
            row.set_name
            for row in rows
            if row.family == "arena_weapon"
        )

    def _expected_monsters(self, rows) -> tuple[str, ...]:
        return tuple(
            row.set_name
            for row in rows
            if row.family == "monster" and self._standing_or_package(row)
        )

    def _expected_ring_mythics(self, rows) -> tuple[str, ...]:
        result: list[str] = []
        for row in rows:
            if row.family != "mythic" or not self._standing_or_package(row):
                continue
            gear_set = self.ring_mythic.repository.get_set(row.set_name)
            if gear_set is None:
                continue
            if self.ring_mythic._ring_mythic_legal(
                gear_set.id,
                gear_set.category,
            ):
                result.append(row.set_name)
        return tuple(result)

    def _expected_non_ring_mythics(self, rows) -> tuple[str, ...]:
        result: list[str] = []
        for row in rows:
            if row.family != "mythic" or not self._standing_or_package(row):
                continue
            gear_set = self.slot_mythic.repository.get_set(row.set_name)
            if gear_set is None:
                continue
            pieces = self.slot_mythic._piece_rows(gear_set.id)
            if len(pieces) != 1:
                continue
            equip_type, _armor_type, weapon_type = pieces[0]
            if int(weapon_type or 0) != 0:
                continue
            if self.slot_mythic.EQUIP_TYPE_TO_SLOT.get(int(equip_type)) is None:
                continue
            result.append(row.set_name)
        return tuple(result)

    def build(self) -> ExtremeActualHealPackageAdmissionDenominator:
        special = self.special.build()
        rows = special.rows

        arena_expected = self._expected_arena_weapons(rows)
        arena_admitted = tuple(
            name for name, _piece_rows in self.arena._arena_set_piece_rows()
        )

        monster_expected = self._expected_monsters(rows)
        monster_admitted = self.monster._reviewed_names(
            monster=True,
            per_objective=None,
        )

        ring_expected = self._expected_ring_mythics(rows)
        ring_admitted = self.ring_mythic._reviewed_names(
            shape="mythic",
            per_objective=None,
        )

        non_ring_expected = self._expected_non_ring_mythics(rows)
        non_ring_admitted = tuple(
            name
            for name, _slot, _equip_type in self.slot_mythic._reviewed_non_ring_mythics(
                per_objective=None,
            )
        )

        families = (
            ExtremeActualHealPackageAdmissionFamily(
                family="arena_weapon_structure",
                expected=arena_expected,
                admitted=arena_admitted,
            ),
            ExtremeActualHealPackageAdmissionFamily(
                family="monster",
                expected=monster_expected,
                admitted=monster_admitted,
            ),
            ExtremeActualHealPackageAdmissionFamily(
                family="ring_mythic",
                expected=ring_expected,
                admitted=ring_admitted,
            ),
            ExtremeActualHealPackageAdmissionFamily(
                family="non_ring_mythic",
                expected=non_ring_expected,
                admitted=non_ring_admitted,
            ),
        )
        return ExtremeActualHealPackageAdmissionDenominator(families=families)


__all__ = [
    "ExtremeActualHealPackageAdmissionFamily",
    "ExtremeActualHealPackageAdmissionDenominator",
    "ExtremeActualHealPackageAdmissionDenominatorService",
]
