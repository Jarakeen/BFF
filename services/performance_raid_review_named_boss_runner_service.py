from __future__ import annotations

"""Settings-backed baseline Raid Review runner for named ESO Logs encounters.

This service intentionally owns no encounter-specific mechanic model. It provides the
shared cross-pull Raid Review baseline for any explicitly named boss by resolving the
selected fight rosters through ESO Logs and delegating observations/analysis to the
canonical PerformanceRaidReviewCoordinatorService.

Encounter adapters may layer reviewed mechanic-specific evidence on top of this
baseline later. Until then, this runner must not invent mechanic windows, boss actor
identity, or encounter-specific obligations.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from services.esologs_client import EsoLogsClient
from services.performance_dashboard_service import PerformanceDashboardService
from services.performance_raid_review_coordinator_service import (
    PerformanceRaidReviewCoordinatorService,
    PerformanceRaidReviewResult,
)
from services.performance_raid_review_observation_service import RaidReviewSource
from services.settings_service import SettingsService


@dataclass(frozen=True, slots=True)
class NamedBossRaidReviewFightChoice:
    fight_id: int
    kill: bool
    boss_percentage: float | None = None
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class NamedBossRaidReviewResult:
    review: PerformanceRaidReviewResult | None
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewNamedBossRunnerService:
    """Run the shared Raid Review baseline for one explicitly named encounter."""

    def __init__(
        self,
        boss_name: str,
        settings_service: SettingsService | None = None,
        *,
        performance_service_factory=None,
        coordinator_factory=None,
    ) -> None:
        normalized_name = str(boss_name or "").strip()
        if not normalized_name:
            raise ValueError("Named-boss Raid Review requires a non-empty boss name.")
        self.boss_name = normalized_name
        self.settings_service = settings_service or SettingsService(Path("settings.json"))
        self.performance_service_factory = (
            performance_service_factory or self._build_performance_service
        )
        self.coordinator_factory = coordinator_factory or PerformanceRaidReviewCoordinatorService

    def list_fights(self, report_code: str) -> tuple[NamedBossRaidReviewFightChoice, ...]:
        performance_service = self.performance_service_factory()
        client = performance_service.client
        code = client.normalize_report_code(report_code)
        if not code:
            raise ValueError("Raid Review requires an ESO Logs report code or report URL.")

        choices: list[NamedBossRaidReviewFightChoice] = []
        for fight in client.get_fights(code):
            if str(fight.get("name") or "").strip().casefold() != self.boss_name.casefold():
                continue
            fight_id = int(fight.get("id") or 0)
            if fight_id <= 0:
                continue

            start_time = float(fight.get("startTime") or 0.0)
            end_time = float(fight.get("endTime") or 0.0)
            raw_pct = fight.get("bossPercentage")
            boss_percentage = None
            if raw_pct is not None:
                try:
                    boss_percentage = float(raw_pct)
                except (TypeError, ValueError):
                    boss_percentage = None

            choices.append(
                NamedBossRaidReviewFightChoice(
                    fight_id=fight_id,
                    kill=bool(fight.get("kill")),
                    boss_percentage=boss_percentage,
                    duration_seconds=max(0.0, (end_time - start_time) / 1000.0),
                )
            )

        choices.sort(key=lambda row: row.fight_id)
        return tuple(choices)

    def review_report(
        self,
        report_code: str,
        fight_ids: Iterable[int],
    ) -> NamedBossRaidReviewResult:
        performance_service = self.performance_service_factory()
        client = performance_service.client
        code = client.normalize_report_code(report_code)
        if not code:
            return NamedBossRaidReviewResult(
                review=None,
                unresolved=("Raid Review requires an ESO Logs report code or report URL.",),
            )

        requested_ids = tuple(
            dict.fromkeys(int(value) for value in fight_ids if int(value) > 0)
        )
        if not requested_ids:
            return NamedBossRaidReviewResult(
                review=None,
                unresolved=(f"No positive fight IDs were selected from report {code}.",),
            )

        sources: list[RaidReviewSource] = []
        unresolved: list[str] = []
        for fight_id in requested_ids:
            try:
                fight = client.get_fight(code, fight_id)
            except Exception as exc:
                unresolved.append(f"Could not load report {code} fight #{fight_id}: {exc}")
                continue

            fight_name = str(fight.get("name") or "").strip()
            if fight_name.casefold() != self.boss_name.casefold():
                unresolved.append(
                    f"Report {code} fight #{fight_id} is {fight_name or 'unnamed'}, not {self.boss_name}; pull was skipped."
                )
                continue

            try:
                _summary, actors = performance_service.list_actors(code, fight_id)
            except Exception as exc:
                unresolved.append(
                    f"Could not resolve player roster for report {code} fight #{fight_id}: {exc}"
                )
                continue

            fight_sources = tuple(
                RaidReviewSource(
                    report_code=code,
                    fight_id=fight_id,
                    actor_id=int(actor.ActorId),
                    actor_label=str(actor.Label),
                    role=str(actor.Role),
                    member_key=f"{code.casefold()}:{int(actor.ActorId)}",
                )
                for actor in actors
                if int(actor.ActorId) > 0
            )
            if not fight_sources:
                unresolved.append(
                    f"No friendly player actors were resolved for report {code} fight #{fight_id}."
                )
                continue
            sources.extend(fight_sources)

        if not sources:
            return NamedBossRaidReviewResult(
                review=None,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        coordinator = self.coordinator_factory(performance_service)
        review = coordinator.review(tuple(sources), encounter_name=self.boss_name)
        all_unresolved = tuple(
            dict.fromkeys((*unresolved, *tuple(getattr(review, "unresolved", ()) or ())))
        )
        return NamedBossRaidReviewResult(review=review, unresolved=all_unresolved)

    def _build_performance_service(self) -> PerformanceDashboardService:
        settings = self.settings_service.load()
        client = EsoLogsClient(
            client_id=settings.get("EsoLogsClientId", ""),
            client_secret=settings.get("EsoLogsClientSecret", ""),
        )
        return PerformanceDashboardService(client)


__all__ = [
    "NamedBossRaidReviewFightChoice",
    "NamedBossRaidReviewResult",
    "PerformanceRaidReviewNamedBossRunnerService",
]
