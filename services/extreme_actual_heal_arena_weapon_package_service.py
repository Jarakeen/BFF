from __future__ import annotations

from pathlib import Path
import sqlite3

from minmax.build_candidate import BuildCandidate
from minmax.eso_weapon_type_id import eso_weapon_type_id_from_saved_name
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService


class ExtremeActualHealArenaWeaponPackageService:
    """Materialize structurally proven two-slot arena-weapon candidates.

    Arena-style weapon sets are identified conservatively from canonical imported
    structure rather than names: the set must have ``max_equip_count == 2`` and
    every recorded piece must be a weapon piece. The active saved-build weapon
    subtype is resolved to its raw ESO ``WEAPONTYPE_*`` id, and only sets that
    contain that exact subtype are admitted.

    This first tranche intentionally covers only an active two-slot weapon with
    an empty off-hand. Dual-wield and one-hand-and-shield arena packages need a
    paired-main/off-hand legality pass rather than being guessed from one slot.
    """

    TWO_HAND_EQUIP_TYPE = 11

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def _matching_sets(self, eso_weapon_type: int) -> tuple[str, ...]:
        with sqlite3.connect(self.database_path) as db:
            tables = {
                str(row[0])
                for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if not {"gear_set", "gear_set_piece"}.issubset(tables):
                return ()

            set_rows = db.execute(
                """
                SELECT id, name
                FROM gear_set
                WHERE max_equip_count = 2
                ORDER BY name COLLATE NOCASE, id
                """
            ).fetchall()

            result: list[str] = []
            for set_id, name in set_rows:
                pieces = db.execute(
                    """
                    SELECT equip_type, COALESCE(armor_type, 0), COALESCE(weapon_type, 0)
                    FROM gear_set_piece
                    WHERE set_id = ?
                    ORDER BY equip_type, armor_type, weapon_type
                    """,
                    (int(set_id),),
                ).fetchall()
                if not pieces:
                    continue

                # Arena-weapon proof: this set's canonical piece universe is
                # weapon-only. Any armor/jewelry/non-weapon row rejects it.
                if any(int(armor_type or 0) > 0 or int(weapon_type or 0) <= 0 for _equip_type, armor_type, weapon_type in pieces):
                    continue

                if not any(
                    int(equip_type or 0) == self.TWO_HAND_EQUIP_TYPE
                    and int(weapon_type or 0) == int(eso_weapon_type)
                    for equip_type, _armor_type, weapon_type in pieces
                ):
                    continue

                clean_name = str(name or "").strip()
                if clean_name:
                    result.append(clean_name)

        return tuple(dict.fromkeys(result))

    def build_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        character_id: str,
        baseline_build_id: str,
        active_bar: str = "front",
    ) -> tuple[BuildCandidate, ...]:
        main, offhand = baseline_build.active_weapon_slots(active_bar)
        if not offhand.is_empty:
            return ()

        eso_weapon_type = eso_weapon_type_id_from_saved_name(main.WeaponType)
        if eso_weapon_type is None:
            return ()

        names = self._matching_sets(eso_weapon_type)
        result: list[BuildCandidate] = []
        for set_name in names:
            if str(main.Set or "").strip().casefold() == set_name.casefold() and not str(main.Set2 or "").strip():
                continue

            build = PlayerBuild.from_dict(baseline_build.to_dict())
            candidate_main, candidate_offhand = build.active_weapon_slots(active_bar)
            before = {
                "set": str(candidate_main.Set or ""),
                "set2": str(candidate_main.Set2 or ""),
                "weapon_type": str(candidate_main.WeaponType or ""),
            }
            candidate_main.Set = set_name
            candidate_main.Set2 = ""
            candidate_offhand.Set = ""
            candidate_offhand.Set2 = ""
            after = {
                "set": set_name,
                "set2": "",
                "weapon_type": str(candidate_main.WeaponType or ""),
            }
            result.append(
                ExtremeCompleteOptimizationService._direct_candidate(
                    build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                    token=f"actual-heal-arena-weapon:{active_bar}:{set_name}",
                    path="Gear.ArenaWeapon",
                    before=before,
                    after=after,
                    source="extreme:actual-heal:gear-package:arena-weapon",
                )
            )
        return tuple(result)
