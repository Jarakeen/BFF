from __future__ import annotations

"""Intersect the global max-resource runtime denominator with one candidate build."""

from dataclasses import dataclass
from pathlib import Path

from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_resource_runtime_condition_state_service import (
    ExtremeResourceRuntimeConditionState,
    ExtremeResourceRuntimeConditionStateService,
)
from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeConditionEvidence,
    ExtremeResourceRuntimeCoverageAuditService,
)


@dataclass(frozen=True)
class ExtremeResourceCandidateRuntimeConditionProjection:
    objective_key: str
    candidate_effects: tuple[ExtremeResourceRuntimeConditionEvidence, ...]
    state: ExtremeResourceRuntimeConditionState
    denominator_proven: bool
    unresolved: tuple[str, ...] = ()

    @property
    def required_conditions(self) -> tuple[str, ...]:
        return self.state.required_conditions

    @property
    def active_conditions(self) -> tuple[str, ...]:
        return self.state.active_conditions

    @property
    def condition_context(self) -> frozenset[str]:
        return self.state.condition_context

    @property
    def projection_complete(self) -> bool:
        return bool(
            self.denominator_proven
            and self.state.projection_complete
            and not self.unresolved
        )


class ExtremeResourceCandidateRuntimeConditionService:
    """Resolve only runtime conditions contributed by sets worn by a candidate."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        coverage_audit_service: ExtremeResourceRuntimeCoverageAuditService | None = None,
        condition_state_service: ExtremeResourceRuntimeConditionStateService | None = None,
    ) -> None:
        if database_path is None and (
            coverage_audit_service is None or condition_state_service is None
        ):
            raise ValueError(
                "database_path is required unless both runtime audit and condition-state services are supplied"
            )
        self.coverage_audit_service = coverage_audit_service or ExtremeResourceRuntimeCoverageAuditService(
            database_path
        )
        self.condition_state_service = condition_state_service or ExtremeResourceRuntimeConditionStateService(
            database_path  # type: ignore[arg-type]
        )

    def build(
        self,
        objective_key: str,
        *,
        build: PlayerBuild,
        active_bar: str = "front",
        food: str = "",
    ) -> ExtremeResourceCandidateRuntimeConditionProjection:
        audit = self.coverage_audit_service.build(objective_key)
        counts = GearStatInputResolver.equipped_set_counts(build, active_bar=active_bar)

        effects = tuple(
            row
            for row in audit.conditional_gear_effects
            if int(counts.get(row.set_name, 0)) >= int(row.piece_count)
        )
        required = tuple(
            sorted({row.condition for row in effects}, key=str.casefold)
        )
        state = self.condition_state_service.build(
            objective_key,
            required_conditions=required,
            build=build,
            active_bar=active_bar,
            food=food,
        )

        unresolved: list[str] = list(audit.unresolved)
        if not audit.denominator_proven:
            unresolved.append(
                f"Global Extreme runtime denominator is not proven for {objective_key}"
            )

        return ExtremeResourceCandidateRuntimeConditionProjection(
            objective_key=str(objective_key or "").strip().casefold(),
            candidate_effects=effects,
            state=state,
            denominator_proven=bool(audit.denominator_proven),
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeResourceCandidateRuntimeConditionProjection",
    "ExtremeResourceCandidateRuntimeConditionService",
]
