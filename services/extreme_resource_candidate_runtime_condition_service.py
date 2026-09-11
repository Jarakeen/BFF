from __future__ import annotations

"""Intersect the global max-resource runtime denominator with one candidate build."""

from dataclasses import dataclass
from pathlib import Path

from minmax.gear_stat_inputs import GearStatInputResolver
from models.build_model import PlayerBuild
from services.extreme_heal_class_route_service import ExtremeHealClassRoute
from services.extreme_resource_runtime_condition_state_service import (
    ExtremeResourceRuntimeConditionState,
    ExtremeResourceRuntimeConditionStateService,
)
from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeConditionEvidence,
    ExtremeResourceRuntimeCoverageAuditService,
)
from services.extreme_resource_runtime_skill_witness_materialization_service import (
    ExtremeResourceRuntimeSkillWitnessMaterialization,
    ExtremeResourceRuntimeSkillWitnessMaterializationService,
)


_SKILL_CONDITIONS = frozenset(
    {
        "armor_ability_slotted",
        "pet_active",
        "transformed",
    }
)


@dataclass(frozen=True)
class ExtremeResourceCandidateRuntimeConditionProjection:
    objective_key: str
    candidate_effects: tuple[ExtremeResourceRuntimeConditionEvidence, ...]
    state: ExtremeResourceRuntimeConditionState
    build: PlayerBuild
    denominator_proven: bool
    skill_witnesses: ExtremeResourceRuntimeSkillWitnessMaterialization | None = None
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
        skill_witness_materialization_service: ExtremeResourceRuntimeSkillWitnessMaterializationService | None = None,
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
        self.skill_witness_materialization_service = (
            skill_witness_materialization_service
            or (
                ExtremeResourceRuntimeSkillWitnessMaterializationService(database_path)
                if database_path is not None
                else None
            )
        )

    def build(
        self,
        objective_key: str,
        *,
        build: PlayerBuild,
        active_bar: str = "front",
        food: str = "",
        route: ExtremeHealClassRoute | None = None,
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
        ordinary_required = tuple(
            condition for condition in required if condition not in _SKILL_CONDITIONS
        )
        skill_required = tuple(
            condition for condition in required if condition in _SKILL_CONDITIONS
        )

        base_state = self.condition_state_service.build(
            objective_key,
            required_conditions=ordinary_required,
            build=build,
            active_bar=active_bar,
            food=food,
        )

        materialized_build = PlayerBuild.from_dict(build.to_dict())
        skill_witnesses = None
        active = set(base_state.active_conditions)
        unresolved_conditions = list(base_state.unresolved_conditions)
        evidence = list(base_state.evidence)

        if skill_required:
            if route is None:
                unresolved_conditions.extend(
                    f"{condition} requires the selected Extreme class route for witness materialization"
                    for condition in skill_required
                )
            elif self.skill_witness_materialization_service is None:
                unresolved_conditions.append(
                    "Extreme runtime skill-witness materialization service is unavailable"
                )
            else:
                skill_witnesses = self.skill_witness_materialization_service.materialize(
                    build=materialized_build,
                    route=route,
                    required_conditions=skill_required,
                    active_bar=active_bar,
                )
                materialized_build = skill_witnesses.build
                active.update(skill_witnesses.active_conditions)
                unresolved_conditions.extend(skill_witnesses.unresolved)
                evidence.extend(
                    f"{condition}: canonical skill witness {skill_name}"
                    for condition, skill_name in skill_witnesses.witnesses
                )
                evidence.extend(
                    f"runtime witness displaced slot {slot}: {skill_name}"
                    for slot, skill_name in skill_witnesses.displaced_skills
                )

        state = ExtremeResourceRuntimeConditionState(
            objective_key=str(objective_key or "").strip().casefold(),
            required_conditions=required,
            active_conditions=tuple(sorted(active, key=str.casefold)),
            unresolved_conditions=tuple(
                dict.fromkeys(item for item in unresolved_conditions if item)
            ),
            evidence=tuple(dict.fromkeys(item for item in evidence if item)),
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
            build=materialized_build,
            denominator_proven=bool(audit.denominator_proven),
            skill_witnesses=skill_witnesses,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )


__all__ = [
    "ExtremeResourceCandidateRuntimeConditionProjection",
    "ExtremeResourceCandidateRuntimeConditionService",
]
