from __future__ import annotations

"""Compare observed landing-recovery timing across successful and failed pulls.

Measurement and interpretation stay separate on purpose.  This service only turns
repeated, already-reviewed recovery observations into coaching findings.  It does not
invent mechanic timing, assign blame, or treat one slow cast as a causal verdict.
"""

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
)
from services.performance_raid_review_service import RaidReviewFinding


@dataclass(frozen=True, slots=True)
class RaidReviewPullOutcome:
    report_code: str
    fight_id: int
    kill: bool

    @property
    def pull_key(self) -> tuple[str, int]:
        return (str(self.report_code), int(self.fight_id))


class PerformanceRaidReviewLandingRecoveryAnalysisService:
    """Create evidence-backed coaching findings from landing-recovery observations."""

    def findings(
        self,
        observations: Iterable[RaidReviewLandingRecoveryObservation],
        outcomes: Iterable[RaidReviewPullOutcome],
        *,
        minimum_delta_seconds: float = 0.75,
    ) -> tuple[RaidReviewFinding, ...]:
        rows = tuple(observations)
        outcome_by_pull = {item.pull_key: bool(item.kill) for item in outcomes}
        if not rows or not outcome_by_pull:
            return ()

        groups: dict[tuple[str, str], list[RaidReviewLandingRecoveryObservation]] = {}
        for row in rows:
            member_key = str(row.member_key or "").strip().casefold()
            if not member_key:
                member_key = f"{row.report_code.strip().casefold()}:{int(row.actor_id)}"
            groups.setdefault((member_key, row.signal_semantic_key), []).append(row)

        threshold = max(0.0, float(minimum_delta_seconds))
        findings: list[RaidReviewFinding] = []

        for (_, signal_key), group in groups.items():
            kills = [
                row.delay_seconds
                for row in group
                if outcome_by_pull.get((row.report_code, int(row.fight_id))) is True
            ]
            wipes = [
                row.delay_seconds
                for row in group
                if outcome_by_pull.get((row.report_code, int(row.fight_id))) is False
            ]
            if len(kills) < 2 or len(wipes) < 2:
                continue

            kill_median = median(kills)
            wipe_median = median(wipes)
            delta = wipe_median - kill_median
            if abs(delta) < threshold:
                continue

            sample = group[0]
            slower_on_wipes = delta > 0
            role = sample.role
            label = sample.signal_label or signal_key
            title = (
                f"{label} is slower on wipe pulls"
                if slower_on_wipes
                else f"{label} timing is not a wipe-side weakness"
            )
            recommendation = (
                f"Review the landing sequence before changing the base build. {label} resumes "
                "later on wipe pulls, so check movement, target reacquisition, bar state, queued "
                "actions, and competing mechanic obligations around the landing."
                if slower_on_wipes
                else f"Do not prioritize speeding up {label}. Wipe pulls are recovering at least as "
                "quickly here; investigate other survival, mechanic, or group-timing signals first."
            )
            findings.append(
                RaidReviewFinding(
                    scope="player",
                    subject=sample.actor_label,
                    role=role,
                    category="landing_recovery",
                    priority="medium" if slower_on_wipes else "note",
                    title=title,
                    evidence=(
                        f"Median delay after observed landing: kills {kill_median:.2f}s vs wipes "
                        f"{wipe_median:.2f}s ({delta:+.2f}s), from {len(kills)} kill and "
                        f"{len(wipes)} wipe observations."
                    ),
                    recommendation=recommendation,
                    confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                )
            )

        priority_order = {"high": 0, "medium": 1, "note": 2}
        findings.sort(
            key=lambda item: (
                priority_order.get(item.priority, 9),
                item.subject.casefold(),
                item.title.casefold(),
            )
        )
        return tuple(findings)


__all__ = [
    "PerformanceRaidReviewLandingRecoveryAnalysisService",
    "RaidReviewPullOutcome",
]
