from __future__ import annotations

from pathlib import Path
import sqlite3

from minmax.build_candidate import BuildCandidate
from minmax.character_build.gear_piece import GearPieceCategory
from minmax.gear_set_category_resolver import GearSetCategoryResolver
from minmax.gear_set_repository import GearSetRepository
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveService


class ExtremeActualHealDoubleFivePackageService:
    """Materialize reviewed 5+5 packages on body and jewelry slots.

    This tranche intentionally avoids weapon-slot assumptions. One ordinary set
    occupies the five non-head/non-shoulder body slots; the other occupies Head,
    Shoulders, Necklace, Ring1, and Ring2. Canonical ``gear_set_piece`` structure
    must prove both shapes before a package is emitted.

    Jewelry legality is inferred structurally rather than from hard-coded ESO
    equip-type integers: two distinct non-armor/non-weapon equip types are
    required, representing the necklace and ring families present in imported
    set-piece data. This keeps the builder aligned with the canonical import
    rather than copying external numeric constants into optimization code.
    """

    HEAD_EQUIP_TYPE = GearSetCategoryResolver.HEAD_EQUIP_TYPE
    SHOULDERS_EQUIP_TYPE = GearSetCategoryResolver.SHOULDERS_EQUIP_TYPE
    BODY_FIVE_SLOTS = ("Chest", "Legs", "Hands", "Waist", "Feet")
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

    def _body_five_legal(self, set_id: int, raw_category: str | None) -> bool:
        if not self._ordinary(set_id, raw_category):
            return False
        armor_equip_types = {
            equip_type
            for equip_type, armor_type, weapon_type in self._piece_rows(set_id)
            if armor_type > 0 and weapon_type == 0
        }
        non_head_shoulders = armor_equip_types - {
            self.HEAD_EQUIP_TYPE,
            self.SHOULDERS_EQUIP_TYPE,
        }
        return len(non_head_shoulders) >= len(self.BODY_FIVE_SLOTS)

    def _head_shoulders_jewelry_legal(
        self,
        set_id: int,
        raw_category: str | None,
    ) -> bool:
        if not self._ordinary(set_id, raw_category):
            return False
        rows = self._piece_rows(set_id)
        armor_equip_types = {
            equip_type
            for equip_type, armor_type, weapon_type in rows
            if armor_type > 0 and weapon_type == 0
        }
        jewelry_like_equip_types = {
            equip_type
            for equip_type, armor_type, weapon_type in rows
            if armor_type == 0 and weapon_type == 0
        }
        return (
            {self.HEAD_EQUIP_TYPE, self.SHOULDERS_EQUIP_TYPE}.issubset(armor_equip_types)
            and len(jewelry_like_equip_types) >= 2
        )

    def _reviewed_names(
        self,
        *,
        secondary_shape: bool,
        per_objective: int,
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
                useful = ExtremeGearSetObjectiveService._maximum_useful_piece_count(
                    self.repository,
                    gear_set,
                )
                if useful < 5:
                    continue
                legal = (
                    self._head_shoulders_jewelry_legal(
                        gear_set.id,
                        gear_set.category,
                    )
                    if secondary_shape
                    else self._body_five_legal(
                        gear_set.id,
                        gear_set.category,
                    )
                )
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
        primary_per_objective: int = 8,
        secondary_per_objective: int = 8,
    ) -> tuple[BuildCandidate, ...]:
        primary_names = self._reviewed_names(
            secondary_shape=False,
            per_objective=primary_per_objective,
        )
        secondary_names = self._reviewed_names(
            secondary_shape=True,
            per_objective=secondary_per_objective,
        )

        result: list[BuildCandidate] = []
        for primary_name in primary_names:
            for secondary_name in secondary_names:
                if primary_name.casefold() == secondary_name.casefold():
                    continue

                build = PlayerBuild.from_dict(baseline_build.to_dict())
                before = {
                    **{
                        slot: str(build.Armor[slot].get("Set", "") or "")
                        for slot in (*self.BODY_FIVE_SLOTS, *self.SECONDARY_ARMOR_SLOTS)
                    },
                    "Necklace": str(build.Necklace.Set or ""),
                    "Ring1": str(build.Ring1.Set or ""),
                    "Ring2": str(build.Ring2.Set or ""),
                }

                for slot in self.BODY_FIVE_SLOTS:
                    build.Armor[slot]["Set"] = primary_name
                for slot in self.SECONDARY_ARMOR_SLOTS:
                    build.Armor[slot]["Set"] = secondary_name
                build.Necklace.Set = secondary_name
                build.Ring1.Set = secondary_name
                build.Ring2.Set = secondary_name

                after = {
                    **{slot: primary_name for slot in self.BODY_FIVE_SLOTS},
                    **{slot: secondary_name for slot in self.SECONDARY_ARMOR_SLOTS},
                    "Necklace": secondary_name,
                    "Ring1": secondary_name,
                    "Ring2": secondary_name,
                }

                result.append(
                    ExtremeCompleteOptimizationService._direct_candidate(
                        build,
                        character_id=character_id,
                        baseline_build_id=baseline_build_id,
                        token=f"actual-heal-5plus5:{primary_name}:{secondary_name}",
                        path="Gear.FivePiecePlusFivePiece",
                        before=before,
                        after=after,
                        source="extreme:actual-heal:gear-package:5+5",
                    )
                )
        return tuple(result)
