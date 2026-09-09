from __future__ import annotations

"""Production coordinator for fresh cross-pull raid review.

The coordinator is intentionally thin: collect fresh per-source observations,
optionally enrich them from raw ESO Logs events, run cross-pull analysis, and then
add findings from explicitly supplied reviewed mechanic windows. It does not persist
computed review state.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_esologs_event_provider import (
    PerformanceRaidReviewEsoLogsEventProvider,
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
from services.performance_raid_review_service import (
    PerformanceRaidReviewService,
    RaidReviewReport,
)


@dataclass(frozen=True, slots=True)
class PerformanceRaidReviewResult:
    report: RaidReviewReport
    collection: RaidReviewCollectionResult

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

    def review(
        self,
        sources: Iterable[RaidReviewSource],
        *,
        encounter_name: str | None = None,
        mechanic_windows: Iterable[RaidReviewEncounterWindow] = (),
    ) -> PerformanceRaidReviewResult:
        collection = self.observation_service.collect(tuple(sources))
        report = self.review_service.analyze(
            collection.observations,
            encounter_name=encounter_name,
        )

        window_findings = self.mechanic_window_service.findings(
            collection.observations,
            tuple(mechanic_windows),
        )
        if window_findings:
            priority_order = {"high": 0, "medium": 1, "note": 2}
            combined = tuple(
                sorted(
                    (*report.findings, *window_findings),
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
        )


__all__ = [
    "PerformanceRaidReviewCoordinatorService",
    "PerformanceRaidReviewResult",
]
