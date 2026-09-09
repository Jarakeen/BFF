from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from services.team_provider_rotation_workload_service import TeamProviderRotationWorkload
from services.team_provider_workload_candidate_service import (
    TeamProviderWorkloadCandidateRejection,
    TeamProviderWorkloadCandidateResult,
)
from services.team_provider_workload_frontier_service import (
    TeamProviderWorkloadDominance,
    TeamProviderWorkloadFrontierService,
)


class TeamProviderWorkloadDecisionStatus(str, Enum):
    FRONTIER = "frontier"
    DOMINATED = "dominated"
    BLOCKED = "blocked"
    REJECTED = "rejected"


@dataclass(frozen=True)
class TeamProviderWorkloadDecision:
    alternative_id: str
    effect_key: str
    duration_seconds: float | None
    status: TeamProviderWorkloadDecisionStatus
    workload: TeamProviderRotationWorkload | None = None
    blockers: tuple[str, ...] = ()
    dominated_by: tuple[str, ...] = ()
    improvements: tuple[str, ...] = ()


@dataclass(frozen=True)
class TeamProviderWorkloadDecisionResult:
    decisions: tuple[TeamProviderWorkloadDecision, ...]

    @property
    def frontier(self) -> tuple[TeamProviderWorkloadDecision, ...]:
        return tuple(
            item
            for item in self.decisions
            if item.status is TeamProviderWorkloadDecisionStatus.FRONTIER
        )

    @property
    def dominated(self) -> tuple[TeamProviderWorkloadDecision, ...]:
        return tuple(
            item
            for item in self.decisions
            if item.status is TeamProviderWorkloadDecisionStatus.DOMINATED
        )

    @property
    def blocked(self) -> tuple[TeamProviderWorkloadDecision, ...]:
        return tuple(
            item
            for item in self.decisions
            if item.status
            in {
                TeamProviderWorkloadDecisionStatus.BLOCKED,
                TeamProviderWorkloadDecisionStatus.REJECTED,
            }
        )


class TeamProviderWorkloadDecisionService:
    """Classify projected provider candidates without inventing encounter policy.

    Candidate batches may contain several effects or comparison horizons. Frontier
    evaluation therefore happens independently inside each exact ``effect_key`` +
    ``duration_seconds`` scope. Projection failures remain distinct from projected
    workloads that later fail recipient/temporal/unresolved workload gates.
    """

    @classmethod
    def analyze(
        cls,
        result: TeamProviderWorkloadCandidateResult,
    ) -> TeamProviderWorkloadDecisionResult:
        groups: dict[tuple[str, float], list[TeamProviderRotationWorkload]] = {}
        for workload in result.workloads:
            groups.setdefault(
                (workload.effect_key, float(workload.duration_seconds)), []
            ).append(workload)

        decisions: list[TeamProviderWorkloadDecision] = []
        for key in sorted(groups):
            workloads = tuple(groups[key])
            frontier = TeamProviderWorkloadFrontierService.evaluate(workloads)
            dominance_by_dominated = cls._dominance_by_dominated(frontier.dominance)

            frontier_ids = {item.alternative_id for item in frontier.frontier}
            dominated_ids = {item.alternative_id for item in frontier.dominated}
            blocked_ids = {item.alternative_id for item in frontier.blocked}

            for workload in workloads:
                if workload.alternative_id in frontier_ids:
                    status = TeamProviderWorkloadDecisionStatus.FRONTIER
                    dominated_by: tuple[str, ...] = ()
                    improvements: tuple[str, ...] = ()
                    blockers: tuple[str, ...] = ()
                elif workload.alternative_id in dominated_ids:
                    status = TeamProviderWorkloadDecisionStatus.DOMINATED
                    relations = dominance_by_dominated.get(workload.alternative_id, ())
                    dominated_by = tuple(
                        dict.fromkeys(item.preferred_id for item in relations)
                    )
                    improvements = tuple(
                        dict.fromkeys(
                            detail
                            for item in relations
                            for detail in item.improvements
                        )
                    )
                    blockers = ()
                elif workload.alternative_id in blocked_ids:
                    status = TeamProviderWorkloadDecisionStatus.BLOCKED
                    dominated_by = ()
                    improvements = ()
                    blockers = workload.unresolved or cls._coverage_blockers(workload)
                else:
                    raise RuntimeError(
                        f"provider workload was not classified: {workload.alternative_id}"
                    )

                decisions.append(
                    TeamProviderWorkloadDecision(
                        alternative_id=workload.alternative_id,
                        effect_key=workload.effect_key,
                        duration_seconds=workload.duration_seconds,
                        status=status,
                        workload=workload,
                        blockers=blockers,
                        dominated_by=dominated_by,
                        improvements=improvements,
                    )
                )

        decisions.extend(cls._rejection_decision(item) for item in result.rejected)
        return TeamProviderWorkloadDecisionResult(decisions=tuple(decisions))

    @staticmethod
    def _dominance_by_dominated(
        dominance: tuple[TeamProviderWorkloadDominance, ...],
    ) -> dict[str, tuple[TeamProviderWorkloadDominance, ...]]:
        grouped: dict[str, list[TeamProviderWorkloadDominance]] = {}
        for item in dominance:
            grouped.setdefault(item.dominated_id, []).append(item)
        return {
            key: tuple(sorted(items, key=lambda relation: relation.preferred_id))
            for key, items in grouped.items()
        }

    @staticmethod
    def _coverage_blockers(
        workload: TeamProviderRotationWorkload,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not workload.recipient_coverage_met:
            blockers.append("recipient coverage requirement is not met")
        if not workload.temporal_coverage_met:
            blockers.append("temporal coverage requirement is not met")
        return tuple(blockers)

    @staticmethod
    def _rejection_decision(
        rejection: TeamProviderWorkloadCandidateRejection,
    ) -> TeamProviderWorkloadDecision:
        return TeamProviderWorkloadDecision(
            alternative_id=rejection.alternative_id,
            effect_key=rejection.effect_key,
            duration_seconds=None,
            status=TeamProviderWorkloadDecisionStatus.REJECTED,
            blockers=rejection.blockers,
        )


__all__ = [
    "TeamProviderWorkloadDecision",
    "TeamProviderWorkloadDecisionResult",
    "TeamProviderWorkloadDecisionService",
    "TeamProviderWorkloadDecisionStatus",
]
