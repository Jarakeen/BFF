from __future__ import annotations

"""Derive an absolute per-action damage ceiling from a closed descendant denominator.

This service is intentionally local. It does not algebraically maximize ESO stats.
Instead, once a partial branch has been refined into a finite proven-complete set of
descendant candidates, callers may supply complete canonical damage consequences for
every damage-bearing scheduled action in every descendant. The largest exact action
total is then a proven absolute per-action ceiling for that closed branch.

Completeness of direct/periodic/triggered consequences is explicit evidence and is not
inferred merely from the absence of unresolved messages.
"""

from dataclasses import dataclass

from services.extreme_sustained_dps_structural_action_upper_bound_service import (
    ExtremeSustainedDPSAbsoluteActionDamageCeiling,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrenceEvidence,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSClosedActionConsequence:
    occurrence_evidence: RotationActionDamageOccurrenceEvidence
    covers_periodic_and_triggered: bool


@dataclass(frozen=True)
class ExtremeSustainedDPSClosedDescendantActionWitness:
    candidate_key: str
    expected_damage_action_count: int
    consequences: tuple[ExtremeSustainedDPSClosedActionConsequence, ...]

    def __post_init__(self) -> None:
        key = str(self.candidate_key or "").strip()
        if not key:
            raise ValueError("closed descendant action witness requires candidate_key")
        count = int(self.expected_damage_action_count)
        if count < 0:
            raise ValueError("expected damage-action count cannot be negative")
        object.__setattr__(self, "candidate_key", key)
        object.__setattr__(self, "expected_damage_action_count", count)


@dataclass(frozen=True)
class ExtremeSustainedDPSClosedDescendantActionCeilingResult:
    branch_key: str
    descendant_count: int
    represented_descendant_count: int
    observed_action_count: int
    maximum_action_damage: float | None
    ceiling: ExtremeSustainedDPSAbsoluteActionDamageCeiling
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSClosedDescendantActionCeilingService:
    """Promote complete local descendant evidence into an absolute action ceiling."""

    @staticmethod
    def _dedupe(values) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                str(value).strip()
                for value in values
                if str(value).strip()
            )
        )

    @classmethod
    def evaluate(
        cls,
        branch_key: str,
        *,
        expected_descendant_keys: tuple[str, ...],
        denominator_proven: bool,
        witnesses: tuple[ExtremeSustainedDPSClosedDescendantActionWitness, ...],
    ) -> ExtremeSustainedDPSClosedDescendantActionCeilingResult:
        branch = str(branch_key or "").strip()
        if not branch:
            raise ValueError("closed descendant action ceiling requires branch_key")

        expected = tuple(
            dict.fromkeys(
                str(value).strip()
                for value in expected_descendant_keys
                if str(value).strip()
            )
        )
        unresolved: list[str] = []
        if len(expected) != len(tuple(expected_descendant_keys)):
            unresolved.append(
                "Closed descendant denominator contains empty or duplicate candidate keys"
            )
        if not denominator_proven:
            unresolved.append("Closed descendant denominator is not proven complete")
        if not expected:
            unresolved.append("Closed descendant denominator is empty")

        by_key: dict[str, ExtremeSustainedDPSClosedDescendantActionWitness] = {}
        for witness in witnesses:
            if witness.candidate_key in by_key:
                unresolved.append(
                    f"Duplicate descendant action witness: {witness.candidate_key}"
                )
                continue
            by_key[witness.candidate_key] = witness

        expected_set = set(expected)
        represented_set = set(by_key)
        missing = sorted(expected_set - represented_set)
        extra = sorted(represented_set - expected_set)
        if missing:
            unresolved.append(
                "Closed descendant action evidence is missing candidate(s): "
                + ", ".join(missing)
            )
        if extra:
            unresolved.append(
                "Closed descendant action evidence contains out-of-denominator candidate(s): "
                + ", ".join(extra)
            )

        action_totals: list[float] = []
        observed_action_count = 0
        for key in expected:
            witness = by_key.get(key)
            if witness is None:
                continue

            if len(witness.consequences) != witness.expected_damage_action_count:
                unresolved.append(
                    f"{key}: expected {witness.expected_damage_action_count} damage-bearing "
                    f"actions but received {len(witness.consequences)} consequence record(s)"
                )

            coordinates: set[tuple[float, int]] = set()
            for consequence in witness.consequences:
                occurrence = consequence.occurrence_evidence
                coordinate = (
                    float(occurrence.action_time_seconds),
                    int(occurrence.action_sequence),
                )
                if coordinate in coordinates:
                    unresolved.append(
                        f"{key}: duplicate damage-action consequence coordinate "
                        f"{coordinate[0]:g}s sequence {coordinate[1]}"
                    )
                    continue
                coordinates.add(coordinate)
                observed_action_count += 1

                if occurrence.unresolved:
                    unresolved.extend(
                        f"{key} {coordinate[0]:g}s #{coordinate[1]}: {item}"
                        for item in occurrence.unresolved
                    )
                    continue
                if not consequence.covers_periodic_and_triggered:
                    unresolved.append(
                        f"{key} {coordinate[0]:g}s #{coordinate[1]}: action consequence "
                        "does not prove complete periodic/triggered coverage"
                    )
                    continue

                action_totals.append(
                    sum(float(item.damage_value) for item in occurrence.occurrences)
                )

        deduped = cls._dedupe(unresolved)
        maximum = max(action_totals, default=0.0) if not deduped else None
        proven = bool(
            denominator_proven
            and expected
            and not deduped
            and represented_set == expected_set
        )

        ceiling = ExtremeSustainedDPSAbsoluteActionDamageCeiling(
            upper_bound_damage=maximum if proven else None,
            proven_safe=proven,
            covers_periodic_and_triggered=proven,
            source=(
                f"closed descendant exact action-consequence maximum for branch {branch}"
            ),
            unresolved=deduped,
        )
        return ExtremeSustainedDPSClosedDescendantActionCeilingResult(
            branch_key=branch,
            descendant_count=len(expected),
            represented_descendant_count=len(represented_set & expected_set),
            observed_action_count=observed_action_count,
            maximum_action_damage=maximum if proven else None,
            ceiling=ceiling,
            evidence=(
                f"Closed descendant denominator size: {len(expected)}",
                f"Represented descendant candidates: {len(represented_set & expected_set)}",
                f"Damage-bearing action consequences inspected: {observed_action_count}",
                (
                    f"Maximum exact total consequence of one damage action: {maximum:g}"
                    if proven and maximum is not None
                    else "Maximum exact total consequence of one damage action: unresolved"
                ),
                "Every accepted action consequence explicitly covers direct, periodic, and triggered damage within the same horizon",
                "This is a local closed-denominator proof; it does not extrapolate beyond the supplied descendant branch",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSClosedActionConsequence",
    "ExtremeSustainedDPSClosedDescendantActionCeilingResult",
    "ExtremeSustainedDPSClosedDescendantActionCeilingService",
    "ExtremeSustainedDPSClosedDescendantActionWitness",
]
