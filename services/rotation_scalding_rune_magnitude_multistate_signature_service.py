from __future__ import annotations

"""Research-only Scalding Rune magnitude review for repeated multi-state signatures.

This layer consumes the existing generic ESO Logs magnitude-transition report and groups
amount-changing transitions by the exact net state signature observed between adjacent
reviewed periodic occurrences. It does not infer causality or promote runtime magnitude
policy.
"""

from dataclasses import dataclass
from statistics import median

from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport,
    RotationDDPeriodicEsoLogsMagnitudeTransition,
    RotationDDPeriodicEsoLogsStateEventEvidence,
)


@dataclass(frozen=True)
class RotationScaldingRuneMagnitudeStateFactor:
    actor_scope: str
    event_type: str
    ability_game_id: int | None
    ability_name: str | None


@dataclass(frozen=True)
class RotationScaldingRuneMagnitudeSignatureSummary:
    factors: tuple[RotationScaldingRuneMagnitudeStateFactor, ...]
    sample_count: int
    amount_increased: int
    amount_decreased: int
    median_ratio: float
    minimum_ratio: float
    maximum_ratio: float

    @property
    def direction_consistent(self) -> bool:
        return self.amount_increased == self.sample_count or self.amount_decreased == self.sample_count


@dataclass(frozen=True)
class RotationScaldingRuneMagnitudeMultistateSignatureReport:
    transition_count: int
    multistate_transition_count: int
    signatures: tuple[RotationScaldingRuneMagnitudeSignatureSummary, ...]
    reversible_signature_pairs: int
    unresolved: tuple[str, ...] = ()


class RotationScaldingRuneMagnitudeMultistateSignatureService:
    """Group repeated multi-state Scalding Rune amount changes without causal promotion."""

    def analyze(
        self,
        report: RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport,
        *,
        minimum_samples: int = 2,
    ) -> RotationScaldingRuneMagnitudeMultistateSignatureReport:
        threshold = max(1, int(minimum_samples))
        grouped: dict[
            tuple[RotationScaldingRuneMagnitudeStateFactor, ...],
            list[float],
        ] = {}
        multistate_count = 0

        for transition in report.transitions:
            if len(transition.state_events) < 2:
                continue
            multistate_count += 1
            signature = self._signature(transition)
            if transition.from_amount == 0:
                continue
            grouped.setdefault(signature, []).append(
                float(transition.to_amount) / float(transition.from_amount)
            )

        summaries: list[RotationScaldingRuneMagnitudeSignatureSummary] = []
        for signature, ratios in grouped.items():
            if len(ratios) < threshold:
                continue
            summaries.append(
                RotationScaldingRuneMagnitudeSignatureSummary(
                    factors=signature,
                    sample_count=len(ratios),
                    amount_increased=sum(1 for ratio in ratios if ratio > 1.0),
                    amount_decreased=sum(1 for ratio in ratios if ratio < 1.0),
                    median_ratio=float(median(ratios)),
                    minimum_ratio=min(ratios),
                    maximum_ratio=max(ratios),
                )
            )

        summaries.sort(
            key=lambda item: (
                -item.sample_count,
                not item.direction_consistent,
                abs(item.median_ratio - 1.0),
                self._render_signature(item.factors),
            )
        )
        reversible_pairs = self._reversible_pairs(tuple(summaries))

        unresolved: list[str] = []
        if multistate_count == 0:
            unresolved.append("Scalding Rune: no multi-state amount-changing transitions were observed")
        if not summaries:
            unresolved.append(
                f"Scalding Rune: no repeated multi-state signatures reached minimum sample count {threshold}"
            )

        return RotationScaldingRuneMagnitudeMultistateSignatureReport(
            transition_count=len(report.transitions),
            multistate_transition_count=multistate_count,
            signatures=tuple(summaries),
            reversible_signature_pairs=reversible_pairs,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )

    @classmethod
    def _signature(
        cls,
        transition: RotationDDPeriodicEsoLogsMagnitudeTransition,
    ) -> tuple[RotationScaldingRuneMagnitudeStateFactor, ...]:
        return tuple(
            sorted(
                (cls._factor(transition, event) for event in transition.state_events),
                key=lambda item: (
                    item.actor_scope,
                    item.event_type,
                    -1 if item.ability_game_id is None else item.ability_game_id,
                    item.ability_name or "",
                ),
            )
        )

    @staticmethod
    def _factor(
        transition: RotationDDPeriodicEsoLogsMagnitudeTransition,
        event: RotationDDPeriodicEsoLogsStateEventEvidence,
    ) -> RotationScaldingRuneMagnitudeStateFactor:
        if event.target_id == transition.source_id:
            scope = "source"
        elif event.target_id == transition.target_id:
            scope = "target"
        else:
            scope = "other"
        return RotationScaldingRuneMagnitudeStateFactor(
            actor_scope=scope,
            event_type=event.event_type,
            ability_game_id=event.ability_game_id,
            ability_name=event.ability_name,
        )

    @classmethod
    def _reversible_pairs(
        cls,
        summaries: tuple[RotationScaldingRuneMagnitudeSignatureSummary, ...],
    ) -> int:
        signatures = {summary.factors for summary in summaries}
        seen: set[frozenset[tuple[RotationScaldingRuneMagnitudeStateFactor, ...]]] = set()
        for signature in signatures:
            inverse = tuple(
                sorted(
                    (
                        RotationScaldingRuneMagnitudeStateFactor(
                            actor_scope=factor.actor_scope,
                            event_type=cls._inverse_event_type(factor.event_type),
                            ability_game_id=factor.ability_game_id,
                            ability_name=factor.ability_name,
                        )
                        for factor in signature
                    ),
                    key=lambda item: (
                        item.actor_scope,
                        item.event_type,
                        -1 if item.ability_game_id is None else item.ability_game_id,
                        item.ability_name or "",
                    ),
                )
            )
            if inverse in signatures and inverse != signature:
                seen.add(frozenset((signature, inverse)))
        return len(seen)

    @staticmethod
    def _inverse_event_type(event_type: str) -> str:
        if event_type == "state_gained":
            return "state_lost"
        if event_type == "state_lost":
            return "state_gained"
        return event_type

    @staticmethod
    def _render_signature(
        signature: tuple[RotationScaldingRuneMagnitudeStateFactor, ...],
    ) -> str:
        return "|".join(
            f"{item.actor_scope}:{item.event_type}:{item.ability_game_id}:{item.ability_name or ''}"
            for item in signature
        )


__all__ = [
    "RotationScaldingRuneMagnitudeMultistateSignatureReport",
    "RotationScaldingRuneMagnitudeMultistateSignatureService",
    "RotationScaldingRuneMagnitudeSignatureSummary",
    "RotationScaldingRuneMagnitudeStateFactor",
]
