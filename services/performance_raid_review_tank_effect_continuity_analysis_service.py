from __future__ import annotations

"""Interpret reviewed tank effect continuity across kills and wipes.

This layer compares already-measured eligible-time coverage. It does not infer aura
lifetimes, assignment ownership, encounter eligibility, or a universal target uptime.
Those remain explicit upstream inputs.
"""

from statistics import median
from typing import Iterable

from services.performance_raid_review_landing_recovery_analysis_service import RaidReviewPullOutcome
from services.performance_raid_review_service import RaidReviewFinding
from services.performance_raid_review_tank_effect_continuity_service import (
    RaidReviewTankEffectContinuityObservation,
)


class PerformanceRaidReviewTankEffectContinuityAnalysisService:
    """Create cross-pull tank findings from reviewed effect coverage evidence."""

    def findings(
        self,
        observations: Iterable[RaidReviewTankEffectContinuityObservation],
        outcomes: Iterable[RaidReviewPullOutcome],
        *,
        minimum_coverage_delta_points: float = 10.0,
    ) -> tuple[RaidReviewFinding, ...]:
        rows = tuple(observations)
        outcome_by_pull = {item.pull_key: bool(item.kill) for item in outcomes}
        if not rows or not outcome_by_pull:
            return ()

        groups: dict[tuple[str, str], list[RaidReviewTankEffectContinuityObservation]] = {}
        for row in rows:
            member_key = str(row.member_key or "").strip().casefold()
            if not member_key:
                member_key = f"{str(row.report_code).strip().casefold()}:{int(row.actor_id)}"
            groups.setdefault((member_key, row.requirement_semantic_key), []).append(row)

        threshold = max(0.0, float(minimum_coverage_delta_points))
        findings: list[RaidReviewFinding] = []

        for group in groups.values():
            kills = [
                row for row in group
                if outcome_by_pull.get((str(row.report_code), int(row.fight_id))) is True
            ]
            wipes = [
                row for row in group
                if outcome_by_pull.get((str(row.report_code), int(row.fight_id))) is False
            ]
            if len(kills) < 2 or len(wipes) < 2:
                continue

            kill_median = median(row.coverage_percent for row in kills)
            wipe_median = median(row.coverage_percent for row in wipes)
            delta = wipe_median - kill_median
            if abs(delta) < threshold:
                continue

            sample = group[0]
            weaker_on_wipes = delta < 0
            findings.append(
                RaidReviewFinding(
                    scope="player",
                    subject=sample.actor_label,
                    role="Tank",
                    category="tank_effect_continuity",
                    priority="medium" if weaker_on_wipes else "note",
                    title=(
                        f"{sample.requirement_label} coverage is weaker on wipe pulls"
                        if weaker_on_wipes
                        else f"{sample.requirement_label} coverage is not a wipe-side weakness"
                    ),
                    evidence=(
                        f"Median eligible-time coverage: kills {kill_median:.1f}% vs wipes "
                        f"{wipe_median:.1f}% ({delta:+.1f} points), from {len(kills)} kill and "
                        f"{len(wipes)} wipe pulls."
                    ),
                    recommendation=(
                        "Inspect the uncovered eligible windows against positioning, target swaps, deaths, "
                        "resource pressure, and assignment conflicts before changing the tank build or rotation."
                        if weaker_on_wipes
                        else "Do not prioritize this assigned effect from these pulls; wipe-side coverage is at least as strong as on kills."
                    ),
                    confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                )
            )

        order = {"high": 0, "medium": 1, "note": 2}
        return tuple(
            sorted(
                findings,
                key=lambda item: (
                    order.get(item.priority, 9),
                    item.subject.casefold(),
                    item.title.casefold(),
                ),
            )
        )


__all__ = ["PerformanceRaidReviewTankEffectContinuityAnalysisService"]
