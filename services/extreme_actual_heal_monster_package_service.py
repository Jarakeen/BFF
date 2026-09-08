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


class ExtremeActualHealMonsterPackageService:
    """Materialize reviewed 5-piece + 2-piece monster packages on legal body slots.

    The package shape is intentionally narrow and provable:

    * the ordinary set must have at least five distinct non-head/non-shoulder
      armor equip types in canonical ``gear_set_piece`` data;
    * the monster set must resolve structurally as a monster set and expose both
      Head and Shoulders;
    * the package is written onto seven actual body slots before the canonical
      build context scores the resulting healing event.

    Mythics, arena weapons, jewelry/weapon five-piece placement, and 5+5 package
    composition remain separate slot-family problems rather than being guessed
    into this service.
    """

    HEAD_EQUIP_TYPE = GearSetCategoryResolver.HEAD_EQUIP_TYPE
    SHOULDERS_EQUIP_TYPE = GearSetCategoryResolver.SHOULDERS_EQUIP_TYPE
    FIVE_PIECE_BODY_SLOTS = ("Chest", "Legs", "Hands", "Waist", "Feet")
    MONSTER_BODY_SLOTS = ("Head", "Shoulders")
    OBJECTIVES = (
        "healing_done",
        "critical_healing",
        "spell_damage",
        "weapon_damage",
        "max_health",
        "max_magicka",
        "max_stamina",
    )

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.repository = GearSetRepository(self.database_path)
        self.categories = GearSetCategoryResolver(self.database_path)

    def _armor_equip_types(self, set_id: int) -> frozenset[int]:
        with sqlite3.connect(self.database_path) as db:
            tables = {
                str(row[0])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "gear_set_piece" not in tables:
                return frozenset()
            rows = db.execute(
                """
                SELECT DISTINCT equip_type
                FROM gear_set_piece
                WHERE set_id = ?
                  AND equip_type IS NOT NULL
                  AND COALESCE(armor_type, 0) > 0
                  AND COALESCE(weapon_type, 0) = 0
                """,
                (int(set_id),),
            ).fetchall()
        return frozenset(int(row[0]) for row in rows)

    def _ordinary_body_legal(self, set_id: int, raw_category: str | None) -> bool:
        if self.categories.resolve(set_id, raw_category=raw_category) is not GearPieceCategory.SET_PIECE:
            return False
        equip_types = self._armor_equip_types(set_id)
        non_monster = equip_types - {self.HEAD_EQUIP_TYPE, self.SHOULDERS_EQUIP_TYPE}
        return len(non_monster) >= len(self.FIVE_PIECE_BODY_SLOTS)

    def _monster_body_legal(self, set_id: int, raw_category: str | None) -> bool:
        if self.categories.resolve(set_id, raw_category=raw_category) is not GearPieceCategory.MONSTER_SET:
            return False
        equip_types = self._armor_equip_types(set_id)
        return {self.HEAD_EQUIP_TYPE, self.SHOULDERS_EQUIP_TYPE}.issubset(equip_types)

    def _reviewed_names(
        self,
        *,
        monster: bool,
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
                if monster:
                    legal = useful >= 2 and self._monster_body_legal(
                        gear_set.id,
                        gear_set.category,
                    )
                else:
                    legal = useful >= 5 and self._ordinary_body_legal(
                        gear_set.id,
                        gear_set.category,
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
        ordinary_per_objective: int = 8,
        monster_per_objective: int = 6,
    ) -> tuple[BuildCandidate, ...]:
        ordinary_names = self._reviewed_names(
            monster=False,
            per_objective=ordinary_per_objective,
        )
        monster_names = self._reviewed_names(
            monster=True,
            per_objective=monster_per_objective,
        )
        result: list[BuildCandidate] = []
        for ordinary_name in ordinary_names:
            for monster_name in monster_names:
                build = PlayerBuild.from_dict(baseline_build.to_dict())
                before = {
                    slot: str(build.Armor[slot].get("Set", "") or "")
                    for slot in (*self.FIVE_PIECE_BODY_SLOTS, *self.MONSTER_BODY_SLOTS)
                }
                for slot in self.FIVE_PIECE_BODY_SLOTS:
                    build.Armor[slot]["Set"] = ordinary_name
                for slot in self.MONSTER_BODY_SLOTS:
                    build.Armor[slot]["Set"] = monster_name

                result.append(
                    ExtremeCompleteOptimizationService._direct_candidate(
                        build,
                        character_id=character_id,
                        baseline_build_id=baseline_build_id,
                        token=f"actual-heal-5plus2:{ordinary_name}:{monster_name}",
                        path="Armor.FivePiecePlusMonster",
                        before=before,
                        after={
                            **{slot: ordinary_name for slot in self.FIVE_PIECE_BODY_SLOTS},
                            **{slot: monster_name for slot in self.MONSTER_BODY_SLOTS},
                        },
                        source="extreme:actual-heal:gear-package:5+2",
                    )
                )
        return tuple(result)
