from __future__ import annotations

"""Settings-backed application runner for API-driven Lokkestiiz Raid Review.

UI code supplies only a report code/URL and selected fight IDs. This service owns
credential loading and application-service construction, while the underlying review
service continues to own no UI state.
"""

from pathlib import Path
from typing import Iterable

from services.esologs_client import EsoLogsClient
from services.performance_dashboard_service import PerformanceDashboardService
from services.performance_raid_review_lokkestiiz_api_review_service import (
    LokkestiizRaidReviewApiReviewResult,
    PerformanceRaidReviewLokkestiizApiReviewService,
)
from services.settings_service import SettingsService


class PerformanceRaidReviewLokkestiizRunnerService:
    def __init__(
        self,
        settings_service: SettingsService | None = None,
        *,
        review_service_factory=None,
    ) -> None:
        self.settings_service = settings_service or SettingsService(Path("settings.json"))
        self.review_service_factory = review_service_factory or self._build_review_service

    def review_report(
        self,
        report_code: str,
        fight_ids: Iterable[int],
    ) -> LokkestiizRaidReviewApiReviewResult:
        service = self.review_service_factory()
        return service.review_report(report_code, tuple(int(value) for value in fight_ids))

    def _build_review_service(self) -> PerformanceRaidReviewLokkestiizApiReviewService:
        settings = self.settings_service.load()
        client = EsoLogsClient(
            client_id=settings.get("EsoLogsClientId", ""),
            client_secret=settings.get("EsoLogsClientSecret", ""),
        )
        performance_service = PerformanceDashboardService(client)
        return PerformanceRaidReviewLokkestiizApiReviewService(performance_service)


__all__ = ["PerformanceRaidReviewLokkestiizRunnerService"]
