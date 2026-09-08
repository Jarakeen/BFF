from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_build.weapon_type import WeaponType, resolve_weapon_skill_line
from minmax.character_progression import CharacterProgression
from minmax.eso_weapon_type_id import weapon_type_from_saved_name
from minmax.skill_coefficient_repository import ability_entity_id
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_component_repository import SkillComponentRepository
from models.build_model import PlayerBuild
from services.extreme_dragon_blood_skill_component_repository import (
    ExtremeDragonBloodSkillComponentRepository,
)
from services.extreme_heal_class_route_service import canonical_class_skill_line_id
from services.extreme_sorcerer_skill_component_repository import (
    ExtremeSorcererSkillComponentRepository,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


@dataclass(frozen=True)
class ExtremeHealSkillCandidate:
    entity_id: str
    name: str
    skill_rank_id: int
    ability_id: int
    rank: int
    morph: int
    skill_line: str
    class_type: str
    heal_component_count: int
    can_crit: bool | None
    legal: bool
    blockers: tuple[str, ...]


class ExtremeHealSkillCandidateService:
    """Discover reviewed active-skill healing candidates from canonical data.

    Skill/rank/ownership metadata comes from canonical ``ability``/``skill`` /
    ``skill_rank`` tables. HEAL evidence comes from the same layered component
    repository used by Extreme canonical healing: persisted classifications when
    present, plus reviewed Dragon Blood, Sorcerer, and U50 healer overlays.

    This keeps candidate discovery aligned with evaluation and does not require a
    binary ``eso.db`` schema migration merely to consume reviewed in-memory
    component identity. Missing core skill metadata still fails closed.
    """

    REQUIRED_TABLES = ("ability", "skill", "skill_rank")
    WEAPON_SKILL_LINE_IDS = frozenset(
        {
            "one_hand_and_shield",
            "dual_wield",
            "two_handed",
            "bow",
            "destruction_staff",
            "restoration_staff",
        }
    )

    def __init__(
        self,
        database_path: str | Path,
        *,
        component_repository=None,
    ) -> None:
        self.database_path = Path(database_path)
        if component_repository is None:
            base = SkillComponentRepository(self.database_path)
            dragon = ExtremeDragonBloodSkillComponentRepository(
                self.database_path,
                base_repository=base,
            )
            sorcerer = ExtremeSorcererSkillComponentRepository(
                self.database_path,
                base_repository=dragon,
            )
            component_repository = RotationHealerU50SkillComponentRepository(
                self.database_path,
                base_repository=sorcerer,
            )
        self.components = component_repository

    def candidates_for_build(
        self,
        build: PlayerBuild,
        progression: CharacterProgression,
        *,
        include_blocked: bool = False,
        class_configuration: ClassSkillLineConfiguration | None = None,
        active_bar: str | None = None,
    ) -> tuple[ExtremeHealSkillCandidate, ...]:
        if not self.database_path.exists():
            raise FileNotFoundError(self.database_path)

        rows = self._skill_rows()
        grouped: dict[tuple[int, int], list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault((int(row["skill_id"]), int(row["morph"])), []).append(row)

        result: list[ExtremeHealSkillCandidate] = []
        for identity_rows in grouped.values():
            row = identity_rows[0]
            selected_rank_id = int(row["skill_rank_id"])
            heal_components = tuple(
                component
                for component in self.components.get_for_skill_rank(selected_rank_id)
                if component.effect_kind is SkillEffectKind.HEAL
            )
            if not heal_components:
                continue

            name = str(row["name"] or "").strip()
            entity_id = ability_entity_id(name)
            skill_line = str(row["skill_line"] or "").strip()
            class_type = str(row["class_type"] or "").strip()
            blockers = self._legality_blockers(
                build=build,
                progression=progression,
                name=name,
                skill_line=skill_line,
                class_type=class_type,
                is_player=bool(int(row["is_player"] or 0)),
                is_passive=bool(int(row["is_passive"] or 0)),
                class_configuration=class_configuration,
                active_bar=active_bar,
            )
            crit_values = {component.can_crit for component in heal_components}
            if crit_values == {True}:
                can_crit: bool | None = True
            elif crit_values == {False}:
                can_crit = False
            else:
                can_crit = None

            candidate = ExtremeHealSkillCandidate(
                entity_id=entity_id,
                name=name,
                skill_rank_id=selected_rank_id,
                ability_id=int(row["ability_id"]),
                rank=int(row["rank"] or 0),
                morph=int(row["morph"] or 0),
                skill_line=skill_line,
                class_type=class_type,
                heal_component_count=len(
                    {int(component.coefficient_number) for component in heal_components}
                ),
                can_crit=can_crit,
                legal=not blockers,
                blockers=blockers,
            )
            if candidate.legal or include_blocked:
                result.append(candidate)

        return tuple(
            sorted(
                result,
                key=lambda item: (
                    not item.legal,
                    item.class_type.casefold(),
                    item.skill_line.casefold(),
                    item.name.casefold(),
                    item.entity_id,
                ),
            )
        )

    def _skill_rows(self) -> tuple[sqlite3.Row, ...]:
        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            missing = [name for name in self.REQUIRED_TABLES if not self._table_exists(db, name)]
            if missing:
                raise ValueError(
                    "Canonical heal candidate discovery requires tables: "
                    + ", ".join(missing)
                )
            rows = db.execute(
                """
                SELECT
                    sr.id AS skill_rank_id,
                    sr.skill_id,
                    sr.ability_id,
                    COALESCE(sr.rank, 0) AS rank,
                    COALESCE(sr.morph, 0) AS morph,
                    COALESCE(NULLIF(a.name, ''), NULLIF(sr.raw_name, ''), s.name, '') AS name,
                    COALESCE(a.skill_line, '') AS skill_line,
                    COALESCE(a.class_type, '') AS class_type,
                    COALESCE(a.is_player, 0) AS is_player,
                    COALESCE(a.is_passive, s.is_passive, 0) AS is_passive
                FROM skill_rank sr
                JOIN skill s ON s.id = sr.skill_id
                LEFT JOIN ability a ON a.ability_id = sr.ability_id
                ORDER BY sr.skill_id, COALESCE(sr.morph, 0), COALESCE(sr.rank, 0) DESC,
                         sr.ability_id DESC
                """
            ).fetchall()
        return tuple(rows)

    @staticmethod
    def _table_exists(db: sqlite3.Connection, name: str) -> bool:
        return db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (name,),
        ).fetchone() is not None

    @staticmethod
    def _character_class(value: object) -> CharacterClass | None:
        key = str(value or "").strip().casefold()
        return next(
            (character_class for character_class in CharacterClass if character_class.value == key),
            None,
        )

    @staticmethod
    def _line_id(value: object) -> str:
        return canonical_class_skill_line_id(value)

    @classmethod
    def _active_weapon_skill_line_id(
        cls,
        build: PlayerBuild,
        active_bar: str,
    ) -> tuple[str | None, str | None]:
        main, offhand = build.active_weapon_slots(active_bar)
        main_raw = str(main.WeaponType or "").strip()
        offhand_raw = str(offhand.WeaponType or "").strip()
        main_type = weapon_type_from_saved_name(main_raw)
        offhand_type = weapon_type_from_saved_name(offhand_raw)

        if main_type is None:
            return None, f"active {active_bar} weapon type is unresolved: {main_raw or '(empty)'}"
        if offhand_raw and offhand_type is None:
            return None, f"active {active_bar} off-hand weapon type is unresolved: {offhand_raw}"
        offhand_type = offhand_type or WeaponType.NONE
        try:
            return resolve_weapon_skill_line(main_type, offhand_type).value, None
        except ValueError as exc:
            return None, str(exc)

    @classmethod
    def _legality_blockers(
        cls,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        name: str,
        skill_line: str,
        class_type: str,
        is_player: bool,
        is_passive: bool,
        class_configuration: ClassSkillLineConfiguration | None = None,
        active_bar: str | None = None,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not name:
            blockers.append("healing ability name is unavailable")
        if not is_player:
            blockers.append(f"{name or 'ability'} is not marked as a player ability")
        if is_passive:
            blockers.append(f"{name or 'ability'} is passive, not an active heal")

        build_class = str(build.EsoClass or "").strip()
        if class_type:
            if class_configuration is None:
                if not build_class:
                    blockers.append(f"{name}: class ownership is unresolved ({class_type})")
                elif class_type.casefold() != build_class.casefold():
                    blockers.append(
                        f"{name}: requires {class_type}; current build class is {build_class}"
                    )
            else:
                character_class = cls._character_class(build_class)
                if character_class is None:
                    blockers.append(
                        f"{name}: subclass base class is unsupported or unresolved: {build_class or '(empty)'}"
                    )
                else:
                    problems = class_configuration.validate(character_class)
                    blockers.extend(
                        f"{name}: invalid class-line configuration: {problem}"
                        for problem in problems
                    )
                    line_id = canonical_class_skill_line_id(skill_line)
                    if not line_id:
                        blockers.append(f"{name}: class skill line is unavailable")
                    elif line_id not in set(
                        class_configuration.effective_skill_lines(character_class)
                    ):
                        blockers.append(
                            f"{name}: class skill line not equipped: {skill_line}"
                        )
        else:
            if not skill_line:
                blockers.append(f"{name}: non-class skill line is unavailable")
            elif not progression.owns_skill_line(skill_line):
                blockers.append(f"{name}: skill line not owned: {skill_line}")

            line_id = cls._line_id(skill_line)
            if active_bar is not None and line_id in cls.WEAPON_SKILL_LINE_IDS:
                equipped_line_id, error = cls._active_weapon_skill_line_id(build, active_bar)
                if error:
                    blockers.append(f"{name}: weapon-skill legality unresolved: {error}")
                elif equipped_line_id != line_id:
                    blockers.append(
                        f"{name}: requires {skill_line} on {active_bar} bar; "
                        f"equipped weapon grants {equipped_line_id or '(none)'}"
                    )

        return tuple(blockers)
