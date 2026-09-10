from __future__ import annotations

"""Compare whether reviewed landing-recovery obligations were completed at all.

Timing and completion are separate evidence questions.  The existing landing-recovery
analysis compares delay when a matching action was observed.  This service keeps the
opportunity denominator explicit so missing recovery actions are not silently dropped.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_landing_recovery_analysis_service import RaidReviewPullOutcome
from services.performance_raid_review_landing_recovery_service import RaidReviewLandingRecoveryObservation
from services.performance_raid_review_service import RaidReviewFinding


@dataclass(frozen=True, slots=True)
class RaidReviewRecoveryOpportunity:
    report_code: str
    fight_id: int
    occurrence: int
    actor_id: int
    actor_label: str
    role: str
    member_key: str
    signal_semantic_key: str
    signal_label: str

    @property
    def pull_key(self) -> tuple[str, int]:
        return (str(self.report_code), int(self.fight_id))

    @property
    def stable_member_key(self) -> str:
        explicit = str(self.member_key or "").strip().casefold()
        return explicit or f"{str(self.report_code).strip().casefold()}:{int(self.actor_id)}"

    @property
    def completion_key(self) -> tuple[str, int, int, int, str]:
        return (
            str(self.report_code),
            int(self.fight_id),
            int(self.occurrence),
            int(self.actor_id),
            str(self.signal_semantic_key),
        )


class PerformanceRaidReviewLandingRecoveryCompletionAnalysisService:
    """Turn repeated completed/missed recovery opportunities into coaching findings."""

    def findings(
        self,
        opportunities: Iterable[RaidReviewRecoveryOpportunity],
        observations: Iterable[RaidReviewLandingRecoveryObservation],
        outcomes: Iterable[RaidReviewPullOutcome],
        *,
        minimum_opportunities_per_outcome: int = 2,
        minimum_rate_delta: float = 0.25,
    ) -> tuple[RaidReviewFinding, ...]:
        chances = tuple(opportunities)
        if not chances:
            return ()

        completed = {
            (
                str(row.report_code),
                int(row.fight_id),
                int(row.occurrence),
                int(row.actor_id),
                str(row.signal_semantic_key),
            )
            for row in observations
        }
        outcome_by_pull = {row.pull_key: bool(row.kill) for row in outcomes}
        groups: dict[tuple[str, str], list[RaidReviewRecoveryOpportunity]] = {}
        for row in chances:
            if row.pull_key not in outcome_by_pull:
                continue
            groups.setdefault((row.stable_member_key, row.signal_semantic_key), []).append(row)

        minimum = max(1, int(minimum_opportunities_per_outcome))
        threshold = max(0.0, float(minimum_rate_delta))
        findings: list[RaidReviewFinding] = []

        for group in groups.values():
            sample = group[0]
            kills = [row for row in group if outcome_by_pull[row.pull_key] is True]
            wipes = [row for row in group if outcome_by_pull[row.pull_key] is False]
            if len(kills) < minimum or len(wipes) < minimum:
                continue

            kill_done = sum(1 for row in kills if row.completion_key in completed)
            wipe_done = sum(1 for row in wipes if row.completion_key in completed)
            kill_rate = kill_done / len(kills)
            wipe_rate = wipe_done / len(wipes)
            delta = wipe_rate - kill_rate
            if abs(delta) < threshold:
                continue

            label = str(sample.signal_label or sample.signal_semantic_key)
            worse_on_wipes = delta < 0
            findings.append(
                RaidReviewFinding(
                    scope="player",
                    subject=sample.actor_label,
                    role=sample.role,
                    category="landing_recovery_completion",
                    priority="medium" if worse_on_wipes else "note",
                    title=(
                        f"{label} is missed more often on wipe pulls"
                        if worse_on_wipes
                        else f"{label} completion is not a wipe-side weakness"
                    ),
                    evidence=(
                        f"Observed within the reviewed recovery window on {kill_done}/{len(kills)} kill "
                        f"opportunities ({kill_rate * 100:.0f}%) vs {wipe_done}/{len(wipes)} wipe "
                        f"opportunities ({wipe_rate * 100:.0f}%)."
                    ),
                    recommendation=(
                        "Inspect the missed landing windows for movement, target reacquisition, deaths, "
                        "assignment conflicts, and queued actions before changing the base rotation."
                        if worse_on_wipes
                        else "Do not prioritize this recovery obligation; wipe pulls complete it at least as consistently as kills."
                    ),
                    confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                )
            )

        order = {"high": 0, "medium": 1, "note": 2}
        return tuple(sorted(findings, key=lambda row: (order.get(row.priority, 9), row.subject.casefold(), row.title.casefold())))


__all__ = [
    "PerformanceRaidReviewLandingRecoveryCompletionAnalysisService",
    "RaidReviewRecoveryOpportunity",
]
