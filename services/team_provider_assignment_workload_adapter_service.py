from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectPolicy,
)
from services.team_provider_coverage_service import (
    TeamProviderCoverageProfile,
    TeamProviderCoverageService,
)
from services.team_provider_temporal_coverage_service import (
    TeamProviderTemporalCoverageService,
    TeamProviderTemporalRequirement,
    TeamProviderTimedApplication,
)
from services.team_provider_workload_candidate_service import (
    TeamProviderActionBinding,
    TeamProviderWorkloadAlternativeRequest,
    TeamProviderWorkloadCandidateRejection,
)


def _canonical(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


def _identity(character_name: object, build_name: object) -> tuple[str, str]:
    return (
        str(character_name or "").strip().casefold(),
        str(build_name or "").strip().casefold(),
    )


@dataclass(frozen=True)
class TeamProviderAssignedWorkloadPolicy:
    """Explicit workload-only semantics for one assigned provider requirement.

    Provider ownership stays authoritative in ``ProviderAssignment``. The exact
    effect, source skill, bar, and target uptime stay authoritative in
    ``RotationAssignmentEffectPolicy``. This policy contributes only facts needed
    to evaluate team workload: effect duration, recipient capacity, encounter
    window, workload horizon, source-count strategy, and explicit GCD/displacement
    assumptions.
    """

    requirement_id: str
    encounter_id: str
    effect_duration_seconds: float
    required_recipients: int
    targets_per_application: int
    window_start_seconds: float
    window_end_seconds: float
    workload_horizon_seconds: float
    minimum_distinct_sources: int = 1
    max_applications_per_cycle: int | None = None
    gcd_seconds_per_application: float | None = None
    primary_role_displacement_seconds: float | None = None
    source: str = "explicit provider workload policy"

    def __post_init__(self) -> None:
        for field_name in ("requirement_id", "encounter_id", "source"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"assigned workload policy {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)

        for field_name in (
            "effect_duration_seconds",
            "window_start_seconds",
            "window_end_seconds",
            "workload_horizon_seconds",
        ):
            value = float(getattr(self, field_name))
            if not isfinite(value):
                raise ValueError(f"{field_name} must be finite")
            object.__setattr__(self, field_name, value)

        if self.effect_duration_seconds <= 0:
            raise ValueError("effect_duration_seconds must be positive")
        if self.window_start_seconds < 0:
            raise ValueError("window_start_seconds cannot be negative")
        if self.window_end_seconds <= self.window_start_seconds:
            raise ValueError("window_end_seconds must be greater than window_start_seconds")
        if self.workload_horizon_seconds <= 0:
            raise ValueError("workload_horizon_seconds must be positive")
        if self.window_end_seconds > self.workload_horizon_seconds + 1e-9:
            raise ValueError("provider workload window cannot extend past workload horizon")
        if self.required_recipients < 0:
            raise ValueError("required_recipients cannot be negative")
        if self.targets_per_application <= 0:
            raise ValueError("targets_per_application must be positive")
        if self.minimum_distinct_sources <= 0:
            raise ValueError("minimum_distinct_sources must be positive")
        if self.max_applications_per_cycle is not None and self.max_applications_per_cycle <= 0:
            raise ValueError("max_applications_per_cycle must be positive when supplied")

        for field_name in (
            "gcd_seconds_per_application",
            "primary_role_displacement_seconds",
        ):
            value = getattr(self, field_name)
            if value is None:
                continue
            normalized = float(value)
            if not isfinite(normalized) or normalized < 0:
                raise ValueError(f"{field_name} must be finite and non-negative")
            object.__setattr__(self, field_name, normalized)


@dataclass(frozen=True)
class TeamProviderAssignmentWorkloadProjection:
    alternatives: tuple[TeamProviderWorkloadAlternativeRequest, ...]
    rejected: tuple[TeamProviderWorkloadCandidateRejection, ...]


class TeamProviderAssignmentWorkloadAdapterService:
    """Project assigned encounter providers into canonical workload requests.

    No assignment, effect, source skill, uptime, target capacity, or duration is
    inferred here. Exact primary providers come from Phase 11 assignment. Rotation
    semantics come from explicit assignment effect policy. Workload-only timing and
    recipient facts come from ``TeamProviderAssignedWorkloadPolicy``. Saved/explicit
    RotationPlans contribute only the casts that actually occurred in the plan.
    """

    @classmethod
    def project(
        cls,
        *,
        assignments: tuple[ProviderAssignment, ...],
        effect_policies: tuple[RotationAssignmentEffectPolicy, ...],
        workload_policies: tuple[TeamProviderAssignedWorkloadPolicy, ...],
        rotation_plans: tuple[RotationPlan, ...],
    ) -> TeamProviderAssignmentWorkloadProjection:
        assignment_by_id = cls._unique(assignments, "provider assignment")
        effect_by_id = cls._unique(effect_policies, "rotation assignment effect policy")
        workload_by_id = cls._unique(workload_policies, "provider workload policy")
        plans_by_identity = cls._unique_plans(rotation_plans)

        alternatives: list[TeamProviderWorkloadAlternativeRequest] = []
        rejected: list[TeamProviderWorkloadCandidateRejection] = []

        for requirement_key, workload_policy in workload_by_id.items():
            assignment = assignment_by_id.get(requirement_key)
            effect_policy = effect_by_id.get(requirement_key)
            blockers: list[str] = []

            if assignment is None:
                blockers.append(
                    f"{workload_policy.requirement_id}: no provider assignment is attached"
                )
            elif assignment.encounter_id != workload_policy.encounter_id:
                blockers.append(
                    f"{workload_policy.requirement_id}: workload policy encounter does not match provider assignment"
                )
            elif assignment.status is not ProviderAssignmentStatus.ASSIGNED:
                blockers.append(
                    f"{workload_policy.requirement_id}: provider assignment is {assignment.status.value}, not assigned"
                )

            if effect_policy is None:
                blockers.append(
                    f"{workload_policy.requirement_id}: no explicit rotation effect policy is attached"
                )
            elif effect_policy.encounter_id != workload_policy.encounter_id:
                blockers.append(
                    f"{workload_policy.requirement_id}: effect policy encounter does not match workload policy"
                )
            elif assignment is not None and effect_policy.requirement_type != assignment.requirement_type:
                blockers.append(
                    f"{workload_policy.requirement_id}: effect policy requirement type does not match provider assignment"
                )

            if blockers or assignment is None or effect_policy is None:
                rejected.append(
                    TeamProviderWorkloadCandidateRejection(
                        alternative_id=workload_policy.requirement_id,
                        effect_key=_canonical(
                            effect_policy.effect_name if effect_policy is not None else assignment.requirement_type if assignment is not None else workload_policy.requirement_id
                        ),
                        blockers=tuple(dict.fromkeys(blockers)),
                    )
                )
                continue

            primary_providers = assignment.primary_providers
            if not primary_providers:
                rejected.append(
                    TeamProviderWorkloadCandidateRejection(
                        alternative_id=workload_policy.requirement_id,
                        effect_key=_canonical(effect_policy.effect_name),
                        blockers=(
                            f"{workload_policy.requirement_id}: assigned provider row has no primary providers",
                        ),
                    )
                )
                continue

            timed_applications: list[TeamProviderTimedApplication] = []
            action_bindings: list[TeamProviderActionBinding] = []
            profiles: list[TeamProviderCoverageProfile] = []

            for provider in primary_providers:
                key = _identity(provider.character_name, provider.build_name)
                plan = plans_by_identity.get(key)
                label = f"{provider.character_name} / {provider.build_name}"
                if plan is None:
                    blockers.append(f"{label}: no exact rotation plan is attached")
                    continue

                matches = tuple(
                    action
                    for action in plan.actions
                    if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
                    and str(action.name or "").strip().casefold()
                    == effect_policy.source_skill_name.casefold()
                    and (effect_policy.bar is None or action.bar == effect_policy.bar)
                )
                if not matches:
                    bar_note = f" on {effect_policy.bar} bar" if effect_policy.bar else ""
                    blockers.append(
                        f"{label}: {effect_policy.source_skill_name!r}{bar_note} is not scheduled in the attached plan"
                    )
                    continue

                action_bindings.append(
                    TeamProviderActionBinding(
                        character_name=provider.character_name,
                        build_name=provider.build_name,
                        action_name=effect_policy.source_skill_name,
                        primary_role_displacement_seconds=(
                            workload_policy.primary_role_displacement_seconds
                        ),
                    )
                )
                profiles.append(
                    TeamProviderCoverageProfile(
                        provider_key=provider.member_id,
                        targets_per_application=workload_policy.targets_per_application,
                        max_applications_per_cycle=(
                            workload_policy.max_applications_per_cycle
                        ),
                    )
                )
                timed_applications.extend(
                    TeamProviderTimedApplication(
                        effect_key=_canonical(effect_policy.effect_name),
                        source=provider.member_id,
                        start_seconds=action.time_seconds,
                        duration_seconds=workload_policy.effect_duration_seconds,
                        application_label=effect_policy.source_skill_name,
                    )
                    for action in matches
                )

            if blockers:
                rejected.append(
                    TeamProviderWorkloadCandidateRejection(
                        alternative_id=workload_policy.requirement_id,
                        effect_key=_canonical(effect_policy.effect_name),
                        blockers=tuple(dict.fromkeys(blockers)),
                    )
                )
                continue

            recipient_coverage = TeamProviderCoverageService.combine(
                tuple(profiles),
                required_recipients=workload_policy.required_recipients,
            )
            temporal_requirement = TeamProviderTemporalRequirement(
                effect_key=_canonical(effect_policy.effect_name),
                start_seconds=workload_policy.window_start_seconds,
                end_seconds=workload_policy.window_end_seconds,
                label=workload_policy.requirement_id,
                minimum_distinct_sources=workload_policy.minimum_distinct_sources,
                target_coverage_ratio=effect_policy.minimum_uptime,
            )
            temporal_coverage = TeamProviderTemporalCoverageService.evaluate(
                temporal_requirement,
                applications=tuple(timed_applications),
            )

            alternatives.append(
                TeamProviderWorkloadAlternativeRequest(
                    alternative_id=workload_policy.requirement_id,
                    effect_key=_canonical(effect_policy.effect_name),
                    duration_seconds=workload_policy.workload_horizon_seconds,
                    recipient_coverage_result=recipient_coverage,
                    temporal_coverage_result=temporal_coverage,
                    action_bindings=tuple(action_bindings),
                    gcd_seconds_per_application=(
                        workload_policy.gcd_seconds_per_application
                    ),
                )
            )

        return TeamProviderAssignmentWorkloadProjection(
            alternatives=tuple(alternatives),
            rejected=tuple(rejected),
        )

    @staticmethod
    def _unique(rows, kind: str):
        result = {}
        for row in rows:
            key = str(row.requirement_id or "").strip().casefold()
            if not key:
                raise ValueError(f"{kind} requirement_id must be non-empty")
            if key in result:
                raise ValueError(f"duplicate {kind} requirement_id: {row.requirement_id!r}")
            result[key] = row
        return result

    @staticmethod
    def _unique_plans(plans: tuple[RotationPlan, ...]) -> dict[tuple[str, str], RotationPlan]:
        result: dict[tuple[str, str], RotationPlan] = {}
        for plan in plans:
            key = _identity(plan.character_name, plan.build_name)
            if key in result:
                raise ValueError(
                    f"multiple rotation plans are attached for: {key[0]} / {key[1]}"
                )
            result[key] = plan
        return result


__all__ = [
    "TeamProviderAssignedWorkloadPolicy",
    "TeamProviderAssignmentWorkloadAdapterService",
    "TeamProviderAssignmentWorkloadProjection",
]
