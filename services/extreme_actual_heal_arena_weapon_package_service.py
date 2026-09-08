from __future__ import annotations

from pathlib import Path
import sqlite3

from minmax.build_candidate import BuildCandidate
from minmax.eso_weapon_type_id import eso_weapon_type_id_from_saved_name
from models.build_model import PlayerBuild
from services.extreme_complete_optimization_service import ExtremeCompleteOptimizationService


class ExtremeActualHealArenaWeaponPackageService:
    """Materialize structurally proven arena-weapon candidates.

    Arena-style weapon sets are identified conservatively from canonical imported
    structure rather than names: the set must have ``max_equip_count == 2`` and
    every recorded piece must be a weapon piece.

    For an active two-slot weapon with an empty off-hand, the saved-build subtype
    must resolve to an exact ESO ``WEAPONTYPE_*`` id and the set must contain that
    exact two-hand-family row.

    For an explicit main-hand + off-hand configuration, both saved-build weapon
    subtypes must resolve exactly and the same weapon-only two-piece set must
    contain both subtype rows. This allows paired arena sets such as dual wield or
    one-hand-and-shield to be proven without collapsing them into an aggregate
    skill-line label.
    """

    TWO_HAND_EQUIP_TYPE = 11

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def _arena_set_piece_rows(self) -> tuple[tuple[str, tuple[tuple[int, int, int], ...]], ...]:
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

            result: list[tuple[str, tuple[tuple[int, int, int], ...]]] = []
            for set_id, name in set_rows:
                raw_rows = db.execute(
                    """
                    SELECT equip_type, COALESCE(armor_type, 0), COALESCE(weapon_type, 0)
                    FROM gear_set_piece
                    WHERE set_id = ?
                    ORDER BY equip_type, armor_type, weapon_type
                    """,
                    (int(set_id),),
                ).fetchall()
                if not raw_rows:
                    continue

                rows = tuple(
                    (int(equip_type or 0), int(armor_type or 0), int(weapon_type or 0))
                    for equip_type, armor_type, weapon_type in raw_rows
                )

                # Arena-weapon proof: this set's canonical piece universe is
                # weapon-only. Any armor/jewelry/non-weapon row rejects it.
                if any(armor_type > 0 or weapon_type <= 0 for _equip_type, armor_type, weapon_type in rows):
                    continue

                clean_name = str(name or "").strip()
                if clean_name:
                    result.append((clean_name, rows))

        return tuple(result)

    def _matching_sets(self, eso_weapon_type: int) -> tuple[str, ...]:
        result: list[str] = []
        for name, rows in self._arena_set_piece_rows():
            if any(
                equip_type == self.TWO_HAND_EQUIP_TYPE
                and weapon_type == int(eso_weapon_type)
                for equip_type, _armor_type, weapon_type in rows
            ):
                result.append(name)
        return tuple(dict.fromkeys(result))

    def _matching_paired_sets(
        self,
        main_weapon_type: int,
        offhand_weapon_type: int,
    ) -> tuple[str, ...]:
        required = {int(main_weapon_type), int(offhand_weapon_type)}
        result: list[str] = []
        for name, rows in self._arena_set_piece_rows():
            available = {weapon_type for _equip_type, _armor_type, weapon_type in rows}
            if required.issubset(available):
                result.append(name)
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
        main_eso_weapon_type = eso_weapon_type_id_from_saved_name(main.WeaponType)
        if main_eso_weapon_type is None:
            return ()

        paired = not offhand.is_empty
        if paired:
            offhand_eso_weapon_type = eso_weapon_type_id_from_saved_name(offhand.WeaponType)
            if offhand_eso_weapon_type is None:
                return ()
            names = self._matching_paired_sets(
                main_eso_weapon_type,
                offhand_eso_weapon_type,
            )
        else:
            names = self._matching_sets(main_eso_weapon_type)

        result: list[BuildCandidate] = []
        for set_name in names:
            if paired:
                already_equipped = (
                    str(main.Set or "").strip().casefold() == set_name.casefold()
                    and str(offhand.Set or "").strip().casefold() == set_name.casefold()
                )
            else:
                already_equipped = (
                    str(main.Set or "").strip().casefold() == set_name.casefold()
                    and not str(main.Set2 or "").strip()
                )
            if already_equipped:
                continue

            build = PlayerBuild.from_dict(baseline_build.to_dict())
            candidate_main, candidate_offhand = build.active_weapon_slots(active_bar)
            before = {
                "main_set": str(candidate_main.Set or ""),
                "main_set2": str(candidate_main.Set2 or ""),
                "main_weapon_type": str(candidate_main.WeaponType or ""),
                "offhand_set": str(candidate_offhand.Set or ""),
                "offhand_set2": str(candidate_offhand.Set2 or ""),
                "offhand_weapon_type": str(candidate_offhand.WeaponType or ""),
            }
            candidate_main.Set = set_name
            candidate_main.Set2 = ""
            if paired:
                candidate_offhand.Set = set_name
            else:
                candidate_offhand.Set = ""
            candidate_offhand.Set2 = ""
            after = {
                "main_set": set_name,
                "main_set2": "",
                "main_weapon_type": str(candidate_main.WeaponType or ""),
                "offhand_set": set_name if paired else "",
                "offhand_set2": "",
                "offhand_weapon_type": str(candidate_offhand.WeaponType or ""),
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
