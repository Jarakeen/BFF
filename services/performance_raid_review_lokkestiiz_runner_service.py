from __future__ import annotations

"""Settings-backed application runner for API-driven Lokkestiiz Raid Review.

UI code supplies only a report code/URL and selected fight IDs. This service owns
credential loading and application-service construction, while the underlying review
service continues to own no UI state.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from services.esologs_client import EsoLogsClient
from services.performance_dashboard_service import PerformanceDashboardService
from services.performance_raid_review_lokkestiiz_api_review_service import (
    LokkestiizRaidReviewApiReviewResult,
    PerformanceRaidReviewLokkestiizApiReviewService,
)
from services.settings_service import SettingsService


@dataclass(frozen=True, slots=True)
class LokkestiizRaidReviewFightChoice:
    fight_id: int
    kill: bool
    boss_percentage: float | None = None
    duration_seconds: float = 0.0


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

    def list_lokkestiiz_fights(
        self,
        report_code: str,
    ) -> tuple[LokkestiizRaidReviewFightChoice, ...]:
        """Return selectable Lokkestiiz pulls from one report without running analysis."""
        service = self.review_service_factory()
        client = service.performance_service.client
        code = client.normalize_report_code(report_code)
        fights = client.get_fights(code)

        choices: list[LokkestiizRaidReviewFightChoice] = []
        for fight in fights:
            if str(fight.get("name") or "").strip().casefold() != "lokkestiiz":
                continue
            fight_id = int(fight.get("id") or 0)
            if fight_id <= 0:
                continue

            start_time = float(fight.get("startTime") or 0.0)
            end_time = float(fight.get("endTime") or 0.0)
            duration_seconds = max(0.0, (end_time - start_time) / 1000.0)

            raw_pct = fight.get("bossPercentage")
            boss_percentage = None
            if raw_pct is not None:
                try:
                    boss_percentage = float(raw_pct)
                except (TypeError, ValueError):
                    boss_percentage = None

            choices.append(
                LokkestiizRaidReviewFightChoice(
                    fight_id=fight_id,
                    kill=bool(fight.get("kill")),
                    boss_percentage=boss_percentage,
                    duration_seconds=duration_seconds,
                )
            )

        choices.sort(key=lambda row: row.fight_id)
        return tuple(choices)

    def _build_review_service(self) -> PerformanceRaidReviewLokkestiizApiReviewService:
        settings = self.settings_service.load()
        client = EsoLogsClient(
            client_id=settings.get("EsoLogsClientId", ""),
            client_secret=settings.get("EsoLogsClientSecret", ""),
        )
        performance_service = PerformanceDashboardService(client)
        return PerformanceRaidReviewLokkestiizApiReviewService(performance_service)


__all__ = [
    "LokkestiizRaidReviewFightChoice",
    "PerformanceRaidReviewLokkestiizRunnerService",
]
