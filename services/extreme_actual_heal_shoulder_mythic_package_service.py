from __future__ import annotations

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


class ExtremeActualHealShoulderMythicPackageService(ExtremeActualHealMythicPackageService):
    """Materialize a provable 5+5+1 shoulder-mythic package.

    Shape:
      * primary set: Chest, Legs, Hands, Waist, Feet (5)
      * secondary set: Head, Necklace, Ring1, active two-slot weapon (5)
      * mythic: Shoulders (1)
      * Ring2: non-set filler

    The active weapon subtype is preserved and must be proven by canonical
    ``gear_set_piece.weapon_type`` data for the secondary ordinary set.
    """

    MYTHIC_SLOT = "Shoulders"

    def __init__(self, database_path: str | Path) -> None:
        super().__init__(database_path)

    def _secondary_without_shoulders_legal(
        self,
        set_id: int,
        raw_category: str | None,
        *,
        weapon_type_id: int,
    ) -> bool:
        if not self._ordinary(set_id, raw_category):
            return False
        rows = self._piece_rows(set_id)
        has_head = any(
            equip_type == self.HEAD_EQUIP_TYPE
            and armor_type > 0
            and weapon_type == 0
            for equip_type, armor_type, weapon_type in rows
        )
        has_neck = any(
            equip_type == self.NECK_EQUIP_TYPE
            and armor_type == 0
            and weapon_type == 0
            for equip_type, armor_type, weapon_type in rows
        )
        has_ring = any(
            equip_type == self.RING_EQUIP_TYPE
            and armor_type == 0
            and weapon_type == 0
            for equip_type, armor_type, weapon_type in rows
        )
        has_exact_weapon = any(
            equip_type == self.TWO_HAND_EQUIP_TYPE
            and weapon_type == int(weapon_type_id)
            for equip_type, _armor_type, weapon_type in rows
        )
        return has_head and has_neck and has_ring and has_exact_weapon

    def _shoulder_mythic_legal(self, set_id: int, raw_category: str | None) -> bool:
        if self.categories.resolve(
            set_id,
            raw_category=raw_category,
        ) is not GearPieceCategory.MYTHIC:
            return False
        rows = self._piece_rows(set_id)
        return (
            len(rows) == 1
            and rows[0][0] == self.SHOULDERS_EQUIP_TYPE
            and rows[0][2] == 0
        )

    def _reviewed_names_for_shape(
        self,
        *,
        shape: str,
        per_objective: int,
        weapon_type_id: int | None = None,
    ) -> tuple[str, ...]:
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
                if gear_set is None:
                    continue
                if shape == "secondary":
                    legal = (
                        weapon_type_id is not None
                        and self._secondary_without_shoulders_legal(
                            gear_set.id,
                            gear_set.category,
                            weapon_type_id=weapon_type_id,
                        )
                    )
                elif shape == "mythic":
                    legal = self._shoulder_mythic_legal(
                        gear_set.id,
                        gear_set.category,
                    )
                else:
                    raise ValueError(f"unknown shoulder mythic package shape: {shape!r}")
                if not legal:
                    continue
                key = row.set_name.casefold()
                if key not in seen:
                    seen.add(key)
                    names.append(row.set_name)
                accepted += 1
                if accepted >= limit:
                    break
        return tuple(names)

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        active_bar: str = "front",
        primary_per_objective: int = 6,
        secondary_per_objective: int = 6,
        mythic_per_objective: int = 6,
    ) -> tuple[BuildCandidate, ...]:
        main, offhand = baseline_build.active_weapon_slots(active_bar)
        weapon_name = str(main.WeaponType or "").strip().casefold()
        weapon_type_id = eso_weapon_type_id_from_saved_name(main.WeaponType)
        if (
            weapon_name not in TWO_SLOT_SET_WEAPON_TYPES
            or weapon_type_id is None
            or not offhand.is_empty
        ):
            return ()

        primary_names = self._reviewed_names(
            shape="primary",
            per_objective=primary_per_objective,
        )
        secondary_names = self._reviewed_names_for_shape(
            shape="secondary",
            per_objective=secondary_per_objective,
            weapon_type_id=weapon_type_id,
        )
        mythic_names = self._reviewed_names_for_shape(
            shape="mythic",
            per_objective=mythic_per_objective,
        )

        result: list[BuildCandidate] = []
        for primary_name in primary_names:
            for secondary_name in secondary_names:
                if primary_name.casefold() == secondary_name.casefold():
                    continue
                for mythic_name in mythic_names:
                    if mythic_name.casefold() in {
                        primary_name.casefold(),
                        secondary_name.casefold(),
                    }:
                        continue

                    build = PlayerBuild.from_dict(baseline_build.to_dict())
                    candidate_main, candidate_offhand = build.active_weapon_slots(active_bar)
                    before = {
                        **{
                            slot: str(build.Armor[slot].get("Set", "") or "")
                            for slot in self.PRIMARY_SLOTS
                        },
                        "Head": str(build.Armor["Head"].get("Set", "") or ""),
                        "Shoulders": str(build.Armor["Shoulders"].get("Set", "") or ""),
                        "Necklace": str(build.Necklace.Set or ""),
                        "Ring1": str(build.Ring1.Set or ""),
                        "Ring2": str(build.Ring2.Set or ""),
                        f"{active_bar}.weapon": str(candidate_main.Set or ""),
                    }

                    for slot in self.PRIMARY_SLOTS:
                        build.Armor[slot]["Set"] = primary_name
                    build.Armor["Head"]["Set"] = secondary_name
                    build.Armor["Shoulders"]["Set"] = mythic_name
                    build.Necklace.Set = secondary_name
                    build.Ring1.Set = secondary_name
                    build.Ring2.Set = ""
                    build.Ring2.Set2 = ""
                    candidate_main.Set = secondary_name
                    candidate_main.Set2 = ""
                    candidate_offhand.Set = ""
                    candidate_offhand.Set2 = ""

                    after = {
                        **{slot: primary_name for slot in self.PRIMARY_SLOTS},
                        "Head": secondary_name,
                        "Shoulders": mythic_name,
                        "Necklace": secondary_name,
                        "Ring1": secondary_name,
                        "Ring2": "",
                        f"{active_bar}.weapon": secondary_name,
                    }

                    result.append(
                        ExtremeCompleteOptimizationService._direct_candidate(
                            build,
                            character_id=character_id,
                            baseline_build_id=baseline_build_id,
                            token=(
                                f"actual-heal-5plus5plus1-shoulder:{primary_name}:"
                                f"{secondary_name}:{mythic_name}:{active_bar}"
                            ),
                            path="Gear.FivePiecePlusFivePiecePlusShoulderMythic",
                            before=before,
                            after=after,
                            source="extreme:actual-heal:gear-package:5+5+1:shoulder-mythic",
                        )
                    )
        return tuple(result)
