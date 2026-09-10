from __future__ import annotations

"""Production coordinator for fresh cross-pull raid review.

The coordinator is intentionally thin: collect fresh per-source observations,
optionally enrich them from raw ESO Logs events, run cross-pull analysis, and then
add findings from explicitly supplied reviewed mechanic windows, landing-recovery,
landing-recovery completion, healer pre-coverage, DD boss-contact continuity, and
DD output-context evidence. It does not persist computed review state.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_dd_ground_continuity_analysis_service import (
    PerformanceRaidReviewDDGroundContinuityAnalysisService,
)
from services.performance_raid_review_dd_ground_continuity_service import (
    RaidReviewDDGroundContinuityObservation,
)
from services.performance_raid_review_dd_output_context_service import (
    PerformanceRaidReviewDDOutputContextService,
)
from services.performance_raid_review_esologs_event_provider import (
    PerformanceRaidReviewEsoLogsEventProvider,
)
from services.performance_raid_review_healer_effect_coverage_analysis_service import (
    PerformanceRaidReviewHealerEffectCoverageAnalysisService,
)
from services.performance_raid_review_healer_effect_coverage_service import (
    RaidReviewHealerEffectCoverageObservation,
)
from services.performance_raid_review_landing_recovery_analysis_service import (
    PerformanceRaidReviewLandingRecoveryAnalysisService,
    RaidReviewPullOutcome,
)
from services.performance_raid_review_landing_recovery_completion_analysis_service import (
    PerformanceRaidReviewLandingRecoveryCompletionAnalysisService,
    RaidReviewRecoveryOpportunity,
)
from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
)
from services.performance_raid_review_mechanic_window_service import (
    PerformanceRaidReviewMechanicWindowService,
    RaidReviewEncounterWindow,
)
from services.performance_raid_review_observation_service import (
    PerformanceRaidReviewObservationService,
    RaidReviewCollectionResult,
    RaidReviewSource,
)
from services.performance_raid_review_priority_service import (
    PerformanceRaidReviewPriorityService,
    RaidReviewPriorityItem,
)
from services.performance_raid_review_service import (
    PerformanceRaidReviewService,
    RaidReviewReport,
)


@dataclass(frozen=True, slots=True)
class PerformanceRaidReviewResult:
    report: RaidReviewReport
    collection: RaidReviewCollectionResult
    priorities: tuple[RaidReviewPriorityItem, ...] = ()

    @property
    def unresolved(self) -> tuple[str, ...]:
        return self.collection.unresolved


class PerformanceRaidReviewCoordinatorService:
    """Build one evidence-backed raid review from explicit fresh ESO Logs sources."""

    def __init__(
        self,
        performance_service,
        *,
        observation_service: PerformanceRaidReviewObservationService | None = None,
        review_service: PerformanceRaidReviewService | None = None,
        event_provider: PerformanceRaidReviewEsoLogsEventProvider | None = None,
        mechanic_window_service: PerformanceRaidReviewMechanicWindowService | None = None,
        landing_recovery_analysis_service: PerformanceRaidReviewLandingRecoveryAnalysisService | None = None,
        landing_recovery_completion_analysis_service: PerformanceRaidReviewLandingRecoveryCompletionAnalysisService | None = None,
        healer_effect_coverage_analysis_service: PerformanceRaidReviewHealerEffectCoverageAnalysisService | None = None,
        dd_ground_continuity_analysis_service: PerformanceRaidReviewDDGroundContinuityAnalysisService | None = None,
        dd_output_context_service: PerformanceRaidReviewDDOutputContextService | None = None,
        priority_service: PerformanceRaidReviewPriorityService | None = None,
    ) -> None:
        self.performance_service = performance_service
        self.event_provider = event_provider or PerformanceRaidReviewEsoLogsEventProvider(
            performance_service.client
        )
        self.observation_service = observation_service or PerformanceRaidReviewObservationService(
            performance_service,
            enrichment_resolver=self.event_provider.resolve,
        )
        self.review_service = review_service or PerformanceRaidReviewService()
        self.mechanic_window_service = (
            mechanic_window_service or PerformanceRaidReviewMechanicWindowService()
        )
        self.landing_recovery_analysis_service = (
            landing_recovery_analysis_service or PerformanceRaidReviewLandingRecoveryAnalysisService()
        )
        self.landing_recovery_completion_analysis_service = (
            landing_recovery_completion_analysis_service
            or PerformanceRaidReviewLandingRecoveryCompletionAnalysisService()
        )
        self.healer_effect_coverage_analysis_service = (
            healer_effect_coverage_analysis_service
            or PerformanceRaidReviewHealerEffectCoverageAnalysisService()
        )
        self.dd_ground_continuity_analysis_service = (
            dd_ground_continuity_analysis_service
            or PerformanceRaidReviewDDGroundContinuityAnalysisService()
        )
        self.dd_output_context_service = (
            dd_output_context_service or PerformanceRaidReviewDDOutputContextService()
        )
        self.priority_service = priority_service or PerformanceRaidReviewPriorityService()

    def review(
        self,
        sources: Iterable[RaidReviewSource],
        *,
        encounter_name: str | None = None,
        mechanic_windows: Iterable[RaidReviewEncounterWindow] = (),
        landing_recovery_observations: Iterable[RaidReviewLandingRecoveryObservation] = (),
        landing_recovery_opportunities: Iterable[RaidReviewRecoveryOpportunity] = (),
        healer_effect_coverage_observations: Iterable[
            RaidReviewHealerEffectCoverageObservation
        ] = (),
        dd_ground_continuity_observations: Iterable[
            RaidReviewDDGroundContinuityObservation
        ] = (),
    ) -> PerformanceRaidReviewResult:
        collection = self.observation_service.collect(tuple(sources))
        report = self.review_service.analyze(
            collection.observations,
            encounter_name=encounter_name,
        )

        extra_findings = list(
            self.mechanic_window_service.findings(
                collection.observations,
                tuple(mechanic_windows),
            )
        )

        recovery_rows = tuple(landing_recovery_observations)
        opportunity_rows = tuple(landing_recovery_opportunities)
        continuity_rows = tuple(dd_ground_continuity_observations)
        if recovery_rows or opportunity_rows or continuity_rows:
            outcomes_by_pull: dict[tuple[str, int], RaidReviewPullOutcome] = {}
            for row in collection.observations:
                key = (str(row.report_code), int(row.fight_id))
                outcomes_by_pull[key] = RaidReviewPullOutcome(
                    report_code=key[0],
                    fight_id=key[1],
                    kill=bool(row.kill),
                )
            outcomes = tuple(outcomes_by_pull.values())
            if recovery_rows:
                extra_findings.extend(
                    self.landing_recovery_analysis_service.findings(
                        recovery_rows,
                        outcomes,
                    )
                )
            if opportunity_rows:
                extra_findings.extend(
                    self.landing_recovery_completion_analysis_service.findings(
                        opportunity_rows,
                        recovery_rows,
                        outcomes,
                    )
                )
            if continuity_rows:
                extra_findings.extend(
                    self.dd_ground_continuity_analysis_service.findings(
                        continuity_rows,
                        outcomes,
                    )
                )

        context_findings = self.dd_output_context_service.findings(
            collection.observations,
            continuity_observations=continuity_rows,
            recovery_opportunities=opportunity_rows,
            recovery_observations=recovery_rows,
        )
        extra_findings.extend(context_findings)

        coverage_rows = tuple(healer_effect_coverage_observations)
        if coverage_rows:
            extra_findings.extend(
                self.healer_effect_coverage_analysis_service.analyze(
                    coverage_rows,
                    collection.observations,
                )
            )

        if extra_findings:
            priority_order = {"high": 0, "medium": 1, "note": 2}
            combined = tuple(
                sorted(
                    (*report.findings, *extra_findings),
                    key=lambda item: (
                        priority_order.get(item.priority, 9),
                        item.scope,
                        item.subject.casefold(),
                        item.category,
                        item.title.casefold(),
                    ),
                )
            )
            report = RaidReviewReport(
                encounter_name=report.encounter_name,
                pull_count=report.pull_count,
                kill_count=report.kill_count,
                wipe_count=report.wipe_count,
                findings=combined,
            )

        return PerformanceRaidReviewResult(
            report=report,
            collection=collection,
            priorities=self.priority_service.rank(report.findings),
        )


__all__ = [
    "PerformanceRaidReviewCoordinatorService",
    "PerformanceRaidReviewResult",
]
