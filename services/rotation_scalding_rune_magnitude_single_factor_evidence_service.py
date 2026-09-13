from __future__ import annotations

"""Read-only single-factor magnitude evidence for Scalding Rune periodic ticks.

This service summarizes already-reviewed ESO Logs magnitude transitions. It does not
promote runtime magnitude semantics. Numeric ability IDs remain observational evidence
handles, and one-factor correlations remain evidence rather than causal proof.
"""

from dataclasses import dataclass
import math
from pathlib import Path
from statistics import median

from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport,
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionService,
)


SCALDING_RUNE_SKILL_ENTITY_ID = "scalding_rune"
SCALDING_RUNE_PERIODIC_EVIDENCE_ID = 40468


@dataclass(frozen=True)
class RotationScaldingRuneMagnitudeSingleFactorSummary:
    ability_game_id: int | None
    ability_name: str | None
    state_event_type: str
    affected_actor: str
    sample_count: int
    amount_increase_count: int
    amount_decrease_count: int
    median_amount_ratio: float
    minimum_amount_ratio: float
    maximum_amount_ratio: float

    @property
    def directionally_consistent(self) -> bool:
        return self.amount_increase_count == 0 or self.amount_decrease_count == 0


@dataclass(frozen=True)
class RotationScaldingRuneMagnitudeSingleFactorEvidenceReport:
    periodic_ability_id: int
    comparable_occurrence_pairs: int
    state_same_amount_changed: int
    single_factor_amount_change_transitions: int
    multi_factor_amount_change_transitions: int
    summaries: tuple[RotationScaldingRuneMagnitudeSingleFactorSummary, ...]
    unresolved: tuple[str, ...] = ()


class RotationScaldingRuneMagnitudeSingleFactorEvidenceService:
    """Rank clean one-state Scalding Rune tick transitions for magnitude review.

    The underlying generic service reconstructs net source/target state at adjacent tick
    boundaries. This layer keeps only amount-changing transitions with exactly one net
    state delta, groups them by observed effect identity/direction/affected actor, and
    summarizes damage-ratio repeatability.
    """

    def __init__(
        self,
        *,
        canonical_database_path: str | Path,
        logs_database_path: str | Path,
        transition_service: RotationDDPeriodicEsoLogsMagnitudeStateTransitionService | None = None,
    ) -> None:
        self.transition_service = transition_service or (
            RotationDDPeriodicEsoLogsMagnitudeStateTransitionService(
                canonical_database_path=canonical_database_path,
                logs_database_path=logs_database_path,
            )
        )

    def inspect(
        self,
        *,
        report_code: str | None = None,
        fight_id: int | None = None,
        source_id: int | None = None,
    ) -> RotationScaldingRuneMagnitudeSingleFactorEvidenceReport:
        base = self.transition_service.inspect(
            SCALDING_RUNE_SKILL_ENTITY_ID,
            periodic_ability_id=SCALDING_RUNE_PERIODIC_EVIDENCE_ID,
            report_code=report_code,
            fight_id=fight_id,
            source_id=source_id,
        )
        return self.from_transition_report(base)

    @classmethod
    def from_transition_report(
        cls,
        base: RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport,
    ) -> RotationScaldingRuneMagnitudeSingleFactorEvidenceReport:
        grouped: dict[
            tuple[int | None, str | None, str, str],
            list[tuple[float, bool]],
        ] = {}
        single_count = 0
        multi_count = 0

        for transition in base.transitions:
            if len(transition.state_events) != 1:
                if len(transition.state_events) > 1:
                    multi_count += 1
                continue
            event = transition.state_events[0]
            if transition.from_amount == 0:
                continue
            ratio = float(transition.to_amount) / float(transition.from_amount)
            if not math.isfinite(ratio) or ratio <= 0:
                continue
            affected_actor = cls._affected_actor(
                event.target_id,
                source_id=transition.source_id,
                target_id=transition.target_id,
            )
            key = (
                event.ability_game_id,
                event.ability_name,
                str(event.event_type),
                affected_actor,
            )
            grouped.setdefault(key, []).append(
                (ratio, transition.to_amount > transition.from_amount)
            )
            single_count += 1

        summaries: list[RotationScaldingRuneMagnitudeSingleFactorSummary] = []
        for (
            ability_game_id,
            ability_name,
            state_event_type,
            affected_actor,
        ), values in grouped.items():
            ratios = [ratio for ratio, _increase in values]
            increases = sum(1 for _ratio, increase in values if increase)
            decreases = len(values) - increases
            summaries.append(
                RotationScaldingRuneMagnitudeSingleFactorSummary(
                    ability_game_id=ability_game_id,
                    ability_name=ability_name,
                    state_event_type=state_event_type,
                    affected_actor=affected_actor,
                    sample_count=len(values),
                    amount_increase_count=increases,
                    amount_decrease_count=decreases,
                    median_amount_ratio=float(median(ratios)),
                    minimum_amount_ratio=min(ratios),
                    maximum_amount_ratio=max(ratios),
                )
            )

        summaries.sort(
            key=lambda item: (
                -item.sample_count,
                not item.directionally_consistent,
                item.ability_name or "",
                -1 if item.ability_game_id is None else item.ability_game_id,
                item.state_event_type,
                item.affected_actor,
            )
        )

        unresolved = list(base.unresolved)
        if not summaries:
            unresolved.append(
                "Scalding Rune: no usable one-state amount-changing transitions were observed"
            )
        if base.state_same_amount_changed:
            unresolved.append(
                "Scalding Rune still has amount-changing adjacent ticks with no observed net source/target state change; tracked state is not a complete magnitude model"
            )

        return RotationScaldingRuneMagnitudeSingleFactorEvidenceReport(
            periodic_ability_id=int(base.periodic_ability_id),
            comparable_occurrence_pairs=int(base.comparable_occurrence_pairs),
            state_same_amount_changed=int(base.state_same_amount_changed),
            single_factor_amount_change_transitions=single_count,
            multi_factor_amount_change_transitions=multi_count,
            summaries=tuple(summaries),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @staticmethod
    def _affected_actor(
        observed_target_id: int | None,
        *,
        source_id: int,
        target_id: int,
    ) -> str:
        if observed_target_id is None:
            return "unknown"
        if int(observed_target_id) == int(source_id):
            return "source"
        if int(observed_target_id) == int(target_id):
            return "damage_target"
        return "other"


__all__ = [
    "SCALDING_RUNE_PERIODIC_EVIDENCE_ID",
    "SCALDING_RUNE_SKILL_ENTITY_ID",
    "RotationScaldingRuneMagnitudeSingleFactorEvidenceReport",
    "RotationScaldingRuneMagnitudeSingleFactorEvidenceService",
    "RotationScaldingRuneMagnitudeSingleFactorSummary",
]
