from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from minmax.character_build.character_class import CharacterClass
from minmax.character_build.class_configuration import ClassSkillLineConfiguration
from minmax.character_progression import CharacterProgression
from minmax.skill_coefficient_repository import ability_entity_id
from models.build_model import PlayerBuild
from services.extreme_heal_class_route_service import canonical_class_skill_line_id


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

    Discovery is evidence-driven: a skill enters the catalog only when at least
    one coefficient is explicitly classified as ``heal``. For ordinary saved-
    build discovery, class abilities remain limited to the build's native class.
    When an explicit ``ClassSkillLineConfiguration`` is supplied, class-skill
    legality instead follows the three equipped class lines. That is the correct
    boundary for subclass routes: base class and available class skill lines are
    related, but they are not the same thing.

    Non-class abilities still require a skill line the progression says the
    character owns. Unknown ownership remains a blocker rather than becoming an
    assumed legal skill.
    """

    REQUIRED_TABLES = (
        "ability",
        "skill",
        "skill_rank",
        "skill_component_classification",
    )

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    def candidates_for_build(
        self,
        build: PlayerBuild,
        progression: CharacterProgression,
        *,
        include_blocked: bool = False,
        class_configuration: ClassSkillLineConfiguration | None = None,
    ) -> tuple[ExtremeHealSkillCandidate, ...]:
        if not self.database_path.exists():
            raise FileNotFoundError(self.database_path)

        rows = self._heal_rows()
        grouped: dict[tuple[int, int], list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault((int(row["skill_id"]), int(row["morph"])), []).append(row)

        result: list[ExtremeHealSkillCandidate] = []
        for _identity, identity_rows in grouped.items():
            # Query order is descending rank/ability ID. Keep every HEAL row for
            # that one selected concrete max-rank record, and do not let older
            # rank metadata leak into the candidate.
            row = identity_rows[0]
            selected_rank_id = int(row["skill_rank_id"])
            selected_rows = tuple(
                item for item in identity_rows
                if int(item["skill_rank_id"]) == selected_rank_id
            )

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
            )
            can_crit_values = {
                None if item["can_crit"] is None else bool(int(item["can_crit"]))
                for item in selected_rows
            }
            can_crit: bool | None
            if can_crit_values == {True}:
                can_crit = True
            elif can_crit_values == {False}:
                can_crit = False
            else:
                # Mixed or unknown per-component eligibility must remain
                # component-scoped. The aggregate candidate cannot collapse it
                # to a misleading yes/no answer.
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
                heal_component_count=len({int(item["coefficient_number"]) for item in selected_rows}),
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

    def _heal_rows(self) -> tuple[sqlite3.Row, ...]:
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
                    COALESCE(a.is_passive, s.is_passive, 0) AS is_passive,
                    c.coefficient_number,
                    c.can_crit
                FROM skill_component_classification c
                JOIN skill_rank sr ON sr.id = c.skill_rank_id
                JOIN skill s ON s.id = sr.skill_id
                LEFT JOIN ability a ON a.ability_id = sr.ability_id
                WHERE LOWER(TRIM(c.effect_kind)) = 'heal'
                ORDER BY sr.skill_id, COALESCE(sr.morph, 0), COALESCE(sr.rank, 0) DESC,
                         sr.ability_id DESC, c.coefficient_number
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

        return tuple(blockers)
