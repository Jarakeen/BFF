from __future__ import annotations

"""Contextualize lower DD wipe-side output using already-reviewed Raid Review evidence.

This layer owns no mechanics and does not recompute damage, death, continuity, or
landing-recovery truth.  It only joins those existing observations so a lower-output
finding can say which measured conditions accompanied it.  Association is not treated
as causation, and the service emits nothing when there is not enough repeated kill/wipe
evidence to make the comparison useful.
"""

from statistics import median
from typing import Iterable

from services.performance_raid_review_dd_ground_continuity_service import (
    RaidReviewDDGroundContinuityObservation,
)
from services.performance_raid_review_landing_recovery_completion_analysis_service import (
    RaidReviewRecoveryOpportunity,
)
from services.performance_raid_review_landing_recovery_service import (
    RaidReviewLandingRecoveryObservation,
)
from services.performance_raid_review_service import (
    RaidReviewFinding,
    RaidReviewObservation,
)


_REACQUISITION_KEY = "boss_damage_reacquisition_after_landing"


class PerformanceRaidReviewDDOutputContextService:
    """Explain repeated lower wipe-side DD output with measured contextual evidence."""

    def findings(
        self,
        observations: Iterable[RaidReviewObservation],
        *,
        continuity_observations: Iterable[RaidReviewDDGroundContinuityObservation] = (),
        recovery_opportunities: Iterable[RaidReviewRecoveryOpportunity] = (),
        recovery_observations: Iterable[RaidReviewLandingRecoveryObservation] = (),
        minimum_output_drop_fraction: float = 0.12,
        minimum_contact_gap_delta_seconds: float = 1.0,
        minimum_contact_gap_rate_delta: float = 0.10,
    ) -> tuple[RaidReviewFinding, ...]:
        rows = tuple(row for row in observations if row.canonical_role == "DPS")
        if not rows:
            return ()

        continuity_by_pull_actor = {
            (str(row.report_code), int(row.fight_id), int(row.actor_id)): row
            for row in continuity_observations
        }
        opportunities = tuple(
            row for row in recovery_opportunities
            if row.signal_semantic_key == _REACQUISITION_KEY
        )
        recoveries = tuple(
            row for row in recovery_observations
            if row.signal_semantic_key == _REACQUISITION_KEY
        )

        by_player: dict[str, list[RaidReviewObservation]] = {}
        for row in rows:
            by_player.setdefault(row.stable_member_key, []).append(row)

        output_threshold = max(0.0, float(minimum_output_drop_fraction))
        gap_delta_threshold = max(0.0, float(minimum_contact_gap_delta_seconds))
        gap_rate_threshold = max(0.0, float(minimum_contact_gap_rate_delta))
        findings: list[RaidReviewFinding] = []

        for player_rows in by_player.values():
            kills = [row for row in player_rows if row.kill and row.active_output_per_second > 0]
            wipes = [row for row in player_rows if not row.kill and row.active_output_per_second > 0]
            if len(kills) < 2 or len(wipes) < 2:
                continue

            kill_output = median(row.active_output_per_second for row in kills)
            wipe_output = median(row.active_output_per_second for row in wipes)
            if kill_output <= 0:
                continue
            output_delta_fraction = (wipe_output - kill_output) / kill_output
            if output_delta_fraction > -output_threshold:
                continue

            sample = player_rows[0]
            evidence_parts = [
                f"Median boss-active output: kills {kill_output:,.0f}/s vs wipes {wipe_output:,.0f}/s ({output_delta_fraction * 100:+.0f}%)."
            ]
            context_labels: list[str] = []

            death_wipes = [row for row in wipes if row.death_count > 0]
            if death_wipes:
                evidence_parts.append(
                    f"Deaths were recorded in {len(death_wipes)}/{len(wipes)} compared wipe pulls."
                )
                context_labels.append("death-affected pulls")

            kill_continuity = self._continuity_for_rows(kills, continuity_by_pull_actor)
            wipe_continuity = self._continuity_for_rows(wipes, continuity_by_pull_actor)
            if len(kill_continuity) >= 2 and len(wipe_continuity) >= 2:
                kill_longest = median(row.longest_inactivity_seconds for row in kill_continuity)
                wipe_longest = median(row.longest_inactivity_seconds for row in wipe_continuity)
                kill_rate = median(self._gap_rate(row) for row in kill_continuity)
                wipe_rate = median(self._gap_rate(row) for row in wipe_continuity)
                longest_delta = wipe_longest - kill_longest
                rate_delta = wipe_rate - kill_rate
                if longest_delta >= gap_delta_threshold or rate_delta >= gap_rate_threshold:
                    evidence_parts.append(
                        "Mechanic-adjusted boss contact was weaker on wipes: "
                        f"median longest silence {kill_longest:.2f}s on kills vs {wipe_longest:.2f}s on wipes; "
                        f"long-gap share {kill_rate * 100:.0f}% vs {wipe_rate * 100:.0f}%."
                    )
                    context_labels.append("weaker boss-contact continuity")

            kill_reacq = self._reacquisition_completion(
                kills, opportunities, recoveries, sample.stable_member_key
            )
            wipe_reacq = self._reacquisition_completion(
                wipes, opportunities, recoveries, sample.stable_member_key
            )
            if kill_reacq is not None and wipe_reacq is not None:
                kill_completed, kill_total = kill_reacq
                wipe_completed, wipe_total = wipe_reacq
                kill_rate = kill_completed / kill_total if kill_total else 0.0
                wipe_rate = wipe_completed / wipe_total if wipe_total else 0.0
                if wipe_rate + 0.10 < kill_rate:
                    evidence_parts.append(
                        "Post-landing boss reacquisition completed on "
                        f"{kill_completed}/{kill_total} kill opportunities vs {wipe_completed}/{wipe_total} wipe opportunities."
                    )
                    context_labels.append("missed post-landing reacquisition")

            if not context_labels:
                continue

            context_text = ", ".join(context_labels)
            findings.append(
                RaidReviewFinding(
                    scope="player",
                    subject=sample.actor_label,
                    role="DPS",
                    category="damage_context",
                    priority="medium",
                    title="Lower wipe-side damage has measured context",
                    evidence=" ".join(evidence_parts),
                    recommendation=(
                        f"Review the timestamped {context_text} before changing the base rotation. "
                        "These signals accompany the lower-output wipes but do not, by themselves, prove cause; "
                        "check mechanic assignments, movement, target choice, and survival around the same windows."
                    ),
                    confidence="high" if len(kills) >= 4 and len(wipes) >= 4 else "medium",
                )
            )

        findings.sort(key=lambda item: (item.subject.casefold(), item.title.casefold()))
        return tuple(findings)

    @staticmethod
    def _continuity_for_rows(
        rows: list[RaidReviewObservation],
        continuity_by_pull_actor: dict[tuple[str, int, int], RaidReviewDDGroundContinuityObservation],
    ) -> list[RaidReviewDDGroundContinuityObservation]:
        return [
            continuity_by_pull_actor[key]
            for row in rows
            if (key := (str(row.report_code), int(row.fight_id), int(row.actor_id)))
            in continuity_by_pull_actor
        ]

    @staticmethod
    def _gap_rate(row: RaidReviewDDGroundContinuityObservation) -> float:
        if row.measured_gap_count <= 0:
            return 0.0
        return row.inactivity_gap_count / row.measured_gap_count

    @staticmethod
    def _reacquisition_completion(
        rows: list[RaidReviewObservation],
        opportunities: tuple[RaidReviewRecoveryOpportunity, ...],
        recoveries: tuple[RaidReviewLandingRecoveryObservation, ...],
        stable_member_key: str,
    ) -> tuple[int, int] | None:
        pull_keys = {(str(row.report_code), int(row.fight_id)) for row in rows}
        relevant_opportunities = [
            row for row in opportunities
            if (str(row.report_code), int(row.fight_id)) in pull_keys
            and PerformanceRaidReviewDDOutputContextService._stable_recovery_key(
                row.report_code, row.actor_id, row.member_key
            ) == stable_member_key
        ]
        if len(relevant_opportunities) < 2:
            return None

        completed_keys = {
            (
                str(row.report_code),
                int(row.fight_id),
                int(row.occurrence),
                PerformanceRaidReviewDDOutputContextService._stable_recovery_key(
                    row.report_code, row.actor_id, row.member_key
                ),
            )
            for row in recoveries
        }
        completed = sum(
            1
            for row in relevant_opportunities
            if (
                str(row.report_code),
                int(row.fight_id),
                int(row.occurrence),
                PerformanceRaidReviewDDOutputContextService._stable_recovery_key(
                    row.report_code, row.actor_id, row.member_key
                ),
            ) in completed_keys
        )
        return completed, len(relevant_opportunities)

    @staticmethod
    def _stable_recovery_key(report_code: str, actor_id: int, member_key: str) -> str:
        explicit = str(member_key or "").strip().casefold()
        if explicit:
            return explicit
        return f"{str(report_code).strip().casefold()}:{int(actor_id)}"


__all__ = ["PerformanceRaidReviewDDOutputContextService"]
