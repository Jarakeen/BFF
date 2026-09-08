from __future__ import annotations

from pathlib import Path
import sqlite3

from minmax.build_candidate import BuildCandidate
from minmax.character_build.gear_piece import GearPieceCategory
from minmax.eso_weapon_type_id import eso_weapon_type_id_from_saved_name
from minmax.gear_set_category_resolver import GearSetCategoryResolver
from minmax.gear_set_repository import GearSetRepository
from minmax.gear_stat_inputs import TWO_SLOT_SET_WEAPON_TYPES
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class ExtremeActualHealMythicPackageService:
    """Materialize a narrow, provable 5+5+1 ring-mythic package shape.

    The healing skill may depend on the active weapon line, so this service never
    changes the saved weapon subtype. The baseline must already use a concrete
    two-slot weapon, and the secondary ordinary set must contain that exact ESO
    weapon subtype in canonical ``gear_set_piece.weapon_type`` data.

    A ring mythic occupies Ring1. The package is then:

    * primary set: Chest, Legs, Hands, Waist, Feet (5)
    * secondary set: Head, Shoulders, Necklace, active two-slot weapon (5)
    * mythic: Ring1 (1)

    Non-ring mythics and arena-weapon replacement remain separate package shapes.
    """

    HEAD_EQUIP_TYPE = GearSetCategoryResolver.HEAD_EQUIP_TYPE
    SHOULDERS_EQUIP_TYPE = GearSetCategoryResolver.SHOULDERS_EQUIP_TYPE
    NECK_EQUIP_TYPE = 8
    RING_EQUIP_TYPE = 9
    TWO_HAND_EQUIP_TYPE = 11

    PRIMARY_SLOTS = ("Chest", "Legs", "Hands", "Waist", "Feet")
    SECONDARY_ARMOR_SLOTS = ("Head", "Shoulders")
    OBJECTIVES = (
        "healing_done",
        "critical_healing",
        "spell_damage",
        "weapon_damage",
    )

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.repository = GearSetRepository(self.database_path)
        self.categories = GearSetCategoryResolver(self.database_path)

    def _piece_rows(self, set_id: int) -> tuple[tuple[int, int, int], ...]:
        with sqlite3.connect(self.database_path) as db:
            tables = {
                str(row[0])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "gear_set_piece" not in tables:
                return ()
            rows = db.execute(
                """
                SELECT equip_type, COALESCE(armor_type, 0), COALESCE(weapon_type, 0)
                FROM gear_set_piece
                WHERE set_id = ? AND equip_type IS NOT NULL
                ORDER BY equip_type, armor_type, weapon_type
                """,
                (int(set_id),),
            ).fetchall()
        return tuple((int(e), int(a), int(w)) for e, a, w in rows)

    def _ordinary(self, set_id: int, raw_category: str | None) -> bool:
        return self.categories.resolve(
            set_id,
            raw_category=raw_category,
        ) is GearPieceCategory.SET_PIECE

    def _primary_legal(self, set_id: int, raw_category: str | None) -> bool:
        if not self._ordinary(set_id, raw_category):
            return False
        armor_types = {
            equip_type
            for equip_type, armor_type, weapon_type in self._piece_rows(set_id)
            if armor_type > 0 and weapon_type == 0
        }
        return len(
            armor_types - {self.HEAD_EQUIP_TYPE, self.SHOULDERS_EQUIP_TYPE}
        ) >= len(self.PRIMARY_SLOTS)

    def _secondary_legal(
        self,
        set_id: int,
        raw_category: str | None,
        *,
        weapon_type_id: int,
    ) -> bool:
        if not self._ordinary(set_id, raw_category):
            return False
        rows = self._piece_rows(set_id)
        armor_types = {
            equip_type
            for equip_type, armor_type, weapon_type in rows
            if armor_type > 0 and weapon_type == 0
        }
        has_neck = any(
            equip_type == self.NECK_EQUIP_TYPE
            and armor_type == 0
            and weapon_type == 0
            for equip_type, armor_type, weapon_type in rows
        )
        has_exact_weapon = any(
            equip_type == self.TWO_HAND_EQUIP_TYPE
            and weapon_type == int(weapon_type_id)
            for equip_type, _armor_type, weapon_type in rows
        )
        return (
            {self.HEAD_EQUIP_TYPE, self.SHOULDERS_EQUIP_TYPE}.issubset(armor_types)
            and has_neck
            and has_exact_weapon
        )

    def _ring_mythic_legal(self, set_id: int, raw_category: str | None) -> bool:
        if self.categories.resolve(
            set_id,
            raw_category=raw_category,
        ) is not GearPieceCategory.MYTHIC:
            return False
        rows = self._piece_rows(set_id)
        return len(rows) == 1 and rows[0] == (self.RING_EQUIP_TYPE, 0, 0)

    def _reviewed_names(
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
                if shape == "primary":
                    legal = self._primary_legal(gear_set.id, gear_set.category)
                elif shape == "secondary":
                    legal = (
                        weapon_type_id is not None
                        and self._secondary_legal(
                            gear_set.id,
                            gear_set.category,
                            weapon_type_id=weapon_type_id,
                        )
                    )
                elif shape == "mythic":
                    legal = self._ring_mythic_legal(gear_set.id, gear_set.category)
                else:
                    raise ValueError(f"unknown mythic package shape: {shape!r}")
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
        secondary_names = self._reviewed_names(
            shape="secondary",
            per_objective=secondary_per_objective,
            weapon_type_id=weapon_type_id,
        )
        mythic_names = self._reviewed_names(
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
                            for slot in (*self.PRIMARY_SLOTS, *self.SECONDARY_ARMOR_SLOTS)
                        },
                        "Necklace": str(build.Necklace.Set or ""),
                        "Ring1": str(build.Ring1.Set or ""),
                        f"{active_bar}.weapon": str(candidate_main.Set or ""),
                    }

                    for slot in self.PRIMARY_SLOTS:
                        build.Armor[slot]["Set"] = primary_name
                    for slot in self.SECONDARY_ARMOR_SLOTS:
                        build.Armor[slot]["Set"] = secondary_name
                    build.Necklace.Set = secondary_name
                    build.Ring1.Set = mythic_name
                    candidate_main.Set = secondary_name
                    candidate_main.Set2 = ""
                    candidate_offhand.Set = ""
                    candidate_offhand.Set2 = ""

                    after = {
                        **{slot: primary_name for slot in self.PRIMARY_SLOTS},
                        **{slot: secondary_name for slot in self.SECONDARY_ARMOR_SLOTS},
                        "Necklace": secondary_name,
                        "Ring1": mythic_name,
                        f"{active_bar}.weapon": secondary_name,
                    }

                    result.append(
                        ExtremeCompleteOptimizationService._direct_candidate(
                            build,
                            character_id=character_id,
                            baseline_build_id=baseline_build_id,
                            token=(
                                f"actual-heal-5plus5plus1:{primary_name}:"
                                f"{secondary_name}:{mythic_name}:{active_bar}"
                            ),
                            path="Gear.FivePiecePlusFivePiecePlusRingMythic",
                            before=before,
                            after=after,
                            source="extreme:actual-heal:gear-package:5+5+1:ring-mythic",
                        )
                    )
        return tuple(result)
