from __future__ import annotations

from dataclasses import dataclass

from minmax.encounter_requirements import EncounterRequirementSet
from minmax.rotation_bar_availability import (
    RotationBarAvailabilityAssessment,
    RotationBarAvailabilityAssessor,
    RotationBarAvailabilityWindow,
)
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.rotation_resource_reserve import (
    RotationResourceReserveAssessment,
    RotationResourceReserveRequirement,
    assess_rotation_resource_reserves,
)
from minmax.support_coverage import SupportCoverage
from services.rotation_duration_analysis_service import RotationDurationProjection
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationPlanConsequenceService,
)
from services.rotation_runtime_uptime_service import (
    RotationRuntimeUptimeAssessment,
    RotationRuntimeUptimeObjective,
    RotationRuntimeUptimeObjectiveAssessment,
    RotationRuntimeUptimeRequirement,
    assess_rotation_runtime_uptime_objective,
    assess_rotation_runtime_uptimes,
)
from services.rotation_sustain_service import RotationSustainProjection


@dataclass(frozen=True)
class RotationDemandActionRequirement:
    """Explicit action evidence required inside one named encounter demand window."""

    demand_name: str
    skill_name: str
    bar: str | None = None
    minimum_casts: int = 1

    def __post_init__(self) -> None:
        demand = str(self.demand_name or "").strip()
        skill = str(self.skill_name or "").strip()
        if not demand:
            raise ValueError("rotation demand action requirement needs demand_name")
        if not skill:
            raise ValueError("rotation demand action requirement needs skill_name")
        object.__setattr__(self, "demand_name", demand)
        object.__setattr__(self, "skill_name", skill)

        if self.bar is not None:
            bar = str(self.bar).strip().casefold()
            if bar not in {"front", "back"}:
                raise ValueError("rotation demand action requirement bar must be front or back")
            object.__setattr__(self, "bar", bar)

        casts = int(self.minimum_casts)
        if casts <= 0:
            raise ValueError("rotation demand action requirement minimum_casts must be positive")
        object.__setattr__(self, "minimum_casts", casts)


@dataclass(frozen=True)
class RotationDemandCoverageEvidence:
    requirement: RotationDemandActionRequirement
    demand: RotationDemandWindow
    observed_casts: int
    cast_times: tuple[float, ...]

    @property
    def satisfied(self) -> bool:
        return self.observed_casts >= self.requirement.minimum_casts


@dataclass(frozen=True)
class RotationCandidateScorecard:
    """Explainable candidate evidence without collapsing it into one magic score."""

    consequence: RotationPlanConsequence
    demand_coverage: tuple[RotationDemandCoverageEvidence, ...]
    missing_required_effects: tuple[str, ...]
    candidate_shortfall: int
    inherited_unresolved: tuple[str, ...]
    candidate_specific_unresolved: tuple[str, ...]
    inherited_schedule_notes: tuple[str, ...] = ()
    candidate_specific_schedule_notes: tuple[str, ...] = ()
    reserve_assessments: tuple[RotationResourceReserveAssessment, ...] = ()
    bar_availability_assessment: RotationBarAvailabilityAssessment | None = None
    runtime_uptime_assessments: tuple[RotationRuntimeUptimeAssessment, ...] = ()
    runtime_uptime_objective_assessment: (
        RotationRuntimeUptimeObjectiveAssessment | None
    ) = None

    @property
    def unresolved(self) -> tuple[str, ...]:
        """Only genuinely unresolved evidence retained for ranking/diagnostics."""
        return self.inherited_unresolved + self.candidate_specific_unresolved

    @property
    def schedule_notes(self) -> tuple[str, ...]:
        """Deterministic scheduler provenance that is informative, not uncertainty."""
        return self.inherited_schedule_notes + self.candidate_specific_schedule_notes

    @property
    def missing_demand_requirements(self) -> tuple[RotationDemandActionRequirement, ...]:
        return tuple(item.requirement for item in self.demand_coverage if not item.satisfied)

    @property
    def failed_reserve_assessments(self) -> tuple[RotationResourceReserveAssessment, ...]:
        return tuple(item for item in self.reserve_assessments if not item.satisfied)

    @property
    def bar_availability_violations(self):
        if self.bar_availability_assessment is None:
            return ()
        return self.bar_availability_assessment.violations

    @property
    def failed_runtime_uptime_assessments(
        self,
    ) -> tuple[RotationRuntimeUptimeAssessment, ...]:
        return tuple(item for item in self.runtime_uptime_assessments if not item.satisfied)

    @property
    def supplied_obligations_satisfied(self) -> bool:
        """Whether all caller-supplied hard obligations are currently satisfied.

        This does not claim the rotation is globally optimal or that static effect
        coverage proves runtime uptime. It only answers the explicit obligations
        supplied to this scorecard.
        """
        return (
            not self.missing_demand_requirements
            and not self.missing_required_effects
            and not self.failed_reserve_assessments
            and not self.bar_availability_violations
            and not self.failed_runtime_uptime_assessments
            and self.candidate_shortfall == 0
        )


class RotationCandidateScorecardService:
    """Combine resource consequences with explicit encounter obligation evidence.

    The scorecard intentionally does not assign weights or choose a winner. Demand
    coverage is based only on exact caller-supplied action requirements. Required
    support effects use the existing static SupportCoverage model and therefore do
    not claim runtime uptime. Explicit runtime uptime requirements are assessed only
    when the caller also supplies canonical duration/recast evidence.

    Optional resource-reserve requirements and encounter bar-availability windows
    are caller-supplied hard obligations. This layer never invents how much resource
    a mechanic requires or which bar an encounter permits. Unresolved evidence is
    split into inherited/shared baseline limitations and candidate-specific additions.
    Deterministic refresh-slot cascade messages are retained separately as schedule
    provenance rather than ranked as uncertainty.
    """

    def __init__(
        self,
        consequence_service: RotationPlanConsequenceService | None = None,
        bar_availability_assessor: RotationBarAvailabilityAssessor | None = None,
    ) -> None:
        self.consequence_service = consequence_service or RotationPlanConsequenceService()
        self.bar_availability_assessor = (
            bar_availability_assessor or RotationBarAvailabilityAssessor()
        )

    def compare(
        self,
        *,
        baseline_plan: RotationPlan,
        candidate_plan: RotationPlan,
        baseline_sustain: RotationSustainProjection,
        candidate_sustain: RotationSustainProjection,
        demands: tuple[RotationDemandWindow, ...] = (),
        demand_requirements: tuple[RotationDemandActionRequirement, ...] = (),
        reserve_requirements: tuple[RotationResourceReserveRequirement, ...] = (),
        bar_availability_windows: tuple[RotationBarAvailabilityWindow, ...] = (),
        encounter_requirements: EncounterRequirementSet | None = None,
        support_coverage: SupportCoverage | None = None,
        candidate_duration: RotationDurationProjection | None = None,
        runtime_uptime_requirements: tuple[RotationRuntimeUptimeRequirement, ...] = (),
        runtime_uptime_objective: RotationRuntimeUptimeObjective | None = None,
    ) -> RotationCandidateScorecard:
        demand_by_name: dict[str, RotationDemandWindow] = {}
        for demand in demands:
            if demand.name in demand_by_name:
                raise ValueError(f"duplicate rotation demand name: {demand.name!r}")
            demand_by_name[demand.name] = demand

        coverage: list[RotationDemandCoverageEvidence] = []
        for requirement in demand_requirements:
            demand = demand_by_name.get(requirement.demand_name)
            if demand is None:
                raise ValueError(
                    "rotation demand action requirement references unknown demand "
                    f"{requirement.demand_name!r}"
                )
            cast_times = self._matching_cast_times(
                candidate_plan,
                demand=demand,
                requirement=requirement,
            )
            coverage.append(
                RotationDemandCoverageEvidence(
                    requirement=requirement,
                    demand=demand,
                    observed_casts=len(cast_times),
                    cast_times=cast_times,
                )
            )

        for requirement in reserve_requirements:
            if requirement.demand_name not in demand_by_name:
                raise ValueError(
                    "rotation resource reserve requirement references unknown demand "
                    f"{requirement.demand_name!r}"
                )
        reserve_assessments = assess_rotation_resource_reserves(
            timeline=candidate_sustain.run.timeline,
            demands=demands,
            requirements=reserve_requirements,
        )

        bar_assessment = (
            self.bar_availability_assessor.assess(candidate_plan, bar_availability_windows)
            if bar_availability_windows
            else None
        )

        if (encounter_requirements is None) != (support_coverage is None):
            raise ValueError(
                "static required-effect coverage requires both encounter_requirements and support_coverage"
            )
        missing_effects: tuple[str, ...] = ()
        if encounter_requirements is not None and support_coverage is not None:
            missing_effects = support_coverage.missing_from(
                encounter_requirements.required_effect_names()
            )

        if (
            runtime_uptime_requirements or runtime_uptime_objective is not None
        ) and candidate_duration is None:
            raise ValueError(
                "runtime uptime requirements/objective need candidate duration evidence"
            )
        uptime_assessments = (
            assess_rotation_runtime_uptimes(
                projection=candidate_duration,
                requirements=runtime_uptime_requirements,
            )
            if candidate_duration is not None
            else ()
        )
        uptime_objective_assessment = (
            assess_rotation_runtime_uptime_objective(
                projection=candidate_duration,
                objective=runtime_uptime_objective,
            )
            if candidate_duration is not None and runtime_uptime_objective is not None
            else None
        )

        consequence = self.consequence_service.compare(
            baseline_plan=baseline_plan,
            candidate_plan=candidate_plan,
            baseline_sustain=baseline_sustain,
            candidate_sustain=candidate_sustain,
        )

        baseline_all = self._dedupe(
            tuple(baseline_plan.unresolved) + tuple(baseline_sustain.unresolved)
        )
        candidate_all = self._dedupe(
            tuple(candidate_plan.unresolved) + tuple(candidate_sustain.unresolved)
        )

        baseline_notes, baseline_unresolved = self._partition_scheduler_notes(baseline_all)
        candidate_notes, candidate_unresolved = self._partition_scheduler_notes(candidate_all)

        baseline_unresolved_keys = {item.casefold() for item in baseline_unresolved}
        inherited_unresolved = tuple(
            item for item in candidate_unresolved if item.casefold() in baseline_unresolved_keys
        )
        candidate_specific_unresolved = tuple(
            item for item in candidate_unresolved if item.casefold() not in baseline_unresolved_keys
        )

        baseline_note_keys = {item.casefold() for item in baseline_notes}
        inherited_notes = tuple(
            item for item in candidate_notes if item.casefold() in baseline_note_keys
        )
        candidate_specific_notes = tuple(
            item for item in candidate_notes if item.casefold() not in baseline_note_keys
        )

        return RotationCandidateScorecard(
            consequence=consequence,
            demand_coverage=tuple(coverage),
            missing_required_effects=missing_effects,
            candidate_shortfall=int(candidate_sustain.run.timeline.total_shortfall),
            inherited_unresolved=inherited_unresolved,
            candidate_specific_unresolved=candidate_specific_unresolved,
            inherited_schedule_notes=inherited_notes,
            candidate_specific_schedule_notes=candidate_specific_notes,
            reserve_assessments=reserve_assessments,
            bar_availability_assessment=bar_assessment,
            runtime_uptime_assessments=uptime_assessments,
            runtime_uptime_objective_assessment=uptime_objective_assessment,
        )

    @staticmethod
    def _matching_cast_times(
        plan: RotationPlan,
        *,
        demand: RotationDemandWindow,
        requirement: RotationDemandActionRequirement,
    ) -> tuple[float, ...]:
        target = requirement.skill_name.casefold()
        return tuple(
            float(action.time_seconds)
            for action in plan.actions
            if action.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}
            and action.name
            and str(action.name).casefold() == target
            and (requirement.bar is None or action.bar == requirement.bar)
            and demand.start_seconds <= float(action.time_seconds) < demand.end_seconds
        )

    @staticmethod
    def _is_deterministic_cascade_trace(value: str) -> bool:
        normalized = value.strip().casefold()
        return (
            normalized.startswith("refresh obligation for '")
            and " claimed the " in normalized
            and normalized.endswith(
                "displaced skill will cascade to the next same-bar skill slot"
            )
        )

    @classmethod
    def _partition_scheduler_notes(
        cls,
        values: tuple[str, ...],
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        notes: list[str] = []
        unresolved: list[str] = []
        for value in values:
            if cls._is_deterministic_cascade_trace(value):
                notes.append(value)
            else:
                unresolved.append(value)
        return tuple(notes), tuple(unresolved)

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return tuple(ordered)
