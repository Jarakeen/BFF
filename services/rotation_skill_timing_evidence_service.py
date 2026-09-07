from __future__ import annotations

from dataclasses import dataclass
import math
import sqlite3
from pathlib import Path

from minmax.rotation_plan import RotationActionKind
from minmax.skill_coefficient_repository import SkillCoefficientRepository, ability_entity_id
from services.rotation_action_occupancy_legality_service import RotationActionOccupancyRule


@dataclass(frozen=True)
class RotationSkillTimingEvidence:
    """Canonical cast/channel timing for one exact resolved player skill rank."""

    skill_id: str
    ability_id: int
    name: str
    cast_time_seconds: float | None
    channel_time_seconds: float | None
    is_channeled: bool
    source: str

    @property
    def occupancy_seconds(self) -> float | None:
        """Return only timing directly supported by the canonical ability row.

        Channeled abilities use channel_time. Non-channeled cast-time abilities use
        cast_time. Instant abilities deliberately return None: zero cast time is not
        evidence for global-cooldown occupancy.
        """

        if self.is_channeled:
            value = self.channel_time_seconds
        else:
            value = self.cast_time_seconds
        if value is None or value <= 0.0:
            return None
        return float(value)


@dataclass(frozen=True)
class RotationSkillTimingResolution:
    evidence: RotationSkillTimingEvidence | None
    unresolved: tuple[str, ...] = ()


class RotationSkillTimingEvidenceService:
    """Resolve imported ESO cast/channel timing without inventing GCD semantics.

    The canonical `ability` table stores raw GetAbilityCastInfo-style cast/channel
    values imported from the ESO skill corpus. Those source values are milliseconds;
    this service converts them to seconds for the RotationPlan time domain.

    This layer resolves timing only. The caller must still state which action kinds
    a cast/channel occupancy window blocks. That separation keeps weave, interrupt,
    and bar-swap policy out of source-data interpretation.
    """

    _MILLISECONDS_PER_SECOND = 1000.0

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.skill_repository = SkillCoefficientRepository(self.database_path)

    def resolve_skill(self, skill_id: str) -> RotationSkillTimingResolution:
        requested = ability_entity_id(skill_id)
        if not requested:
            return RotationSkillTimingResolution(None, ("rotation skill timing requires skill_id",))
        if not self.database_path.exists():
            return RotationSkillTimingResolution(
                None,
                (f"rotation skill timing database is unavailable: {self.database_path}",),
            )

        rank_resolution = self.skill_repository.resolve_entity_id(requested)
        rank = rank_resolution.rank
        if rank is None:
            return RotationSkillTimingResolution(
                None,
                rank_resolution.unresolved or (f"canonical skill timing identity unresolved: {requested}",),
            )

        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            if not self._table_exists(connection, "ability"):
                return RotationSkillTimingResolution(None, ("ability table is unavailable",))
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(ability)").fetchall()
            }
            required = {"ability_id", "name", "cast_time", "channel_time", "is_channeled"}
            missing = sorted(required - columns)
            if missing:
                return RotationSkillTimingResolution(
                    None,
                    ("ability timing columns are unavailable: " + ", ".join(missing),),
                )
            row = connection.execute(
                """
                SELECT ability_id, name, cast_time, channel_time, is_channeled
                FROM ability
                WHERE ability_id = ?
                """,
                (int(rank.ability_id),),
            ).fetchone()

        if row is None:
            return RotationSkillTimingResolution(
                None,
                (f"canonical ability timing row not found for ability ID {rank.ability_id}",),
            )

        cast = self._source_milliseconds_to_seconds(row["cast_time"], label="cast_time")
        channel = self._source_milliseconds_to_seconds(row["channel_time"], label="channel_time")
        unresolved = tuple(message for _value, message in (cast, channel) if message)
        if unresolved:
            return RotationSkillTimingResolution(None, unresolved)

        evidence = RotationSkillTimingEvidence(
            skill_id=rank.entity_id,
            ability_id=int(rank.ability_id),
            name=str(row["name"] or rank.name or "").strip() or rank.name,
            cast_time_seconds=cast[0],
            channel_time_seconds=channel[0],
            is_channeled=bool(row["is_channeled"]),
            source=f"canonical ability table ability_id={int(rank.ability_id)}",
        )
        return RotationSkillTimingResolution(evidence=evidence)

    def occupancy_rule(
        self,
        *,
        skill_id: str,
        blocked_action_kinds: tuple[RotationActionKind, ...],
    ) -> tuple[RotationActionOccupancyRule | None, tuple[str, ...]]:
        """Bridge proven timing to the existing occupancy contract.

        Instant skills return no rule and no error. Blocking semantics remain an
        explicit caller policy rather than being inferred from cast/channel data.
        """

        resolution = self.resolve_skill(skill_id)
        if resolution.evidence is None:
            return None, resolution.unresolved
        occupancy = resolution.evidence.occupancy_seconds
        if occupancy is None:
            return None, ()
        return (
            RotationActionOccupancyRule(
                action_kind=RotationActionKind.SKILL,
                action_name=resolution.evidence.name,
                occupancy_seconds=occupancy,
                blocked_action_kinds=tuple(blocked_action_kinds),
                source=resolution.evidence.source,
            ),
            (),
        )

    @classmethod
    def _source_milliseconds_to_seconds(
        cls,
        value: object,
        *,
        label: str,
    ) -> tuple[float | None, str | None]:
        if value is None:
            return None, None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None, f"canonical {label} is not numeric: {value!r}"
        if not math.isfinite(number) or number < 0.0:
            return None, f"canonical {label} is invalid: {value!r}"
        return number / cls._MILLISECONDS_PER_SECOND, None

    @staticmethod
    def _table_exists(connection: sqlite3.Connection, name: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (name,),
        ).fetchone() is not None


__all__ = [
    "RotationSkillTimingEvidence",
    "RotationSkillTimingEvidenceService",
    "RotationSkillTimingResolution",
]
