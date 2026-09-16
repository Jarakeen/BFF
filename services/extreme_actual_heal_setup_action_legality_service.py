from __future__ import annotations

"""Legal setup-action witnesses for Extreme H1 gear conditions.

This bridge deliberately reuses :class:`ExtremePlayerSkillCandidateService` for
route/bar legality. It does not decide whether a gear set is valuable and it does
not mutate a build. It answers one narrower question: does the selected legality
context contain a canonical active skill whose reviewed evidence proves a requested
setup capability?

Resolve evidence is reviewed tooltip semantics. Cast/channel evidence is canonical
ability timing. Unknown capabilities fail closed.
"""

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Protocol

from minmax.eso_markup import normalize_eso_markup
from services.extreme_player_skill_candidate_service import (
    ExtremePlayerSkillCandidateService,
    ExtremePlayerSkillLegalityContext,
)
from services.extreme_skill_universe_service import ExtremePlayerSkillRecord
from services.rotation_skill_timing_evidence_service import RotationSkillTimingEvidenceService


GRANTS_RESOLVE = "grants_resolve"
HAS_CAST_OR_CHANNEL_TIME = "has_cast_or_channel_time"


class _CandidateProvider(Protocol):
    def candidates(
        self,
        context: ExtremePlayerSkillLegalityContext,
        *,
        ultimate: bool | None = None,
    ) -> tuple[ExtremePlayerSkillRecord, ...]: ...


class _TimingProvider(Protocol):
    def resolve_skill(self, skill_id: str): ...


@dataclass(frozen=True)
class _SetupTimingEvidence:
    cast_time_seconds: float | None
    channel_time_seconds: float | None
    is_channeled: bool


@dataclass(frozen=True)
class ExtremeActualHealSetupActionWitness:
    capability: str
    skill_name: str | None = None
    skill_line: str | None = None
    ability_id: int | None = None
    evidence: str | None = None
    unresolved: tuple[str, ...] = ()

    @property
    def proven(self) -> bool:
        return bool(self.skill_name and not self.unresolved)


class ExtremeActualHealSetupActionLegalityService:
    """Find deterministic, route-legal setup actions for reviewed H1 capabilities."""

    _RESOLVE_PATTERNS = (
        re.compile(
            r"\b(?:gain|gaining)\s+(?:Major|Minor) Resolve\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bgrant(?:s|ing)?\s+(?:you|yourself)\s+(?:Major|Minor) Resolve\b",
            re.IGNORECASE,
        ),
    )
    _SUPPORTED = frozenset({GRANTS_RESOLVE, HAS_CAST_OR_CHANNEL_TIME})
    _MILLISECONDS_PER_SECOND = 1000.0

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        candidate_service: _CandidateProvider | None = None,
        timing_service: _TimingProvider | None = None,
    ) -> None:
        if database_path is None and candidate_service is None:
            raise ValueError("database_path or candidate_service is required")
        self.candidate_service = candidate_service or ExtremePlayerSkillCandidateService(
            database_path  # type: ignore[arg-type]
        )
        self.timing_service = timing_service or (
            RotationSkillTimingEvidenceService(database_path)
            if database_path is not None
            else None
        )
        self._timing_by_ability_id = self._load_positive_timing_index(database_path)
        self._timing_by_name: dict[str, object | None] = {}

    @classmethod
    def _load_positive_timing_index(
        cls,
        database_path: str | Path | None,
    ) -> dict[int, _SetupTimingEvidence]:
        """Load positive cast/channel timings once for denominator-scale audits.

        H1 route audits revisit the same legal skills across thousands of routes.
        Opening SQLite once per candidate skill is correct but needlessly quadratic
        in database work. The canonical ``ability`` table is small enough to index
        all positive timing rows once, preserving the same source evidence.
        """
        if database_path is None:
            return {}
        path = Path(database_path)
        if not path.exists():
            return {}
        with sqlite3.connect(path) as connection:
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ability'"
            ).fetchone()
            if table is None:
                return {}
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(ability)").fetchall()
            }
            required = {"ability_id", "cast_time", "channel_time", "is_channeled"}
            if not required.issubset(columns):
                return {}
            rows = connection.execute(
                """
                SELECT ability_id, cast_time, channel_time, is_channeled
                FROM ability
                WHERE COALESCE(cast_time, 0) > 0
                   OR (COALESCE(is_channeled, 0) <> 0 AND COALESCE(channel_time, 0) > 0)
                """
            ).fetchall()

        result: dict[int, _SetupTimingEvidence] = {}
        for ability_id, cast_time, channel_time, is_channeled in rows:
            cast = (
                float(cast_time) / cls._MILLISECONDS_PER_SECOND
                if cast_time is not None and float(cast_time) > 0.0
                else None
            )
            channel = (
                float(channel_time) / cls._MILLISECONDS_PER_SECOND
                if channel_time is not None and float(channel_time) > 0.0
                else None
            )
            result[int(ability_id)] = _SetupTimingEvidence(
                cast_time_seconds=cast,
                channel_time_seconds=channel,
                is_channeled=bool(is_channeled),
            )
        return result

    @staticmethod
    def _text(row: ExtremePlayerSkillRecord) -> str:
        normalized = normalize_eso_markup(str(row.description or "")).text
        return " ".join(normalized.split())

    @classmethod
    def _supports_resolve(cls, row: ExtremePlayerSkillRecord) -> bool:
        text = cls._text(row)
        return any(pattern.search(text) for pattern in cls._RESOLVE_PATTERNS)

    def _timing_evidence(self, row: ExtremePlayerSkillRecord):
        for ability_id in (row.max_rank_ability_id, row.base_ability_id, row.skill_id):
            if ability_id is None:
                continue
            indexed = self._timing_by_ability_id.get(int(ability_id))
            if indexed is not None:
                return indexed

        if self.timing_service is None:
            return None
        key = str(row.name or "").strip().casefold()
        if key in self._timing_by_name:
            return self._timing_by_name[key]
        resolution = self.timing_service.resolve_skill(row.name)
        evidence = getattr(resolution, "evidence", None)
        if evidence is None:
            self._timing_by_name[key] = None
            return None
        cast_time = getattr(evidence, "cast_time_seconds", None)
        channel_time = getattr(evidence, "channel_time_seconds", None)
        is_channeled = bool(getattr(evidence, "is_channeled", False))
        if is_channeled and channel_time is not None and float(channel_time) > 0.0:
            self._timing_by_name[key] = evidence
            return evidence
        if cast_time is not None and float(cast_time) > 0.0:
            self._timing_by_name[key] = evidence
            return evidence
        self._timing_by_name[key] = None
        return None

    def _supports(self, row: ExtremePlayerSkillRecord, capability: str) -> bool:
        if capability == GRANTS_RESOLVE:
            return self._supports_resolve(row)
        if capability == HAS_CAST_OR_CHANNEL_TIME:
            return self._timing_evidence(row) is not None
        return False

    def witness(
        self,
        capability: str,
        context: ExtremePlayerSkillLegalityContext,
    ) -> ExtremeActualHealSetupActionWitness:
        key = str(capability or "").strip().casefold()
        if key not in self._SUPPORTED:
            return ExtremeActualHealSetupActionWitness(
                capability=key,
                unresolved=(f"unsupported H1 setup capability: {key or '<empty>'}",),
            )

        legal = self.candidate_service.candidates(context, ultimate=False)
        matches = tuple(row for row in legal if self._supports(row, key))
        if not matches:
            return ExtremeActualHealSetupActionWitness(
                capability=key,
                unresolved=(
                    f"{key} has no reviewed route-legal non-Ultimate active-skill witness",
                ),
            )

        witness = sorted(
            matches,
            key=lambda row: (
                row.domain.value,
                row.skill_line.casefold(),
                row.name.casefold(),
                row.max_rank_ability_id or 0,
            ),
        )[0]
        ability_id = witness.max_rank_ability_id or witness.base_ability_id or witness.skill_id
        if key == GRANTS_RESOLVE:
            evidence_text = (
                f"{witness.name}: route-legal active skill explicitly grants Major/Minor Resolve"
            )
        else:
            timing = self._timing_evidence(witness)
            cast_time = getattr(timing, "cast_time_seconds", None)
            channel_time = getattr(timing, "channel_time_seconds", None)
            evidence_text = (
                f"{witness.name}: route-legal active skill has canonical cast/channel timing "
                f"cast={cast_time!r}s channel={channel_time!r}s"
            )
        return ExtremeActualHealSetupActionWitness(
            capability=key,
            skill_name=witness.name,
            skill_line=witness.skill_line,
            ability_id=int(ability_id) if ability_id is not None else None,
            evidence=evidence_text,
        )


__all__ = [
    "GRANTS_RESOLVE",
    "HAS_CAST_OR_CHANNEL_TIME",
    "ExtremeActualHealSetupActionWitness",
    "ExtremeActualHealSetupActionLegalityService",
]
