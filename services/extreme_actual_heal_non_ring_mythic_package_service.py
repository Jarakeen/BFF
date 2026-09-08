from __future__ import annotations

from itertools import combinations
from pathlib import Path

from minmax.build_candidate import BuildCandidate
from minmax.character_build.gear_piece import GearPieceCategory
from minmax.eso_weapon_type_id import eso_weapon_type_id_from_saved_name
from minmax.gear_stat_inputs import TWO_SLOT_SET_WEAPON_TYPES
from models.build_model import PlayerBuild
from services.extreme_actual_heal_mythic_package_service import (
    ExtremeActualHealMythicPackageService,
)
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class ExtremeActualHealNonRingMythicPackageService(ExtremeActualHealMythicPackageService):
    """Materialize reviewed 5+5+1 packages around any proven non-ring mythic slot.

    The imported ``gear_set_piece.equip_type`` is the authority for the mythic's
    physical slot. This service supports the seven armor slots plus Necklace;
    Ring mythics remain covered by ``ExtremeActualHealMythicPackageService``.

    Both ordinary five-piece sets are assigned around the occupied mythic slot
    using only positions each set can canonically occupy. An active two-slot
    weapon may contribute two pieces only when the ordinary set contains that
    exact saved weapon subtype. Explicit paired main/off-hand configurations may
    contribute one piece per hand only when the set contains both exact subtypes.
    No slot or set count is inferred from a tooltip or aggregate weapon label.
    """

    # ESO/UESP mined-item equipType identities used by gear_set_piece.
    EQUIP_TYPE_TO_SLOT = {
        1: "Head",
        2: "Chest",
        3: "Feet",
        4: "Shoulders",
        5: "Hands",
        6: "Legs",
        7: "Waist",
        8: "Necklace",
    }
    TWO_HAND_EQUIP_TYPE = 11

    # position, equip_type, set-piece count
    NON_WEAPON_POSITIONS = (
        ("Head", 1, 1),
        ("Chest", 2, 1),
        ("Feet", 3, 1),
        ("Shoulders", 4, 1),
        ("Hands", 5, 1),
        ("Legs", 6, 1),
        ("Waist", 7, 1),
        ("Necklace", 8, 1),
        ("Ring1", 9, 1),
        ("Ring2", 9, 1),
    )
    TWO_SLOT_WEAPON_POSITION = ("ActiveWeapon", TWO_HAND_EQUIP_TYPE, 2)
    PAIRED_MAIN_POSITION = ("ActiveMainHand", 0, 1)
    PAIRED_OFFHAND_POSITION = ("ActiveOffHand", 0, 1)

    def __init__(self, database_path: str | Path) -> None:
        super().__init__(database_path)

    def _reviewed_ordinary_names(self, *, per_objective: int) -> tuple[str, ...]:
        names: list[str] = []
        seen: set[str] = set()
        limit = max(1, int(per_objective))
        for objective in self.OBJECTIVES:
            accepted = 0
            for row in ExtremeGearSetObjectiveService.candidates_for_objective(
                self.repository,
                objective,
            ):
                if not row.mechanic_complete or row.reviewed_delta <= 0:
                    continue
                gear_set = self.repository.get_set_by_id(row.set_id)
                if gear_set is None or not self._ordinary(gear_set.id, gear_set.category):
                    continue
                key = row.set_name.casefold()
                if key not in seen:
                    seen.add(key)
                    names.append(row.set_name)
                accepted += 1
                if accepted >= limit:
                    break
        return tuple(names)

    def _reviewed_non_ring_mythics(
        self,
        *,
        per_objective: int,
    ) -> tuple[tuple[str, str, int], ...]:
        result: list[tuple[str, str, int]] = []
        seen: set[str] = set()
        limit = max(1, int(per_objective))
        for objective in self.OBJECTIVES:
            accepted = 0
            for row in ExtremeGearSetObjectiveService.candidates_for_objective(
                self.repository,
                objective,
            ):
                if not row.mechanic_complete or row.reviewed_delta <= 0:
                    continue
                gear_set = self.repository.get_set_by_id(row.set_id)
                if gear_set is None:
                    continue
                if self.categories.resolve(
                    gear_set.id,
                    raw_category=gear_set.category,
                ) is not GearPieceCategory.MYTHIC:
                    continue
                rows = self._piece_rows(gear_set.id)
                if len(rows) != 1:
                    continue
                equip_type, _armor_type, weapon_type = rows[0]
                slot = self.EQUIP_TYPE_TO_SLOT.get(int(equip_type))
                if slot is None or int(weapon_type or 0) != 0:
                    continue
                key = row.set_name.casefold()
                if key not in seen:
                    seen.add(key)
                    result.append((row.set_name, slot, int(equip_type)))
                accepted += 1
                if accepted >= limit:
                    break
        return tuple(result)

    @staticmethod
    def _active_weapon_positions(
        baseline_build: PlayerBuild,
        *,
        active_bar: str,
    ) -> tuple[tuple[str, int, int, int, bool], ...]:
        """Return exact active-weapon positions as package-search evidence.

        Tuple shape is ``(position, equip_type, piece_count, weapon_type_id,
        exact_equip_type_required)``. Two-slot weapons count as two set pieces and
        require the canonical two-hand equip family. Explicit paired weapons count
        one piece per hand and require only the exact weapon subtype to exist in
        the set's canonical piece universe, matching the shared arena-set proof.
        """

        main, offhand = baseline_build.active_weapon_slots(active_bar)
        main_id = eso_weapon_type_id_from_saved_name(main.WeaponType)
        if main_id is None:
            return ()

        if not offhand.is_empty:
            offhand_id = eso_weapon_type_id_from_saved_name(offhand.WeaponType)
            if offhand_id is None:
                return ()
            return (
                ("ActiveMainHand", 0, 1, int(main_id), False),
                ("ActiveOffHand", 0, 1, int(offhand_id), False),
            )

        weapon_name = str(main.WeaponType or "").strip().casefold()
        if weapon_name not in TWO_SLOT_SET_WEAPON_TYPES:
            return ()
        return (
            (
                "ActiveWeapon",
                ExtremeActualHealNonRingMythicPackageService.TWO_HAND_EQUIP_TYPE,
                2,
                int(main_id),
                True,
            ),
        )

    def _available_positions(
        self,
        set_name: str,
        *,
        mythic_slot: str,
        weapon_type_id: int | None = None,
        weapon_positions: tuple[tuple[str, int, int, int, bool], ...] | None = None,
    ) -> tuple[tuple[str, int, int], ...]:
        gear_set = self.repository.get_set(set_name)
        if gear_set is None or not self._ordinary(gear_set.id, gear_set.category):
            return ()
        rows = self._piece_rows(gear_set.id)
        available: list[tuple[str, int, int]] = []
        for position, equip_type, count in self.NON_WEAPON_POSITIONS:
            if position == mythic_slot:
                continue
            if any(
                row_equip == equip_type and int(row_weapon or 0) == 0
                for row_equip, _row_armor, row_weapon in rows
            ):
                available.append((position, equip_type, count))

        if weapon_positions is None and weapon_type_id is not None:
            weapon_positions = (
                ("ActiveWeapon", self.TWO_HAND_EQUIP_TYPE, 2, int(weapon_type_id), True),
            )
        for position, equip_type, count, exact_weapon_type, require_equip_type in (
            weapon_positions or ()
        ):
            if any(
                int(row_weapon or 0) == int(exact_weapon_type)
                and (not require_equip_type or row_equip == equip_type)
                for row_equip, _row_armor, row_weapon in rows
            ):
                available.append((position, equip_type, count))
        return tuple(available)

    @staticmethod
    def _five_piece_combinations(
        positions: tuple[tuple[str, int, int], ...],
    ) -> tuple[tuple[str, ...], ...]:
        found: list[tuple[str, ...]] = []
        for size in range(1, len(positions) + 1):
            for chosen in combinations(positions, size):
                if sum(int(item[2]) for item in chosen) != 5:
                    continue
                found.append(tuple(item[0] for item in chosen))
        return tuple(found)

    def _assignment(
        self,
        primary_name: str,
        secondary_name: str,
        *,
        mythic_slot: str,
        weapon_type_id: int | None = None,
        weapon_positions: tuple[tuple[str, int, int, int, bool], ...] | None = None,
    ) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
        primary = self._five_piece_combinations(
            self._available_positions(
                primary_name,
                mythic_slot=mythic_slot,
                weapon_type_id=weapon_type_id,
                weapon_positions=weapon_positions,
            )
        )
        secondary = self._five_piece_combinations(
            self._available_positions(
                secondary_name,
                mythic_slot=mythic_slot,
                weapon_type_id=weapon_type_id,
                weapon_positions=weapon_positions,
            )
        )
        for first in primary:
            first_slots = set(first)
            for second in secondary:
                if first_slots.isdisjoint(second):
                    return first, second
        return None

    @staticmethod
    def _set_position(
        build: PlayerBuild,
        position: str,
        set_name: str,
        *,
        active_bar: str,
    ) -> None:
        if position in build.Armor:
            build.Armor[position]["Set"] = set_name
            build.Armor[position]["Set2"] = ""
            return
        if position == "Necklace":
            build.Necklace.Set = set_name
            build.Necklace.Set2 = ""
            return
        if position == "Ring1":
            build.Ring1.Set = set_name
            build.Ring1.Set2 = ""
            return
        if position == "Ring2":
            build.Ring2.Set = set_name
            build.Ring2.Set2 = ""
            return
        main, offhand = build.active_weapon_slots(active_bar)
        if position == "ActiveWeapon":
            main.Set = set_name
            main.Set2 = ""
            offhand.Set = ""
            offhand.Set2 = ""
            return
        if position == "ActiveMainHand":
            main.Set = set_name
            main.Set2 = ""
            return
        if position == "ActiveOffHand":
            offhand.Set = set_name
            offhand.Set2 = ""
            return
        raise ValueError(f"Unknown actual-heal package position: {position!r}")

    @classmethod
    def _clear_package_positions(cls, build: PlayerBuild, *, active_bar: str) -> None:
        for position, _equip_type, _count in cls.NON_WEAPON_POSITIONS:
            cls._set_position(build, position, "", active_bar=active_bar)
        main, offhand = build.active_weapon_slots(active_bar)
        main.Set = ""
        main.Set2 = ""
        offhand.Set = ""
        offhand.Set2 = ""

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        active_bar: str = "front",
        ordinary_per_objective: int = 8,
        mythic_per_objective: int = 8,
    ) -> tuple[BuildCandidate, ...]:
        weapon_positions = self._active_weapon_positions(
            baseline_build,
            active_bar=active_bar,
        )
        if not weapon_positions:
            return ()

        ordinary_names = self._reviewed_ordinary_names(
            per_objective=ordinary_per_objective,
        )
        mythics = self._reviewed_non_ring_mythics(
            per_objective=mythic_per_objective,
        )
        result: list[BuildCandidate] = []
        for mythic_name, mythic_slot, equip_type in mythics:
            for primary_name in ordinary_names:
                for secondary_name in ordinary_names:
                    if primary_name.casefold() >= secondary_name.casefold():
                        continue
                    if mythic_name.casefold() in {
                        primary_name.casefold(),
                        secondary_name.casefold(),
                    }:
                        continue
                    assignment = self._assignment(
                        primary_name,
                        secondary_name,
                        mythic_slot=mythic_slot,
                        weapon_positions=weapon_positions,
                    )
                    if assignment is None:
                        continue
                    primary_positions, secondary_positions = assignment
                    build = PlayerBuild.from_dict(baseline_build.to_dict())
                    self._clear_package_positions(build, active_bar=active_bar)
                    for position in primary_positions:
                        self._set_position(
                            build,
                            position,
                            primary_name,
                            active_bar=active_bar,
                        )
                    for position in secondary_positions:
                        self._set_position(
                            build,
                            position,
                            secondary_name,
                            active_bar=active_bar,
                        )
                    self._set_position(
                        build,
                        mythic_slot,
                        mythic_name,
                        active_bar=active_bar,
                    )
                    result.append(
                        ExtremeCompleteOptimizationService._direct_candidate(
                            build,
                            character_id=character_id,
                            baseline_build_id=baseline_build_id,
                            token=(
                                f"actual-heal-5plus5plus1-slot-mythic:{mythic_slot}:"
                                f"{primary_name}:{secondary_name}:{mythic_name}:{active_bar}"
                            ),
                            path="Gear.FivePiecePlusFivePiecePlusSlotMythic",
                            before={"mythic_slot": mythic_slot},
                            after={
                                "primary": primary_name,
                                "primary_positions": primary_positions,
                                "secondary": secondary_name,
                                "secondary_positions": secondary_positions,
                                "mythic": mythic_name,
                                "mythic_slot": mythic_slot,
                                "mythic_equip_type": equip_type,
                                "weapon_positions": tuple(
                                    position for position, _equip, _count, _type, _strict in weapon_positions
                                ),
                            },
                            source="extreme:actual-heal:gear-package:5+5+1:slot-mythic",
                        )
                    )
        return tuple(result)
