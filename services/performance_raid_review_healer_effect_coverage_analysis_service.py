from __future__ import annotations

"""Cross-pull interpretation for reviewed healer mechanic-start effect coverage.

The coverage evaluator owns the per-pull fact: whether reviewed effect evidence was
already active when a reviewed mechanic began.  This service compares those facts
across successful and failed pulls.  It does not infer causation from correlation and
it does not reconstruct missing aura evidence.
"""

from dataclasses import dataclass
from typing import Iterable

from services.performance_raid_review_healer_effect_coverage_service import (
    RaidReviewHealerEffectCoverageObservation,
)
from services.performance_raid_review_service import RaidReviewFinding, RaidReviewObservation


@dataclass(frozen=True, slots=True)
class _CoverageRow:
    coverage: RaidReviewHealerEffectCoverageObservation
    actor: RaidReviewObservation


class PerformanceRaidReviewHealerEffectCoverageAnalysisService:
    """Turn repeated healer pre-coverage evidence into cautious Raid Review findings."""

    def analyze(
        self,
        coverage_observations: Iterable[RaidReviewHealerEffectCoverageObservation],
        raid_observations: Iterable[RaidReviewObservation],
    ) -> tuple[RaidReviewFinding, ...]:
        observations = tuple(coverage_observations)
        raid_rows = tuple(raid_observations)
        if not observations or not raid_rows:
            return ()

        actors = {
            (row.report_code, int(row.fight_id), int(row.actor_id)): row
            for row in raid_rows
        }
        matched: list[_CoverageRow] = []
        for coverage in observations:
            if coverage.source_actor_id is None:
                continue
            actor = actors.get(
                (
                    coverage.report_code,
                    int(coverage.fight_id),
                    int(coverage.source_actor_id),
                )
            )
            if actor is None or actor.canonical_role != "Healer":
                continue
            matched.append(_CoverageRow(coverage=coverage, actor=actor))

        grouped: dict[tuple[str, str, str], list[_CoverageRow]] = {}
        for row in matched:
            key = (
                row.actor.stable_member_key,
                row.coverage.requirement_semantic_key,
                row.coverage.mechanic_semantic_key,
            )
            grouped.setdefault(key, []).append(row)

        findings: list[RaidReviewFinding] = []
        for rows in grouped.values():
            findings.extend(self._group_findings(rows))

        priority_order = {"high": 0, "medium": 1, "note": 2}
        findings.sort(
            key=lambda item: (
                priority_order.get(item.priority, 9),
                item.subject.casefold(),
                item.category,
                item.title.casefold(),
            )
        )
        return tuple(findings)

    @staticmethod
    def _group_findings(rows: list[_CoverageRow]) -> list[RaidReviewFinding]:
        if not rows:
            return []
        actor = rows[0].actor
        sample = rows[0].coverage
        kills = [row for row in rows if row.actor.kill]
        wipes = [row for row in rows if not row.actor.kill]
        kill_covered = sum(1 for row in kills if row.coverage.covered)
        wipe_covered = sum(1 for row in wipes if row.coverage.covered)
        findings: list[RaidReviewFinding] = []

        if len(kills) >= 2 and len(wipes) >= 2:
            kill_rate = kill_covered / len(kills)
            wipe_rate = wipe_covered / len(wipes)
            delta = kill_rate - wipe_rate
            if delta >= 0.25:
                findings.append(
                    RaidReviewFinding(
                        scope="player",
                        subject=actor.actor_label,
                        role="Healer",
                        category="mechanic_precoverage",
                        priority="medium",
                        title=f"{sample.requirement_label} is stronger on successful pulls",
                        evidence=(
                            f"At {sample.mechanic_label} start, reviewed pre-coverage was present on "
                            f"{kill_covered}/{len(kills)} kills ({kill_rate * 100:.0f}%) versus "
                            f"{wipe_covered}/{len(wipes)} wipes ({wipe_rate * 100:.0f}%)."
                        ),
                        recommendation=(
                            "Preserve the successful-pull timing and inspect the missed wipe windows for cast timing, "
                            "positioning, target coverage, or assignment conflicts. Treat this as a correlated execution "
                            "pattern, not proof that missing pre-coverage caused the wipe."
                        ),
                        confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                    )
                )
                return findings

            if wipe_rate - kill_rate >= 0.25:
                findings.append(
                    RaidReviewFinding(
                        scope="player",
                        subject=actor.actor_label,
                        role="Healer",
                        category="mechanic_precoverage",
                        priority="note",
                        title=f"{sample.requirement_label} is not the obvious wipe signal",
                        evidence=(
                            f"At {sample.mechanic_label} start, reviewed pre-coverage was present on "
                            f"{kill_covered}/{len(kills)} kills ({kill_rate * 100:.0f}%) versus "
                            f"{wipe_covered}/{len(wipes)} wipes ({wipe_rate * 100:.0f}%)."
                        ),
                        recommendation=(
                            "Do not ask for more of this effect based on wipe outcome alone. Check the rest of the mechanic "
                            "window, incoming damage, other support obligations, deaths, and positioning before changing the plan."
                        ),
                        confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                    )
                )
                return findings

        measured = len(rows)
        covered = sum(1 for row in rows if row.coverage.covered)
        if measured >= 3:
            rate = covered / measured
            if rate <= 0.5:
                findings.append(
                    RaidReviewFinding(
                        scope="player",
                        subject=actor.actor_label,
                        role="Healer",
                        category="mechanic_precoverage",
                        priority="medium",
                        title=f"{sample.requirement_label} is repeatedly missing at mechanic start",
                        evidence=(
                            f"Reviewed pre-coverage was present on {covered}/{measured} measured "
                            f"{sample.mechanic_label} starts ({rate * 100:.0f}%)."
                        ),
                        recommendation=(
                            "Review the exact mechanic-start timestamps against cast timing, movement, target coverage, "
                            "and assignment ownership. Missing observed coverage is a coaching lead, not automatic proof of a bad build or rotation."
                        ),
                        confidence="high" if measured >= 6 else "medium",
                    )
                )
            elif rate >= 0.8:
                findings.append(
                    RaidReviewFinding(
                        scope="player",
                        subject=actor.actor_label,
                        role="Healer",
                        category="mechanic_precoverage",
                        priority="note",
                        title=f"{sample.requirement_label} is consistently in place",
                        evidence=(
                            f"Reviewed pre-coverage was present on {covered}/{measured} measured "
                            f"{sample.mechanic_label} starts ({rate * 100:.0f}%)."
                        ),
                        recommendation=(
                            "Preserve this timing pattern. If the mechanic is still failing, investigate the rest of the "
                            "support stack, positioning, incoming damage, and player execution rather than changing a coverage pattern that is already stable."
                        ),
                        confidence="high" if measured >= 6 else "medium",
                    )
                )

        return findings


__all__ = ["PerformanceRaidReviewHealerEffectCoverageAnalysisService"]
