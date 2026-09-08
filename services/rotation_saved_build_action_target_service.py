from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3

from engine.config import get_data_dir
from minmax.rotation_action_target_legality import (
    RotationActionTargetRequirement,
    RotationTargetKind,
)
from minmax.rotation_plan import RotationActionKind
from models.build_model import PlayerBuild


DEFAULT_DATABASE = get_data_dir() / "eso.db"

_UNAMBIGUOUS_TARGETS = {
    "enemy": RotationTargetKind.ENEMY,
    "self": RotationTargetKind.SELF,
    "ground": RotationTargetKind.GROUND,
}
_TOPOLOGY_ONLY_TARGETS = frozenset({"area", "cone"})


@dataclass(frozen=True)
class RotationSavedBuildActionTargetEvidence:
    """Conservative target-identity evidence for one saved build's slotted actions."""

    target_requirements: tuple[RotationActionTargetRequirement, ...] = ()
    unresolved: tuple[str, ...] = ()
    unresolved_action_names: tuple[str, ...] = ()


class RotationSavedBuildActionTargetService:
    """Resolve only unambiguous canonical target identities from saved skill slots.

    The current canonical ESO corpus stores textual ``skill.target`` values. Enemy,
    Self, and Ground are promoted because they directly identify the action target.
    Area and Cone are target topology/shape rather than target identity, so they stay
    unresolved. Blank or unfamiliar values also stay unresolved. No tooltip-text
    inference and no numeric target enum mapping are used here.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE) -> None:
        self.database_path = Path(database_path)

    def resolve(self, player_build: PlayerBuild) -> RotationSavedBuildActionTargetEvidence:
        slots = self._saved_slots(player_build)
        if not slots:
            return RotationSavedBuildActionTargetEvidence()

        slot_names = self._unique_names(slots)
        if not self.database_path.exists():
            return RotationSavedBuildActionTargetEvidence(
                unresolved=(f"canonical skill target database not found: {self.database_path}",),
                unresolved_action_names=slot_names,
            )

        requirements: dict[
            tuple[RotationActionKind, str], RotationActionTargetRequirement
        ] = {}
        unresolved: list[str] = []
        unresolved_action_names: list[str] = []

        with sqlite3.connect(self.database_path) as db:
            db.row_factory = sqlite3.Row
            skill_columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(skill)").fetchall()
            }
            rank_columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(skill_rank)").fetchall()
            }
            required_skill = {"id", "name", "target"}
            required_rank = {"skill_id", "ability_id", "rank", "raw_name"}
            missing = (required_skill - skill_columns) | (required_rank - rank_columns)
            if missing:
                return RotationSavedBuildActionTargetEvidence(
                    unresolved=(
                        "canonical skill target schema is missing: "
                        + ", ".join(sorted(missing)),
                    ),
                    unresolved_action_names=slot_names,
                )

            for action_name, action_kind in slots:
                rows = self._target_rows(db, action_name)
                if not rows:
                    unresolved.append(
                        f"canonical skill target not found by exact saved name: {action_name}"
                    )
                    unresolved_action_names.append(action_name)
                    continue

                highest_rank = max(int(row["rank"] or 0) for row in rows)
                top_rows = tuple(
                    row for row in rows if int(row["rank"] or 0) == highest_rank
                )
                values = {
                    str(row["target"] or "").strip().casefold()
                    for row in top_rows
                }
                if len(values) != 1:
                    unresolved.append(
                        "canonical skill target is ambiguous at highest rank for exact saved name: "
                        f"{action_name}"
                    )
                    unresolved_action_names.append(action_name)
                    continue

                target_value = next(iter(values))
                target_kind = _UNAMBIGUOUS_TARGETS.get(target_value)
                if target_kind is not None:
                    key = (action_kind, action_name.casefold())
                    requirements[key] = RotationActionTargetRequirement(
                        action_name=action_name,
                        action_kind=action_kind,
                        allowed_targets=(target_kind,),
                    )
                    continue

                if target_value in _TOPOLOGY_ONLY_TARGETS:
                    unresolved.append(
                        "canonical skill target describes topology rather than target identity for "
                        f"{action_name}: {target_value.title()}"
                    )
                elif not target_value:
                    unresolved.append(
                        f"canonical skill target identity is blank for {action_name}"
                    )
                else:
                    unresolved.append(
                        "canonical skill target identity is unsupported for "
                        f"{action_name}: {target_value}"
                    )
                unresolved_action_names.append(action_name)

        return RotationSavedBuildActionTargetEvidence(
            target_requirements=tuple(requirements.values()),
            unresolved=tuple(dict.fromkeys(unresolved)),
            unresolved_action_names=self._unique_strings(unresolved_action_names),
        )

    @staticmethod
    def _saved_slots(player_build: PlayerBuild) -> tuple[tuple[str, RotationActionKind], ...]:
        front = tuple(getattr(player_build, "FrontBarSkills", ()) or ())
        back = tuple(getattr(player_build, "BackBarSkills", ()) or ())
        values: list[tuple[str, RotationActionKind]] = []
        for names in (front, back):
            for index, raw_name in enumerate(names):
                name = str(raw_name or "").strip()
                if not name:
                    continue
                kind = RotationActionKind.ULTIMATE if index == 5 else RotationActionKind.SKILL
                values.append((name, kind))
        return tuple(values)

    @classmethod
    def _unique_names(
        cls,
        slots: tuple[tuple[str, RotationActionKind], ...],
    ) -> tuple[str, ...]:
        return cls._unique_strings(name for name, _kind in slots)

    @staticmethod
    def _unique_strings(values) -> tuple[str, ...]:
        ordered: list[str] = []
        seen: set[str] = set()
        for raw in values:
            value = str(raw or "").strip()
            key = value.casefold()
            if not value or key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)

    @staticmethod
    def _target_rows(db: sqlite3.Connection, action_name: str) -> tuple[sqlite3.Row, ...]:
        return tuple(
            db.execute(
                """
                SELECT
                    sr.rank,
                    s.target
                FROM skill_rank sr
                JOIN skill s ON s.id = sr.skill_id
                LEFT JOIN ability a ON a.ability_id = sr.ability_id
                WHERE LOWER(TRIM(COALESCE(NULLIF(sr.raw_name, ''), NULLIF(a.name, ''), s.name)))
                    = LOWER(TRIM(?))
                ORDER BY COALESCE(sr.rank, 0) DESC, sr.ability_id DESC
                """,
                (action_name,),
            ).fetchall()
        )


__all__ = [
    "RotationSavedBuildActionTargetEvidence",
    "RotationSavedBuildActionTargetService",
]
