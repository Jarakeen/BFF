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
from services.performance_raid_review_dd_ground_continuity_service import (
    PerformanceRaidReviewDDGroundContinuityService,
    RaidReviewDDGroundContinuityObservation,
)
from services.performance_raid_review_esologs_event_provider import (
    PerformanceRaidReviewEsoLogsEventProvider,
)
from services.performance_raid_review_healer_effect_coverage_service import (
    PerformanceRaidReviewHealerEffectCoverageService,
    RaidReviewHealerEffectCoverageObservation,
    RaidReviewHealerEffectRequirement,
)
from services.performance_raid_review_landing_recovery_completion_analysis_service import (
    RaidReviewRecoveryOpportunity,
)
from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
    RaidReviewRecoveryActor,
    RaidReviewRecoverySignal,
)
from services.performance_raid_review_lokkestiiz_pull_service import (
    LokkestiizPullRaidReviewEvidence,
    PerformanceRaidReviewLokkestiizPullService,
)
from services.performance_raid_review_observation_service import RaidReviewSource
from services.performance_raid_review_tank_effect_continuity_service import (
    PerformanceRaidReviewTankEffectContinuityService,
    RaidReviewTankEffectContinuityObservation,
    RaidReviewTankEffectRequirement,
)
from services.performance_raid_review_tank_recovery_service import (
    PerformanceRaidReviewTankRecoveryService,
)


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
    landing_recovery_opportunities: tuple[RaidReviewRecoveryOpportunity, ...] = ()
    dd_ground_continuity: tuple[RaidReviewDDGroundContinuityObservation, ...] = ()
    tank_recovery_observations: tuple[RaidReviewLandingRecoveryObservation, ...] = ()
    tank_effect_continuity: tuple[RaidReviewTankEffectContinuityObservation, ...] = ()
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
        dd_ground_continuity_service: PerformanceRaidReviewDDGroundContinuityService | None = None,
        tank_recovery_service: PerformanceRaidReviewTankRecoveryService | None = None,
        tank_effect_continuity_service: PerformanceRaidReviewTankEffectContinuityService | None = None,
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
        self.dd_ground_continuity_service = (
            dd_ground_continuity_service or PerformanceRaidReviewDDGroundContinuityService()
        )
        self.tank_recovery_service = tank_recovery_service or PerformanceRaidReviewTankRecoveryService()
        self.tank_effect_continuity_service = (
            tank_effect_continuity_service or PerformanceRaidReviewTankEffectContinuityService()
        )

    def review(
        self,
        pulls: Iterable[LokkestiizRaidReviewPullRequest],
        *,
        healer_effect_requirements: Iterable[RaidReviewHealerEffectRequirement] = (),
        tank_recovery_signals: Iterable[RaidReviewRecoverySignal] = (),
        tank_effect_requirements: Iterable[RaidReviewTankEffectRequirement] = (),
        dd_inactivity_threshold_seconds: float = 3.0,
        tank_max_recovery_delay_seconds: float = 15.0,
    ) -> LokkestiizRaidReviewSessionResult:
        requests = tuple(pulls)
        coverage_requirements = tuple(item for item in healer_effect_requirements if item.reviewed)
        reviewed_tank_signals = tuple(
            signal
            for signal in tank_recovery_signals
            if signal.reviewed and self._is_tank(signal.role)
        )
        reviewed_tank_effects = tuple(item for item in tank_effect_requirements if item.reviewed)
        reviewed_effect_names = tuple(
            dict.fromkeys(
                name
                for requirement in (*coverage_requirements, *reviewed_tank_effects)
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
                landing_recovery_opportunities=(),
                dd_ground_continuity=(),
                tank_recovery_observations=(),
                tank_effect_continuity=(),
                unresolved=("No Lokkestiiz pulls were supplied for Raid Review.",),
            )

        all_sources: list[RaidReviewSource] = []
        mechanic_windows = []
        recovery_observations = []
        recovery_opportunities: list[RaidReviewRecoveryOpportunity] = []
        healer_effect_coverage: list[RaidReviewHealerEffectCoverageObservation] = []
        dd_ground_continuity: list[RaidReviewDDGroundContinuityObservation] = []
        tank_recovery_observations: list[RaidReviewLandingRecoveryObservation] = []
        tank_effect_continuity: list[RaidReviewTankEffectContinuityObservation] = []
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

            continuity_result = self.dd_ground_continuity_service.measure(
                report_code=report_code,
                fight_id=fight_id,
                fight_start_time_ms=start,
                fight_end_time_ms=end,
                events=events,
                boss_actor_id=int(request.boss_actor_id),
                actors=actors,
                excluded_mechanic_windows=evidence.mechanic_windows,
                inactivity_threshold_seconds=float(dd_inactivity_threshold_seconds),
            )
            dd_ground_continuity.extend(continuity_result.observations)
            unresolved.extend(
                f"{report_code} #{fight_id}: {message}"
                for message in continuity_result.unresolved
                if "No DPS actors were supplied" not in message
            )

            landing_boundaries = tuple(
                boundary
                for boundary in evidence.boundaries
                if boundary.fact_key == "aerial_onslaught_flight" and boundary.boundary == "end"
            )
            landing_occurrences = tuple(int(boundary.occurrence) for boundary in landing_boundaries)
            if landing_occurrences:
                for actor in actors:
                    if not self._is_dps(actor.role):
                        continue
                    for occurrence in landing_occurrences:
                        recovery_opportunities.append(
                            RaidReviewRecoveryOpportunity(
                                report_code=report_code,
                                fight_id=fight_id,
                                occurrence=occurrence,
                                actor_id=int(actor.actor_id),
                                actor_label=str(actor.actor_label),
                                role="DPS",
                                member_key=str(actor.member_key or ""),
                                signal_semantic_key="boss_damage_reacquisition_after_landing",
                                signal_label="Boss Damage Reacquisition",
                            )
                        )

            if reviewed_tank_signals and landing_boundaries:
                tank_result = self.tank_recovery_service.measure(
                    report_code=report_code,
                    fight_id=fight_id,
                    fight_start_time_ms=start,
                    events=events,
                    landing_boundaries=landing_boundaries,
                    actors=actors,
                    signals=reviewed_tank_signals,
                    boss_actor_id=int(request.boss_actor_id),
                    max_delay_seconds=float(tank_max_recovery_delay_seconds),
                )
                recovery_observations.extend(tank_result.observations)
                tank_recovery_observations.extend(tank_result.observations)
                recovery_opportunities.extend(tank_result.opportunities)
                unresolved.extend(
                    f"{report_code} #{fight_id}: {message}"
                    for message in tank_result.unresolved
                    if "No Tank actors were supplied" not in message
                )

            runtime_windows = None
            if reviewed_effect_names:
                runtime_windows = self.effect_window_service.build(
                    events,
                    fight_start_time_ms=start,
                    effect_names=reviewed_effect_names,
                )
                unresolved.extend(
                    f"{report_code} #{fight_id}: {message}"
                    for message in runtime_windows.unresolved
                )

            if coverage_requirements and runtime_windows is not None:
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

            if reviewed_tank_effects and runtime_windows is not None:
                tank_continuity_result = self.tank_effect_continuity_service.measure(
                    report_code=report_code,
                    fight_id=fight_id,
                    fight_duration_seconds=(end - start) / 1000.0,
                    effect_windows=runtime_windows.windows,
                    actors=actors,
                    requirements=reviewed_tank_effects,
                    excluded_mechanic_windows=evidence.mechanic_windows,
                )
                tank_effect_continuity.extend(tank_continuity_result.observations)
                unresolved.extend(
                    f"{report_code} #{fight_id}: {message}"
                    for message in tank_continuity_result.unresolved
                )

        review = self.coordinator_service.review(
            tuple(all_sources),
            encounter_name="Lokkestiiz",
            mechanic_windows=tuple(mechanic_windows),
            landing_recovery_observations=tuple(recovery_observations),
            landing_recovery_opportunities=tuple(recovery_opportunities),
            healer_effect_coverage_observations=tuple(healer_effect_coverage),
            dd_ground_continuity_observations=tuple(dd_ground_continuity),
            tank_effect_continuity_observations=tuple(tank_effect_continuity),
        )
        unresolved.extend(review.unresolved)

        return LokkestiizRaidReviewSessionResult(
            review=review,
            pull_evidence=tuple(pull_evidence),
            healer_effect_coverage=tuple(healer_effect_coverage),
            landing_recovery_opportunities=tuple(recovery_opportunities),
            dd_ground_continuity=tuple(dd_ground_continuity),
            tank_recovery_observations=tuple(tank_recovery_observations),
            tank_effect_continuity=tuple(tank_effect_continuity),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _is_dps(role: str) -> bool:
        return str(role or "").strip().casefold() in {
            "dps",
            "dd",
            "damage",
            "damage dealer",
            "damage_dealer",
        }

    @staticmethod
    def _is_tank(role: str) -> bool:
        return str(role or "").strip().casefold() in {"tank", "tanking"}


__all__ = [
    "LokkestiizRaidReviewPullRequest",
    "LokkestiizRaidReviewSessionResult",
    "PerformanceRaidReviewLokkestiizSessionService",
]
