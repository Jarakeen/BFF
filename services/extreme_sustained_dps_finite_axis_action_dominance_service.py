from __future__ import annotations

"""Generic finite-axis action dominance for generated sustained-DPS search.

This service exhausts one caller-supplied finite, proven-complete choice denominator
while every non-target mutation axis remains fixed. Each choice must resolve the same
scheduled damage-action coordinate through a canonical occurrence evaluator.

If every choice resolves with complete direct/periodic/triggered consequences, the
largest exact action total is both:
1) a proof-safe absolute per-action ceiling across the supplied finite axes; and
2) canonical dominance coverage for exactly those axes.

The service does not enumerate axes itself and does not calculate ESO damage.
"""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_structural_action_upper_bound_service import (
    ExtremeSustainedDPSAbsoluteActionDamageCeiling,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrenceEvidence,
)


T = TypeVar("T")


class ExtremeSustainedDPSFiniteChoiceActionEvaluator(Protocol[T]):
    def evaluate(self, choice: T) -> RotationActionDamageOccurrenceEvidence: ...


class ExtremeSustainedDPSIndexedFiniteChoiceFrontier(Protocol[T]):
    @property
    def axes(self) -> tuple[str, ...]: ...

    @property
    def choice_count(self) -> int: ...

    @property
    def denominator_proven(self) -> bool: ...

    def choice_at(self, index: int) -> "ExtremeSustainedDPSFiniteAxisChoice[T]": ...


@dataclass(frozen=True)
class ExtremeSustainedDPSFiniteAxisChoice(Generic[T]):
    choice_id: str
    payload: T

    def __post_init__(self) -> None:
        value = str(self.choice_id or "").strip()
        if not value:
            raise ValueError("finite-axis dominance choice_id cannot be empty")
        object.__setattr__(self, "choice_id", value)


@dataclass(frozen=True)
class ExtremeSustainedDPSFiniteAxisActionDominanceResult:
    candidate_key: str
    axes: tuple[str, ...]
    expected_choices: int
    evaluated_choices: int
    resolved_choices: int
    winning_choice_id: str | None
    upper_bound_damage: float | None
    axis_coverage: ExtremeSustainedDPSAxisCoverageProof
    action_ceiling: ExtremeSustainedDPSAbsoluteActionDamageCeiling
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSFiniteAxisActionDominanceService:
    """Exhaust one proven finite axis denominator for one exact scheduled action."""

    @classmethod
    def evaluate_indexed(
        cls,
        *,
        candidate_key: str,
        frontier: ExtremeSustainedDPSIndexedFiniteChoiceFrontier[T],
        evaluator: ExtremeSustainedDPSFiniteChoiceActionEvaluator[T],
        source: str,
    ) -> ExtremeSustainedDPSFiniteAxisActionDominanceResult:
        count = int(frontier.choice_count)
        if count < 0:
            raise ValueError("indexed finite-axis choice_count cannot be negative")
        return cls._evaluate_accessor(
            candidate_key=candidate_key,
            axes=tuple(frontier.axes),
            expected_choices=count,
            denominator_proven=bool(frontier.denominator_proven),
            choice_at=frontier.choice_at,
            evaluator=evaluator,
            source=source,
        )

    @classmethod
    def evaluate(
        cls,
        *,
        candidate_key: str,
        axes: tuple[str, ...],
        choices: tuple[ExtremeSustainedDPSFiniteAxisChoice[T], ...],
        denominator_proven: bool,
        evaluator: ExtremeSustainedDPSFiniteChoiceActionEvaluator[T],
        source: str,
    ) -> ExtremeSustainedDPSFiniteAxisActionDominanceResult:
        ordered = tuple(sorted(choices, key=lambda row: row.choice_id.casefold()))
        return cls._evaluate_accessor(
            candidate_key=candidate_key,
            axes=axes,
            expected_choices=len(ordered),
            denominator_proven=bool(denominator_proven),
            choice_at=lambda index: ordered[index],
            evaluator=evaluator,
            source=source,
        )

    @classmethod
    def _evaluate_accessor(
        cls,
        *,
        candidate_key: str,
        axes: tuple[str, ...],
        expected_choices: int,
        denominator_proven: bool,
        choice_at,
        evaluator: ExtremeSustainedDPSFiniteChoiceActionEvaluator[T],
        source: str,
    ) -> ExtremeSustainedDPSFiniteAxisActionDominanceResult:
        key = str(candidate_key or "").strip()
        if not key:
            raise ValueError("finite-axis action dominance requires candidate_key")

        canonical = {
            axis.casefold(): axis
            for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        }
        normalized_axes: list[str] = []
        unresolved: list[str] = []
        for raw in axes:
            token = str(raw or "").strip().casefold()
            if not token:
                continue
            axis = canonical.get(token)
            if axis is None:
                unresolved.append(
                    f"Unknown sustained-DPS mutation axis: {str(raw).strip()}"
                )
            elif axis not in normalized_axes:
                normalized_axes.append(axis)
        if not normalized_axes:
            unresolved.append("Finite-axis action dominance requires at least one canonical axis")
        if not denominator_proven:
            unresolved.append("Finite-axis choice denominator is not proven complete")

        expected = int(expected_choices)
        if expected <= 0:
            unresolved.append("Finite-axis choice denominator is empty")

        evaluated = 0
        resolved = 0
        coordinate: tuple[float, int] | None = None
        winner_id: str | None = None
        winner_damage: float | None = None
        seen_ids: set[str] = set()

        for index in range(max(expected, 0)):
            choice = choice_at(index)
            choice_id = str(choice.choice_id or "").strip()
            if choice_id in seen_ids:
                unresolved.append(
                    f"Duplicate finite-axis choice identity: {choice_id}"
                )
                continue
            seen_ids.add(choice_id)

            result = evaluator.evaluate(choice.payload)
            evaluated += 1

            current = (
                float(result.action_time_seconds),
                int(result.action_sequence),
            )
            if coordinate is None:
                coordinate = current
            elif coordinate != current:
                unresolved.append(
                    f"{choice_id}: action coordinate drifted from "
                    f"{coordinate[0]:g}s/{coordinate[1]} to "
                    f"{current[0]:g}s/{current[1]}"
                )
                continue

            if result.unresolved:
                unresolved.extend(
                    f"{choice_id}: {item}"
                    for item in result.unresolved
                )
                continue

            total = sum(float(item.damage_value) for item in result.occurrences)
            resolved += 1
            if (
                winner_damage is None
                or total > winner_damage + 1e-9
                or (
                    abs(total - winner_damage) <= 1e-9
                    and choice_id.casefold() < str(winner_id or choice_id).casefold()
                )
            ):
                winner_damage = total
                winner_id = choice_id

        deduped = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )
        complete = bool(
            denominator_proven
            and normalized_axes
            and expected > 0
            and len(seen_ids) == expected
            and evaluated == expected
            and resolved == expected
            and winner_damage is not None
            and not deduped
        )

        coverage = ExtremeSustainedDPSAxisCoverageProof(
            source=str(source or "").strip() or "finite-axis action dominance",
            dominated_axes=tuple(normalized_axes) if complete else (),
            unresolved=deduped,
        )
        ceiling = ExtremeSustainedDPSAbsoluteActionDamageCeiling(
            upper_bound_damage=float(winner_damage) if complete else None,
            proven_safe=complete,
            covers_periodic_and_triggered=complete,
            source=str(source or "").strip() or "finite-axis action dominance",
            unresolved=deduped,
        )

        return ExtremeSustainedDPSFiniteAxisActionDominanceResult(
            candidate_key=key,
            axes=tuple(normalized_axes),
            expected_choices=expected,
            evaluated_choices=evaluated,
            resolved_choices=resolved,
            winning_choice_id=winner_id if complete else None,
            upper_bound_damage=float(winner_damage) if complete else None,
            axis_coverage=coverage,
            action_ceiling=ceiling,
            evidence=(
                f"Canonical axes searched jointly: {', '.join(normalized_axes) or '(none)'}",
                f"Finite choices expected/evaluated/resolved: {expected}/{evaluated}/{resolved}",
                (
                    f"Finite-axis absolute action ceiling: {float(winner_damage):g}"
                    if complete and winner_damage is not None
                    else "Finite-axis absolute action ceiling withheld"
                ),
                "Every non-target mutation axis must remain fixed by the caller",
                "All supplied choices must resolve one identical scheduled action coordinate",
                "Indexed frontiers are consumed one choice at a time without materializing the denominator",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSFiniteAxisActionDominanceResult",
    "ExtremeSustainedDPSFiniteAxisActionDominanceService",
    "ExtremeSustainedDPSFiniteAxisChoice",
    "ExtremeSustainedDPSFiniteChoiceActionEvaluator",
    "ExtremeSustainedDPSIndexedFiniteChoiceFrontier",
]
