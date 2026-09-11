from __future__ import annotations

"""Inventory canonical passive coverage for Extreme max-resource objectives.

This is deliberately a coverage/audit layer, not a second passive calculator.
Every canonical player passive is classified through ``ExtremePassiveProjectionService``.
Simple unconditional max-resource clauses can therefore be identified as reviewed
static contributors, while bar/equipment/runtime-dependent and unparsed mechanics
remain explicit blockers.

A complete inventory denominator is not the same as complete mechanic coverage.
The audit never assigns zero value to contextual or unresolved passives.
"""

from dataclasses import dataclass
from pathlib import Path

from services.extreme_passive_projection_service import (
    ExtremePassiveProjectionService,
    ExtremePassiveProjectionStatus,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillUniverseService,
)


_SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")


@dataclass(frozen=True)
class ExtremeResourcePassiveCoverageAudit:
    objective_key: str
    passives_reviewed: int
    static_relevant: tuple[str, ...]
    static_irrelevant: tuple[str, ...]
    context_required: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def denominator_proven(self) -> bool:
        classified = (
            len(self.static_relevant)
            + len(self.static_irrelevant)
            + len(self.context_required)
            + len(self.unresolved)
        )
        return self.passives_reviewed > 0 and classified == self.passives_reviewed

    @property
    def projection_complete(self) -> bool:
        """Whether every passive is losslessly static for this audit boundary."""
        return self.denominator_proven and not self.context_required and not self.unresolved


class ExtremeResourcePassiveCoverageAuditService:
    """Classify every canonical player passive for one max-resource objective."""

    SUPPORTED_OBJECTIVES = _SUPPORTED_OBJECTIVES

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        universe_service: ExtremeSkillUniverseService | None = None,
    ) -> None:
        if universe_service is None and database_path is None:
            raise ValueError("database_path is required when no skill universe service is supplied")
        self.universe_service = universe_service or ExtremeSkillUniverseService(database_path)  # type: ignore[arg-type]

    @staticmethod
    def _identity(passive: ExtremePlayerSkillRecord) -> str:
        domain = passive.domain.value
        line = str(passive.skill_line or "").strip() or "<no line>"
        return f"[{domain}] {line} :: {passive.name}"

    def build(self, objective_key: str) -> ExtremeResourcePassiveCoverageAudit:
        key = str(objective_key or "").strip().casefold()
        if key not in _SUPPORTED_OBJECTIVES:
            raise KeyError(f"unreviewed Extreme resource passive objective: {objective_key!r}")

        passives = tuple(self.universe_service.passives())
        static_relevant: list[str] = []
        static_irrelevant: list[str] = []
        context_required: list[str] = []
        unresolved: list[str] = []

        for passive in passives:
            projection = ExtremePassiveProjectionService.project(passive)
            identity = self._identity(passive)
            if projection.status is ExtremePassiveProjectionStatus.REVIEWED_STATIC:
                if any(row.objective_key == key for row in projection.contributions):
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
            static_irrelevant=tuple(sorted(static_irrelevant, key=str.casefold)),
            context_required=tuple(sorted(context_required, key=str.casefold)),
            unresolved=tuple(sorted(unresolved, key=str.casefold)),
        )
