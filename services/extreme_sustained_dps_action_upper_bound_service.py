from __future__ import annotations

"""Promote exact action-damage consequences to pruning bounds only with dominance proof.

Canonical Rotation evaluators already own exact skill/Ultimate damage consequences for
one concrete build/runtime witness. Exact damage is not automatically an optimistic
upper bound over unsynthesized gear, CP, passive, skill-bar, or runtime mutations.
This service keeps those concepts separate and fails open unless a caller supplies an
explicit dominance proof for every still-open mutation axis.
"""

from dataclasses import dataclass
from math import isfinite

from services.extreme_sustained_dps_rotation_upper_bound_service import (
    ExtremeSustainedDPSActionUpperBound,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrenceEvidence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSActionDominanceProof:
    candidate_key: str
    dominated_axes: tuple[str, ...]
    required_axes: tuple[str, ...]
    optimistic_multiplier: float = 1.0
    source: str = ""
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        multiplier = float(self.optimistic_multiplier)
        if not isfinite(multiplier) or multiplier < 1.0:
            raise ValueError(
                "sustained-DPS action dominance multiplier must be finite and at least 1"
            )
        object.__setattr__(self, "optimistic_multiplier", multiplier)
        object.__setattr__(
            self,
            "dominated_axes",
            tuple(dict.fromkeys(str(x).strip() for x in self.dominated_axes if str(x).strip())),
        )
        object.__setattr__(
            self,
            "required_axes",
            tuple(dict.fromkeys(str(x).strip() for x in self.required_axes if str(x).strip())),
        )
        object.__setattr__(
            self,
            "unresolved",
            tuple(dict.fromkeys(str(x).strip() for x in self.unresolved if str(x).strip())),
        )

    @property
    def complete(self) -> bool:
        dominated = {axis.casefold() for axis in self.dominated_axes}
        required = {axis.casefold() for axis in self.required_axes}
        return required.issubset(dominated) and not self.unresolved


@dataclass(frozen=True)
class ExtremeSustainedDPSActionUpperBoundResult:
    bound: ExtremeSustainedDPSActionUpperBound
    exact_damage: float | None
    dominance_complete: bool
    evidence: tuple[str, ...]


class ExtremeSustainedDPSActionUpperBoundService:
    """Bridge exact canonical action occurrences into proof-safe optimistic bounds."""

    @classmethod
    def from_occurrences(
        cls,
        *,
        occurrence_evidence: RotationActionDamageOccurrenceEvidence,
        dominance: ExtremeSustainedDPSActionDominanceProof,
    ) -> ExtremeSustainedDPSActionUpperBoundResult:
        unresolved = list(occurrence_evidence.unresolved)
        unresolved.extend(dominance.unresolved)

        if occurrence_evidence.unresolved:
            bound = ExtremeSustainedDPSActionUpperBound(
                time_seconds=occurrence_evidence.action_time_seconds,
                sequence=occurrence_evidence.action_sequence,
                upper_bound_damage=None,
                proven_safe=False,
                covers_periodic_and_triggered=False,
                source=dominance.source,
                unresolved=tuple(dict.fromkeys(unresolved)),
            )
            return ExtremeSustainedDPSActionUpperBoundResult(
                bound=bound,
                exact_damage=None,
                dominance_complete=False,
                evidence=(
                    "Exact canonical action consequence is unresolved; no pruning ceiling was promoted",
                ),
            )

        exact_damage = sum(
            float(item.damage_value)
            for item in occurrence_evidence.occurrences
        )

        missing_axes = cls._missing_axes(dominance)
        if missing_axes:
            unresolved.append(
                "Action dominance proof does not cover open mutation axes: "
                + ", ".join(missing_axes)
            )

        complete = dominance.complete and not missing_axes
        optimistic = (
            exact_damage * float(dominance.optimistic_multiplier)
            if complete
            else None
        )
        bound = ExtremeSustainedDPSActionUpperBound(
            time_seconds=occurrence_evidence.action_time_seconds,
            sequence=occurrence_evidence.action_sequence,
            upper_bound_damage=optimistic,
            proven_safe=complete,
            covers_periodic_and_triggered=not bool(occurrence_evidence.unresolved),
            source=dominance.source,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )
        evidence = (
            f"Exact canonical action damage: {exact_damage:g}",
            f"Dominance multiplier: {float(dominance.optimistic_multiplier):g}",
            f"Required mutation axes: {len(dominance.required_axes)}",
            f"Dominated mutation axes: {len(dominance.dominated_axes)}",
            (
                "Action promoted to proof-safe optimistic ceiling"
                if complete
                else "Action remains fail-open because dominance over future mutation axes is incomplete"
            ),
        )
        return ExtremeSustainedDPSActionUpperBoundResult(
            bound=bound,
            exact_damage=exact_damage,
            dominance_complete=complete,
            evidence=evidence,
        )

    @staticmethod
    def _missing_axes(
        dominance: ExtremeSustainedDPSActionDominanceProof,
    ) -> tuple[str, ...]:
        dominated = {axis.casefold() for axis in dominance.dominated_axes}
        return tuple(
            axis
            for axis in dominance.required_axes
            if axis.casefold() not in dominated
        )


__all__ = [
    "ExtremeSustainedDPSActionDominanceProof",
    "ExtremeSustainedDPSActionUpperBoundResult",
    "ExtremeSustainedDPSActionUpperBoundService",
]
