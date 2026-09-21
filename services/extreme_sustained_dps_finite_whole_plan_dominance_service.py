from __future__ import annotations

"""Proof-safe whole-plan dominance over one finite generated dynamic family.

Unlike action-level dominance, this service allows the compared candidates to change
scheduled action identity and plan shape. Every choice must instead resolve a complete
modeled sustained-DPS result over the same exact horizon.

If the finite denominator is proven complete and every choice resolves completely,
the largest modeled DPS is a proof-safe ceiling for that finite family. Omitted scope
is preserved separately and prevents callers from mistaking finite-family closure for
theoretical global closure.
"""

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
)
from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
)


T = TypeVar("T")


class ExtremeSustainedDPSFiniteWholePlanFrontier(Protocol[T]):
    @property
    def axes(self) -> tuple[str, ...]: ...

    @property
    def choice_count(self) -> int: ...

    @property
    def denominator_proven(self) -> bool: ...

    @property
    def omitted_scope(self) -> tuple[str, ...]: ...

    def choice_at(self, index: int) -> T: ...


@dataclass(frozen=True)
class ExtremeSustainedDPSWholePlanEvaluation:
    choice_id: str
    modeled_dps: float | None
    duration_seconds: float | None
    mechanic_complete: bool
    unresolved: tuple[str, ...] = ()


class ExtremeSustainedDPSFiniteWholePlanEvaluator(Protocol[T]):
    def evaluate(self, choice: T) -> ExtremeSustainedDPSWholePlanEvaluation: ...


@dataclass(frozen=True)
class ExtremeSustainedDPSFiniteWholePlanDominanceResult:
    candidate_key: str
    axes: tuple[str, ...]
    expected_choices: int
    evaluated_choices: int
    resolved_choices: int
    winning_choice_id: str | None
    upper_bound_dps: float | None
    axis_coverage: ExtremeSustainedDPSAxisCoverageProof
    bound: ExtremeSustainedDPSBoundEvidence
    omitted_scope: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSFiniteWholePlanDominanceService:
    """Promote complete finite same-horizon whole-plan results into a family ceiling."""

    TOLERANCE = 1e-9

    @classmethod
    def evaluate_indexed(
        cls,
        *,
        candidate_key: str,
        frontier: ExtremeSustainedDPSFiniteWholePlanFrontier[T],
        evaluator: ExtremeSustainedDPSFiniteWholePlanEvaluator[T],
        required_duration_seconds: float,
        source: str,
    ) -> ExtremeSustainedDPSFiniteWholePlanDominanceResult:
        key = str(candidate_key or "").strip()
        if not key:
            raise ValueError("finite whole-plan dominance requires candidate_key")

        duration = float(required_duration_seconds)
        if duration <= 0.0:
            raise ValueError("finite whole-plan dominance duration must be positive")

        canonical = {
            axis.casefold(): axis
            for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        }
        axes: list[str] = []
        unresolved: list[str] = []
        for raw in frontier.axes:
            token = str(raw or "").strip().casefold()
            if not token:
                continue
            axis = canonical.get(token)
            if axis is None:
                unresolved.append(
                    f"Unknown sustained-DPS mutation axis: {str(raw).strip()}"
                )
            elif axis not in axes:
                axes.append(axis)

        if not axes:
            unresolved.append("Finite whole-plan dominance requires at least one canonical axis")
        if not bool(frontier.denominator_proven):
            unresolved.append("Finite whole-plan denominator is not proven complete")

        expected = int(frontier.choice_count)
        if expected <= 0:
            unresolved.append("Finite whole-plan denominator is empty")

        evaluated = 0
        resolved = 0
        seen: set[str] = set()
        winner_id: str | None = None
        winner_dps: float | None = None

        for index in range(max(expected, 0)):
            result = evaluator.evaluate(frontier.choice_at(index))
            evaluated += 1

            choice_id = str(result.choice_id or "").strip()
            if not choice_id:
                unresolved.append(f"choice index {index}: whole-plan evaluator returned empty identity")
                continue
            if choice_id in seen:
                unresolved.append(f"Duplicate whole-plan choice identity: {choice_id}")
                continue
            seen.add(choice_id)

            local = list(result.unresolved)
            if result.duration_seconds is None:
                local.append("whole-plan duration is unavailable")
            elif abs(float(result.duration_seconds) - duration) > cls.TOLERANCE:
                local.append(
                    f"whole-plan duration {float(result.duration_seconds):g}s does not match "
                    f"required horizon {duration:g}s"
                )
            if result.modeled_dps is None:
                local.append("modeled sustained DPS is unavailable")
            elif float(result.modeled_dps) < 0.0:
                local.append("modeled sustained DPS cannot be negative")
            if not result.mechanic_complete:
                local.append("whole-plan mechanic evidence is incomplete")

            if local:
                unresolved.extend(
                    f"{choice_id}: {item}" for item in local
                )
                continue

            score = float(result.modeled_dps)
            resolved += 1
            if (
                winner_dps is None
                or score > winner_dps + cls.TOLERANCE
                or (
                    abs(score - winner_dps) <= cls.TOLERANCE
                    and choice_id.casefold() < str(winner_id or choice_id).casefold()
                )
            ):
                winner_dps = score
                winner_id = choice_id

        deduped = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in unresolved
                if str(item).strip()
            )
        )
        omitted = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in frontier.omitted_scope
                if str(item).strip()
            )
        )
        complete = bool(
            frontier.denominator_proven
            and axes
            and expected > 0
            and len(seen) == expected
            and evaluated == expected
            and resolved == expected
            and winner_dps is not None
            and not deduped
        )

        coverage = ExtremeSustainedDPSAxisCoverageProof(
            source=str(source or "").strip() or "finite whole-plan dominance",
            dominated_axes=tuple(axes) if complete else (),
            unresolved=deduped,
        )
        bound = ExtremeSustainedDPSBoundEvidence(
            candidate_key=key,
            upper_bound_dps=float(winner_dps) if complete else None,
            proven_safe=complete,
            source=str(source or "").strip() or "finite whole-plan dominance",
            unresolved=deduped,
        )

        return ExtremeSustainedDPSFiniteWholePlanDominanceResult(
            candidate_key=key,
            axes=tuple(axes),
            expected_choices=expected,
            evaluated_choices=evaluated,
            resolved_choices=resolved,
            winning_choice_id=winner_id if complete else None,
            upper_bound_dps=float(winner_dps) if complete else None,
            axis_coverage=coverage,
            bound=bound,
            omitted_scope=omitted,
            evidence=(
                f"Canonical dynamic axes searched jointly: {', '.join(axes) or '(none)'}",
                f"Whole-plan choices expected/evaluated/resolved: {expected}/{evaluated}/{resolved}",
                f"Required comparison horizon: {duration:g}s",
                (
                    f"Finite-family sustained-DPS ceiling: {float(winner_dps):g}"
                    if complete and winner_dps is not None
                    else "Finite-family sustained-DPS ceiling withheld"
                ),
                "Plan shape and action identity may differ across choices; same-horizon complete modeled DPS is the comparison authority",
                "Omitted scope is preserved separately from finite-family denominator closure",
            ),
            unresolved=deduped,
        )


__all__ = [
    "ExtremeSustainedDPSFiniteWholePlanDominanceResult",
    "ExtremeSustainedDPSFiniteWholePlanDominanceService",
    "ExtremeSustainedDPSFiniteWholePlanEvaluator",
    "ExtremeSustainedDPSFiniteWholePlanFrontier",
    "ExtremeSustainedDPSWholePlanEvaluation",
]
