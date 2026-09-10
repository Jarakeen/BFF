from __future__ import annotations

"""Interpret measured DD boss-contact continuity across kills and wipes.

The input observations are already mechanic-adjusted and only measure silence between
consecutive positive boss-damage events in reviewed eligible time.  This layer compares
those observations across pull outcomes.  It does not reinterpret flight windows, infer
GCD cadence, or claim that damage-event silence proves a rotation error.
"""

from statistics import median
from typing import Iterable

from services.performance_raid_review_dd_ground_continuity_service import (
    RaidReviewDDGroundContinuityObservation,
)
from services.performance_raid_review_landing_recovery_analysis_service import RaidReviewPullOutcome
from services.performance_raid_review_service import RaidReviewFinding


class PerformanceRaidReviewDDGroundContinuityAnalysisService:
    """Create cross-pull findings from mechanic-adjusted DD boss-contact evidence."""

    def findings(
        self,
        observations: Iterable[RaidReviewDDGroundContinuityObservation],
        outcomes: Iterable[RaidReviewPullOutcome],
        *,
        minimum_longest_gap_delta_seconds: float = 1.0,
        minimum_gap_rate_delta: float = 0.10,
    ) -> tuple[RaidReviewFinding, ...]:
        rows = tuple(observations)
        outcome_by_pull = {item.pull_key: bool(item.kill) for item in outcomes}
        if not rows or not outcome_by_pull:
            return ()

        groups: dict[str, list[RaidReviewDDGroundContinuityObservation]] = {}
        for row in rows:
            member_key = str(row.member_key or "").strip().casefold()
            if not member_key:
                member_key = f"{row.report_code.strip().casefold()}:{int(row.actor_id)}"
            groups.setdefault(member_key, []).append(row)

        gap_threshold = max(0.0, float(minimum_longest_gap_delta_seconds))
        rate_threshold = max(0.0, float(minimum_gap_rate_delta))
        findings: list[RaidReviewFinding] = []

        for group in groups.values():
            kills = [
                row for row in group
                if outcome_by_pull.get((row.report_code, int(row.fight_id))) is True
            ]
            wipes = [
                row for row in group
                if outcome_by_pull.get((row.report_code, int(row.fight_id))) is False
            ]
            if len(kills) < 2 or len(wipes) < 2:
                continue

            kill_longest = median(row.longest_inactivity_seconds for row in kills)
            wipe_longest = median(row.longest_inactivity_seconds for row in wipes)
            longest_delta = wipe_longest - kill_longest

            kill_rate = median(self._gap_rate(row) for row in kills)
            wipe_rate = median(self._gap_rate(row) for row in wipes)
            rate_delta = wipe_rate - kill_rate

            wipes_weaker = longest_delta >= gap_threshold or rate_delta >= rate_threshold
            wipes_not_weaker = longest_delta <= -gap_threshold or rate_delta <= -rate_threshold
            if not wipes_weaker and not wipes_not_weaker:
                continue

            sample = group[0]
            evidence = (
                f"Median longest eligible boss-damage silence: kills {kill_longest:.2f}s vs "
                f"wipes {wipe_longest:.2f}s ({longest_delta:+.2f}s). Median long-gap share: "
                f"kills {kill_rate * 100:.0f}% vs wipes {wipe_rate * 100:.0f}% "
                f"({rate_delta * 100:+.0f} points), from {len(kills)} kill and {len(wipes)} wipe pulls."
            )

            if wipes_weaker:
                findings.append(
                    RaidReviewFinding(
                        scope="player",
                        subject=sample.actor_label,
                        role="DPS",
                        category="boss_contact",
                        priority="medium",
                        title="Boss-contact continuity is weaker on wipe pulls",
                        evidence=evidence,
                        recommendation=(
                            "Inspect the measured ground-phase silence windows against movement, mechanics, deaths, "
                            "target choice, and assignment load. Treat this as lost boss contact, not automatic proof "
                            "of a rotation problem; periodic effects can continue dealing damage while the player is not casting."
                        ),
                        confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                    )
                )
            else:
                findings.append(
                    RaidReviewFinding(
                        scope="player",
                        subject=sample.actor_label,
                        role="DPS",
                        category="boss_contact",
                        priority="note",
                        title="Boss-contact continuity is not a wipe-side weakness",
                        evidence=evidence,
                        recommendation=(
                            "Do not prioritize boss-contact continuity for this player from these pulls. Check deaths, "
                            "mechanic execution, target selection, burst alignment, and group timing before changing the base rotation."
                        ),
                        confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                    )
                )

        order = {"high": 0, "medium": 1, "note": 2}
        findings.sort(
            key=lambda item: (
                order.get(item.priority, 9),
                item.subject.casefold(),
                item.title.casefold(),
            )
        )
        return tuple(findings)

    @staticmethod
    def _gap_rate(row: RaidReviewDDGroundContinuityObservation) -> float:
        if row.measured_gap_count <= 0:
            return 0.0
        return row.inactivity_gap_count / row.measured_gap_count


__all__ = ["PerformanceRaidReviewDDGroundContinuityAnalysisService"]
