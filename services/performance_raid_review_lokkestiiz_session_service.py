from __future__ import annotations

"""Assemble one multi-pull Lokkestiiz raid review from shared runtime evidence.

This service deliberately does not own combat truth. It reuses the shared ESO Logs
fight-event provider, shared runtime effect-window projection, encounter-specific
per-pull evidence builder, and generic Raid Review coordinator. Its job is orchestration
only.
"""

from dataclasses import dataclass
from typing import Iterable

from services.esologs_runtime_effect_window_service import EsoLogsRuntimeEffectWindowService
from services.performance_raid_review_coordinator_service import (
    PerformanceRaidReviewCoordinatorService,
    PerformanceRaidReviewResult,
)
from services.performance_raid_review_esologs_event_provider import (
    PerformanceRaidReviewEsoLogsEventProvider,
)
from services.performance_raid_review_healer_effect_coverage_service import (
    PerformanceRaidReviewHealerEffectCoverageService,
    RaidReviewHealerEffectCoverageObservation,
    RaidReviewHealerEffectRequirement,
)
from services.performance_raid_review_landing_recovery_service import (
    RaidReviewRecoveryActor,
)
from services.performance_raid_review_lokkestiiz_pull_service import (
    LokkestiizPullRaidReviewEvidence,
    PerformanceRaidReviewLokkestiizPullService,
)
from services.performance_raid_review_observation_service import RaidReviewSource


@dataclass(frozen=True, slots=True)
class LokkestiizRaidReviewPullRequest:
    report_code: str
    fight_id: int
    boss_actor_id: int
    sources: tuple[RaidReviewSource, ...]
    evidence_source: str = "ESO Logs reviewed runtime evidence"


@dataclass(frozen=True, slots=True)
class LokkestiizRaidReviewSessionResult:
    review: PerformanceRaidReviewResult
    pull_evidence: tuple[LokkestiizPullRaidReviewEvidence, ...]
    healer_effect_coverage: tuple[RaidReviewHealerEffectCoverageObservation, ...] = ()
    unresolved: tuple[str, ...] = ()


class PerformanceRaidReviewLokkestiizSessionService:
    """Build a complete Lokkestiiz cross-pull review from explicit pull requests."""

    def __init__(
        self,
        performance_service,
        *,
        event_provider: PerformanceRaidReviewEsoLogsEventProvider | None = None,
        pull_service: PerformanceRaidReviewLokkestiizPullService | None = None,
        coordinator_service: PerformanceRaidReviewCoordinatorService | None = None,
        effect_window_service: EsoLogsRuntimeEffectWindowService | None = None,
        healer_effect_coverage_service: PerformanceRaidReviewHealerEffectCoverageService | None = None,
    ) -> None:
        self.performance_service = performance_service
        self.event_provider = event_provider or PerformanceRaidReviewEsoLogsEventProvider(
            performance_service.client
        )
        self.pull_service = pull_service or PerformanceRaidReviewLokkestiizPullService()
        self.coordinator_service = coordinator_service or PerformanceRaidReviewCoordinatorService(
            performance_service,
            event_provider=self.event_provider,
        )
        self.effect_window_service = effect_window_service or EsoLogsRuntimeEffectWindowService()
        self.healer_effect_coverage_service = (
            healer_effect_coverage_service or PerformanceRaidReviewHealerEffectCoverageService()
        )

    def review(
        self,
        pulls: Iterable[LokkestiizRaidReviewPullRequest],
        *,
        healer_effect_requirements: Iterable[RaidReviewHealerEffectRequirement] = (),
    ) -> LokkestiizRaidReviewSessionResult:
        requests = tuple(pulls)
        coverage_requirements = tuple(item for item in healer_effect_requirements if item.reviewed)
        reviewed_effect_names = tuple(
            dict.fromkeys(
                name
                for requirement in coverage_requirements
                for raw_name in requirement.effect_names
                if (name := str(raw_name or "").strip())
            )
        )
        if not requests:
            review = self.coordinator_service.review((), encounter_name="Lokkestiiz")
            return LokkestiizRaidReviewSessionResult(
                review=review,
                pull_evidence=(),
                healer_effect_coverage=(),
                unresolved=("No Lokkestiiz pulls were supplied for Raid Review.",),
            )

        all_sources: list[RaidReviewSource] = []
        mechanic_windows = []
        recovery_observations = []
        healer_effect_coverage: list[RaidReviewHealerEffectCoverageObservation] = []
        pull_evidence: list[LokkestiizPullRaidReviewEvidence] = []
        unresolved: list[str] = []

        for request in requests:
            report_code = str(request.report_code or "").strip()
            fight_id = int(request.fight_id)
            if not report_code or fight_id <= 0:
                unresolved.append(
                    f"Invalid Lokkestiiz pull request: report={report_code!r}, fight={fight_id}."
                )
                continue

            try:
                fight = self.performance_service.client.get_fight(report_code, fight_id)
            except Exception as exc:
                unresolved.append(
                    f"Could not load Lokkestiiz fight {report_code} #{fight_id}: {exc}"
                )
                continue

            fight_name = str(fight.get("name") or "").strip()
            if fight_name.casefold() != "lokkestiiz":
                unresolved.append(
                    f"Fight {report_code} #{fight_id} is {fight_name or 'unnamed'}, not Lokkestiiz; pull was skipped."
                )
                continue

            start = float(fight.get("startTime", 0.0) or 0.0)
            end = float(fight.get("endTime", 0.0) or 0.0)
            try:
                events = self.event_provider.events_for_fight(
                    report_code=report_code,
                    fight_id=fight_id,
                    start_time=start,
                    end_time=end,
                )
            except Exception as exc:
                unresolved.append(
                    f"Could not load complete Lokkestiiz runtime evidence for {report_code} #{fight_id}: {exc}"
                )
                continue

            sources = tuple(
                source
                for source in request.sources
                if source.report_code == report_code and int(source.fight_id) == fight_id
            )
            if not sources:
                unresolved.append(
                    f"No matching Raid Review sources were supplied for {report_code} #{fight_id}."
                )
                continue

            actors = tuple(
                RaidReviewRecoveryActor(
                    actor_id=int(source.actor_id),
                    actor_label=str(source.actor_label),
                    role=str(source.role),
                    member_key=str(source.member_key or ""),
                )
                for source in sources
            )

            evidence = self.pull_service.build(
                report_code=report_code,
                fight_id=fight_id,
                fight_start_time_ms=start,
                events=events,
                boss_actor_id=int(request.boss_actor_id),
                actors=actors,
                evidence_source=str(request.evidence_source or "ESO Logs reviewed runtime evidence"),
            )
            pull_evidence.append(evidence)
            all_sources.extend(sources)
            mechanic_windows.extend(evidence.mechanic_windows)
            recovery_observations.extend(evidence.recovery_observations)
            unresolved.extend(
                f"{report_code} #{fight_id}: {message}" for message in evidence.unresolved
            )

            if coverage_requirements:
                runtime_windows = self.effect_window_service.build(
                    events,
                    fight_start_time_ms=start,
                    effect_names=reviewed_effect_names,
                )
                unresolved.extend(
                    f"{report_code} #{fight_id}: {message}"
                    for message in runtime_windows.unresolved
                )
                coverage_result = self.healer_effect_coverage_service.evaluate(
                    effect_windows=runtime_windows.windows,
                    mechanic_windows=evidence.mechanic_windows,
                    requirements=coverage_requirements,
                )
                healer_effect_coverage.extend(coverage_result.observations)
                unresolved.extend(
                    f"{report_code} #{fight_id}: {message}"
                    for message in coverage_result.unresolved
                )

        review = self.coordinator_service.review(
            tuple(all_sources),
            encounter_name="Lokkestiiz",
            mechanic_windows=tuple(mechanic_windows),
            landing_recovery_observations=tuple(recovery_observations),
        )
        unresolved.extend(review.unresolved)

        return LokkestiizRaidReviewSessionResult(
            review=review,
            pull_evidence=tuple(pull_evidence),
            healer_effect_coverage=tuple(healer_effect_coverage),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "LokkestiizRaidReviewPullRequest",
    "LokkestiizRaidReviewSessionResult",
    "PerformanceRaidReviewLokkestiizSessionService",
]
