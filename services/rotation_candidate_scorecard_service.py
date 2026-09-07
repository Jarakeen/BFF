from __future__ import annotations

from dataclasses import dataclass

from minmax.encounter_requirements import EncounterRequirementSet
from minmax.rotation_demand_window import RotationDemandWindow
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.support_coverage import SupportCoverage
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationPlanConsequenceService,
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
    unresolved: tuple[str, ...]

    @property
    def missing_demand_requirements(self) -> tuple[RotationDemandActionRequirement, ...]:
        return tuple(item.requirement for item in self.demand_coverage if not item.satisfied)

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
            and self.candidate_shortfall == 0
        )


class RotationCandidateScorecardService:
    """Combine resource consequences with explicit encounter obligation evidence.

    The scorecard intentionally does not assign weights or choose a winner. Demand
    coverage is based only on exact caller-supplied action requirements. Required
    support effects use the existing static SupportCoverage model and therefore do
    not claim runtime uptime unless a later layer proves it.
    """

    def __init__(
        self,
        consequence_service: RotationPlanConsequenceService | None = None,
    ) -> None:
        self.consequence_service = consequence_service or RotationPlanConsequenceService()

    def compare(
        self,
        *,
        baseline_plan: RotationPlan,
        candidate_plan: RotationPlan,
        baseline_sustain: RotationSustainProjection,
        candidate_sustain: RotationSustainProjection,
        demands: tuple[RotationDemandWindow, ...] = (),
        demand_requirements: tuple[RotationDemandActionRequirement, ...] = (),
        encounter_requirements: EncounterRequirementSet | None = None,
        support_coverage: SupportCoverage | None = None,
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

        if (encounter_requirements is None) != (support_coverage is None):
            raise ValueError(
                "static required-effect coverage requires both encounter_requirements and support_coverage"
            )
        missing_effects: tuple[str, ...] = ()
        if encounter_requirements is not None and support_coverage is not None:
            missing_effects = support_coverage.missing_from(
                encounter_requirements.required_effect_names()
            )

        consequence = self.consequence_service.compare(
            baseline_plan=baseline_plan,
            candidate_plan=candidate_plan,
            baseline_sustain=baseline_sustain,
            candidate_sustain=candidate_sustain,
        )
        unresolved = self._dedupe(
            tuple(candidate_plan.unresolved) + tuple(candidate_sustain.unresolved)
        )

        return RotationCandidateScorecard(
            consequence=consequence,
            demand_coverage=tuple(coverage),
            missing_required_effects=missing_effects,
            candidate_shortfall=int(candidate_sustain.run.timeline.total_shortfall),
            unresolved=unresolved,
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
