from __future__ import annotations

from dataclasses import dataclass

from minmax.encounter_requirements import EncounterRequirementSet
from minmax.rotation_action_cooldown import (
    RotationActionCooldownAssessment,
    RotationActionCooldownAssessor,
    RotationActionCooldownRequirement,
)
from minmax.rotation_action_occupancy import (
    RotationActionOccupancyAssessment,
    RotationActionOccupancyAssessor,
    RotationActionOccupancyRequirement,
)
from minmax.rotation_action_range import (
    RotationActionRangeAssessment,
    RotationActionRangeAssessor,
    RotationActionRangeRequirement,
    RotationTargetDistanceWindow,
)
from minmax.rotation_action_slot_legality import (
    RotationActionSlotAssessment,
    RotationActionSlotAssessor,
    RotationActionSlotRequirement,
)
from minmax.rotation_action_target_legality import (
    RotationActionTargetAssessment,
    RotationActionTargetAssessor,
    RotationActionTargetRequirement,
    RotationTargetStateWindow,
)
from minmax.rotation_active_bar_legality import RotationActiveBarAssessment
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
from minmax.rotation_ultimate_affordability import (
    RotationUltimateAffordabilityAssessment,
    RotationUltimateAffordabilityAssessor,
    RotationUltimateAffordabilityRequirement,
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
    cooldown_assessment: RotationActionCooldownAssessment | None = None
    occupancy_assessment: RotationActionOccupancyAssessment | None = None
    range_assessment: RotationActionRangeAssessment | None = None
    target_assessment: RotationActionTargetAssessment | None = None
    slot_assessment: RotationActionSlotAssessment | None = None
    active_bar_assessment: RotationActiveBarAssessment | None = None
    ultimate_affordability_assessment: RotationUltimateAffordabilityAssessment | None = None
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
    def cooldown_violations(self):
        if self.cooldown_assessment is None:
            return ()
        return self.cooldown_assessment.violations

    @property
    def occupancy_violations(self):
        if self.occupancy_assessment is None:
            return ()
        return self.occupancy_assessment.violations

    @property
    def range_violations(self):
        if self.range_assessment is None:
            return ()
        return self.range_assessment.violations

    @property
    def target_violations(self):
        if self.target_assessment is None:
            return ()
        return self.target_assessment.violations

    @property
    def slot_violations(self):
        if self.slot_assessment is None:
            return ()
        return self.slot_assessment.violations

    @property
    def active_bar_violations(self):
        if self.active_bar_assessment is None:
            return ()
        return self.active_bar_assessment.violations

    @property
    def ultimate_affordability_violations(self):
        if self.ultimate_affordability_assessment is None:
            return ()
        return self.ultimate_affordability_assessment.violations

    @property
    def failed_runtime_uptime_assessments(
        self,
    ) -> tuple[RotationRuntimeUptimeAssessment, ...]:
        return tuple(item for item in self.runtime_uptime_assessments if not item.satisfied)

    @property
    def supplied_obligations_satisfied(self) -> bool:
        """Whether all explicit candidate-specific hard obligations are satisfied.

        Inherited/shared unresolved evidence remains diagnostic because every
        candidate carries the same limitation. Candidate-specific unresolved
        evidence is hard-failing because it means this candidate itself depends on
        mechanics that are not sufficiently resolved to recommend it safely.
        """
        return (
            not self.missing_demand_requirements
            and not self.missing_required_effects
            and not self.failed_reserve_assessments
            and not self.bar_availability_violations
            and not self.cooldown_violations
            and not self.occupancy_violations
            and not self.range_violations
            and not self.target_violations
            and not self.slot_violations
            and not self.active_bar_violations
            and not self.ultimate_affordability_violations
            and not self.failed_runtime_uptime_assessments
            and not self.candidate_specific_unresolved
            and self.candidate_shortfall == 0
        )


class RotationCandidateScorecardService:
    """Combine resource consequences with explicit encounter obligation evidence.

    The scorecard intentionally does not assign weights or choose a winner. Demand
    coverage is based only on exact caller-supplied action requirements. Required
    support effects use the existing static SupportCoverage model and therefore do
    not claim runtime uptime. Explicit runtime uptime requirements are assessed only
    when the caller also supplies canonical duration/recast evidence.

    Optional resource-reserve requirements, encounter bar-availability windows,
    resolved action cooldowns, resolved skill/ultimate occupancy durations,
    explicit target-distance/range evidence, explicit target-state legality,
    exact slotted-bar ownership, and explicit shared-pool Ultimate affordability
    evidence are caller-supplied hard obligations. This layer never invents resource
    reserves, bar restrictions, cooldowns, cast times, channel times, target
    distance, skill range, target identity, slot ownership, Ultimate costs, or
    Ultimate generation. Unresolved evidence is split into inherited/shared baseline
    limitations and candidate-specific additions. Candidate-specific unresolved
    evidence is hard-failing; inherited/shared unresolved evidence remains
    diagnostic. Deterministic refresh-slot cascade messages are retained separately
    as schedule provenance rather than ranked as uncertainty.
    """

    def __init__(
        self,
        consequence_service: RotationPlanConsequenceService | None = None,
        bar_availability_assessor: RotationBarAvailabilityAssessor | None = None,
        cooldown_assessor: RotationActionCooldownAssessor | None = None,
        occupancy_assessor: RotationActionOccupancyAssessor | None = None,
        range_assessor: RotationActionRangeAssessor | None = None,
        target_assessor: RotationActionTargetAssessor | None = None,
        slot_assessor: RotationActionSlotAssessor | None = None,
        ultimate_affordability_assessor: RotationUltimateAffordabilityAssessor | None = None,
    ) -> None:
        self.consequence_service = consequence_service or RotationPlanConsequenceService()
        self.bar_availability_assessor = (
            bar_availability_assessor or RotationBarAvailabilityAssessor()
        )
        self.cooldown_assessor = cooldown_assessor or RotationActionCooldownAssessor()
        self.occupancy_assessor = occupancy_assessor or RotationActionOccupancyAssessor()
        self.range_assessor = range_assessor or RotationActionRangeAssessor()
        self.target_assessor = target_assessor or RotationActionTargetAssessor()
        self.slot_assessor = slot_assessor or RotationActionSlotAssessor()
        self.ultimate_affordability_assessor = (
            ultimate_affordability_assessor or RotationUltimateAffordabilityAssessor()
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
        cooldown_requirements: tuple[RotationActionCooldownRequirement, ...] = (),
        occupancy_requirements: tuple[RotationActionOccupancyRequirement, ...] = (),
        range_requirements: tuple[RotationActionRangeRequirement, ...] = (),
        target_distance_windows: tuple[RotationTargetDistanceWindow, ...] = (),
        target_requirements: tuple[RotationActionTargetRequirement, ...] = (),
        target_state_windows: tuple[RotationTargetStateWindow, ...] = (),
        slot_requirements: tuple[RotationActionSlotRequirement, ...] = (),
        ultimate_affordability_requirement: RotationUltimateAffordabilityRequirement | None = None,
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
        cooldown_assessment = (
            self.cooldown_assessor.assess(candidate_plan, cooldown_requirements)
            if cooldown_requirements
            else None
        )
        occupancy_assessment = (
            self.occupancy_assessor.assess(candidate_plan, occupancy_requirements)
            if occupancy_requirements
            else None
        )
        range_assessment = (
            self.range_assessor.assess(
                candidate_plan,
                range_requirements,
                target_distance_windows,
            )
            if range_requirements and target_distance_windows
            else None
        )
        target_assessment = (
            self.target_assessor.assess(
                candidate_plan,
                target_requirements,
                target_state_windows,
            )
            if target_requirements and target_state_windows
            else None
        )
        slot_assessment = (
            self.slot_assessor.assess(candidate_plan, slot_requirements)
            if slot_requirements
            else None
        )
        ultimate_affordability_assessment = (
            self.ultimate_affordability_assessor.assess(
                candidate_plan,
                ultimate_affordability_requirement,
            )
            if ultimate_affordability_requirement is not None
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
            cooldown_assessment=cooldown_assessment,
            occupancy_assessment=occupancy_assessment,
            range_assessment=range_assessment,
            target_assessment=target_assessment,
            slot_assessment=slot_assessment,
            ultimate_affordability_assessment=ultimate_affordability_assessment,
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