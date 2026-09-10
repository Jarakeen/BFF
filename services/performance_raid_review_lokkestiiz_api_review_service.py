from __future__ import annotations

"""Application service for API-driven Lokkestiiz Raid Review.

The UI supplies a report code and selected fight IDs. This service resolves validated
pull requests from ESO Logs and then executes the existing Lokkestiiz session engine.
It does not own combat mechanics; it only composes intake and analysis services.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_lokkestiiz_api_intake_service import (
    PerformanceRaidReviewLokkestiizApiIntakeService,
)
from services.performance_raid_review_lokkestiiz_session_service import (
    LokkestiizRaidReviewSessionResult,
    PerformanceRaidReviewLokkestiizSessionService,
)


@dataclass(frozen=True, slots=True)
class LokkestiizRaidReviewApiReviewResult:
    session: LokkestiizRaidReviewSessionResult | None
    unresolved: tuple[str, ...] = ()

    @property
    def review(self):
        return self.session.review if self.session is not None else None


class PerformanceRaidReviewLokkestiizApiReviewService:
    """Run a Lokkestiiz review directly from one report and selected fight IDs."""

    def __init__(
        self,
        performance_service,
        *,
        intake_service: PerformanceRaidReviewLokkestiizApiIntakeService | None = None,
        session_service: PerformanceRaidReviewLokkestiizSessionService | None = None,
    ) -> None:
        self.performance_service = performance_service
        self.intake_service = intake_service or PerformanceRaidReviewLokkestiizApiIntakeService(
            performance_service
        )
        self.session_service = session_service or PerformanceRaidReviewLokkestiizSessionService(
            performance_service
        )

    def review_report(
        self,
        report_code: str,
        fight_ids: Iterable[int],
    ) -> LokkestiizRaidReviewApiReviewResult:
        intake = self.intake_service.build(report_code, tuple(fight_ids))
        if not intake.pulls:
            return LokkestiizRaidReviewApiReviewResult(
                session=None,
                unresolved=tuple(intake.unresolved),
            )

        session = self.session_service.review(intake.pulls)
        unresolved = tuple(
            dict.fromkeys((*intake.unresolved, *tuple(session.unresolved or ())))
        )
        return LokkestiizRaidReviewApiReviewResult(
            session=session,
            unresolved=unresolved,
        )


__all__ = [
    "LokkestiizRaidReviewApiReviewResult",
    "PerformanceRaidReviewLokkestiizApiReviewService",
]
