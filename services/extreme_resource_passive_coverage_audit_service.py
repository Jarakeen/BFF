from __future__ import annotations

"""Inventory canonical passive coverage for Extreme max-resource objectives.

This is deliberately a coverage/audit layer, not a second passive calculator.
Every canonical player passive is classified through ``ExtremePassiveProjectionService``.
Simple unconditional max-resource clauses can therefore be identified as reviewed
static contributors, while bar/equipment/runtime-dependent and unparsed mechanics
remain explicit blockers.

Racial resource passives are reconciled against the same Phase 5 tooltip resolver
used by canonical Extreme resource scoring.  The historical aggregate ``race_stat``
repository remains a compatibility fallback for injected/legacy callers, but it is
not the primary proof source for production audits.

A complete inventory denominator is not the same as complete mechanic coverage.
The audit never assigns zero value to contextual or unresolved passives.
"""

from dataclasses import dataclass
from pathlib import Path

from minmax.character_progression import CharacterProgression
from minmax.race_repository import RaceRepository
from minmax.racial_passive_stat_repository import RacialPassiveStatRepository
from services.extreme_passive_projection_service import (
    ExtremePassiveProjectionService,
    ExtremePassiveProjectionStatus,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
    ExtremeSkillUniverseService,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


@dataclass(frozen=True)
class ExtremeResourcePassiveCoverageAudit:
    objective_key: str
    passives_reviewed: int
    static_relevant: tuple[str, ...]
    accounted_elsewhere: tuple[str, ...]
    static_irrelevant: tuple[str, ...]
    context_required: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def denominator_proven(self) -> bool:
        classified = (
            len(self.static_relevant)
            + len(self.accounted_elsewhere)
            + len(self.static_irrelevant)
            + len(self.context_required)
            + len(self.unresolved)
        )
        return self.passives_reviewed > 0 and classified == self.passives_reviewed

    @property
    def projection_complete(self) -> bool:
        """Whether every passive is resolved for this audit boundary."""
        return (
            self.denominator_proven
            and not self.static_relevant
            and not self.context_required
            and not self.unresolved
        )


class ExtremeResourcePassiveCoverageAuditService:
    """Classify every canonical player passive for one max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        universe_service: ExtremeSkillUniverseService | None = None,
        race_repository: RaceRepository | None = None,
        racial_passive_repository: RacialPassiveStatRepository | None = None,
    ) -> None:
        if universe_service is None and database_path is None:
            raise ValueError("database_path is required when no skill universe service is supplied")
        self.universe_service = universe_service or ExtremeSkillUniverseService(database_path)  # type: ignore[arg-type]
        self.race_repository = race_repository or (
            RaceRepository(database_path) if database_path is not None else None
        )
        self.racial_passive_repository = racial_passive_repository or (
            RacialPassiveStatRepository(database_path) if database_path is not None else None
        )

    @staticmethod
    def _identity(passive: ExtremePlayerSkillRecord) -> str:
        domain = passive.domain.value
        line = str(passive.skill_line or "").strip() or "<no line>"
        return f"[{domain}] {line} :: {passive.name}"

    @staticmethod
    def _race_name(passive: ExtremePlayerSkillRecord) -> str:
        line = str(passive.skill_line or "").strip()
        suffix = " skills"
        if line.casefold().endswith(suffix):
            return line[: -len(suffix)].strip()
        return ""

    def _phase5_racial_resource_accounted(
        self,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
        passives: tuple[ExtremePlayerSkillRecord, ...],
    ) -> bool:
        repository = self.racial_passive_repository
        if passive.domain is not ExtremeSkillDomain.RACIAL or repository is None:
            return False
        race_name = self._race_name(passive)
        if not race_name:
            return False

        expected_line = str(passive.skill_line or "").strip().casefold()
        race_passives = tuple(
            row
            for row in passives
            if row.domain is ExtremeSkillDomain.RACIAL
            and str(row.skill_line or "").strip().casefold() == expected_line
        )
        if not race_passives:
            return False

        passive_ranks: dict[str, int] = {}
        for row in race_passives:
            passive_ranks[row.name] = 0
        try:
            target_rank = int(passive.max_rank or 0)
        except (TypeError, ValueError):
            target_rank = 0
        if target_rank <= 0:
            return False
        passive_ranks[passive.name] = target_rank

        resolution = repository.resolve(
            race_name,
            CharacterProgression(passive_ranks=passive_ranks),
        )
        if resolution.unresolved:
            return False
        try:
            value = float(resolution.stats.get(objective_key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return False
        return value != 0.0

    def _legacy_racial_resource_accounted(
        self,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
    ) -> bool:
        if passive.domain is not ExtremeSkillDomain.RACIAL or self.race_repository is None:
            return False
        race_name = self._race_name(passive)
        if not race_name:
            return False
        stat_map = self.race_repository.get_stat_map_by_name(race_name)
        try:
            value = float(stat_map.get(objective_key, 0.0) or 0.0)
        except (TypeError, ValueError):
            return False
        return value != 0.0

    def _racial_resource_already_accounted(
        self,
        passive: ExtremePlayerSkillRecord,
        objective_key: str,
        passives: tuple[ExtremePlayerSkillRecord, ...],
    ) -> bool:
        if self._phase5_racial_resource_accounted(passive, objective_key, passives):
            return True
        return self._legacy_racial_resource_accounted(passive, objective_key)

    def build(self, objective_key: str) -> ExtremeResourcePassiveCoverageAudit:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource passive objective: {objective_key!r}")

        passives = tuple(self.universe_service.passives())
        static_relevant: list[str] = []
        accounted_elsewhere: list[str] = []
        static_irrelevant: list[str] = []
        context_required: list[str] = []
        unresolved: list[str] = []

        for passive in passives:
            projection = ExtremePassiveProjectionService.project(passive)
            identity = self._identity(passive)
            if projection.status is ExtremePassiveProjectionStatus.REVIEWED_STATIC:
                relevant = any(row.objective_key == key for row in projection.contributions)
                if relevant and self._racial_resource_already_accounted(passive, key, passives):
                    accounted_elsewhere.append(identity)
                elif relevant:
                    static_relevant.append(identity)
                else:
                    static_irrelevant.append(identity)
            elif projection.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED:
                context_required.append(identity)
            elif projection.status is ExtremePassiveProjectionStatus.KNOWN_NONCOMBAT:
                static_irrelevant.append(identity)
            else:
                unresolved.append(identity)

        return ExtremeResourcePassiveCoverageAudit(
            objective_key=key,
            passives_reviewed=len(passives),
            static_relevant=tuple(sorted(static_relevant, key=str.casefold)),
            accounted_elsewhere=tuple(sorted(accounted_elsewhere, key=str.casefold)),
            static_irrelevant=tuple(sorted(static_irrelevant, key=str.casefold)),
            context_required=tuple(sorted(context_required, key=str.casefold)),
            unresolved=tuple(sorted(unresolved, key=str.casefold)),
        )
