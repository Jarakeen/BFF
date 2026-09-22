from __future__ import annotations

"""Finite breakpoint family for continuous potion first-use offsets.

This service closes only named-buff runtime state over an explicit finite set of
observation times and effective potion-buff durations. It does not claim potion
instant-restoration timing or any other consequence not represented by those
observations.
"""

from dataclasses import dataclass
import math


_EPSILON = 1e-9
_PRECISION = 9


def _seconds(value: float) -> float:
    return round(float(value), _PRECISION)


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionTimingBreakpointChoice:
    first_use_seconds: float
    kind: str
    source_boundary_seconds: float | None = None


@dataclass(frozen=True)
class ExtremeSustainedDPSPotionTimingBreakpointFrontier:
    choices: tuple[ExtremeSustainedDPSPotionTimingBreakpointChoice, ...]
    candidate_count: int
    named_buff_state_denominator_proven: bool
    full_potion_timing_closed: bool
    omitted_scope: tuple[str, ...]
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSPotionTimingBreakpointFrontierService:
    """Reduce continuous first-use offsets to exact observation-state regions."""

    @staticmethod
    def _validate_positive(name: str, value: float) -> float:
        result = float(value)
        if not math.isfinite(result) or result <= 0.0:
            raise ValueError(f"{name} must be finite and positive")
        return result

    @classmethod
    def _domain_limit(
        cls,
        *,
        duration_seconds: float,
        cooldown_seconds: float,
    ) -> float:
        duration = cls._validate_positive("duration_seconds", duration_seconds)
        cooldown = cls._validate_positive("cooldown_seconds", cooldown_seconds)
        return min(duration, cooldown)

    @staticmethod
    def _normalize_observations(
        observations: tuple[float, ...],
        *,
        duration_seconds: float,
    ) -> tuple[float, ...]:
        result: list[float] = []
        for raw in observations:
            value = float(raw)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(
                    "potion timing observation times must be finite and non-negative"
                )
            if value > float(duration_seconds) + _EPSILON:
                raise ValueError(
                    "potion timing observation cannot exceed rotation duration"
                )
            normalized = _seconds(value)
            if normalized not in result:
                result.append(normalized)
        return tuple(sorted(result))

    @staticmethod
    def _normalize_durations(
        durations: tuple[float, ...],
    ) -> tuple[float, ...]:
        result: list[float] = []
        for raw in durations:
            value = float(raw)
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(
                    "effective potion buff durations must be finite and positive"
                )
            normalized = _seconds(value)
            if normalized not in result:
                result.append(normalized)
        return tuple(sorted(result))

    @classmethod
    def _breakpoints(
        cls,
        *,
        observations: tuple[float, ...],
        buff_durations: tuple[float, ...],
        cooldown_seconds: float,
        limit: float,
    ) -> tuple[float, ...]:
        cooldown = float(cooldown_seconds)
        values = {0.0, _seconds(limit)}

        for observation in observations:
            max_cycle = int(math.floor(float(observation) / cooldown)) + 1
            for cycle in range(max_cycle + 1):
                activation = float(observation) - cycle * cooldown
                if -_EPSILON <= activation <= limit + _EPSILON:
                    values.add(_seconds(min(max(activation, 0.0), limit)))

                for duration in buff_durations:
                    expiry = float(observation) - float(duration) - cycle * cooldown
                    if -_EPSILON <= expiry <= limit + _EPSILON:
                        values.add(_seconds(min(max(expiry, 0.0), limit)))

        return tuple(sorted(values))

    @classmethod
    def build(
        cls,
        *,
        duration_seconds: float,
        cooldown_seconds: float,
        observation_times: tuple[float, ...],
        effective_buff_durations: tuple[float, ...],
        instant_restoration_timing_closed: bool = False,
    ) -> ExtremeSustainedDPSPotionTimingBreakpointFrontier:
        duration = cls._validate_positive("duration_seconds", duration_seconds)
        cooldown = cls._validate_positive("cooldown_seconds", cooldown_seconds)
        observations = cls._normalize_observations(
            tuple(observation_times),
            duration_seconds=duration,
        )
        durations = cls._normalize_durations(tuple(effective_buff_durations))
        unresolved: list[str] = []

        if not observations:
            unresolved.append(
                "Finite potion timing observation set is empty"
            )
        if not durations:
            unresolved.append(
                "No effective named-buff durations were supplied"
            )

        limit = cls._domain_limit(
            duration_seconds=duration,
            cooldown_seconds=cooldown,
        )
        breakpoints = cls._breakpoints(
            observations=observations,
            buff_durations=durations,
            cooldown_seconds=cooldown,
            limit=limit,
        )

        choices: list[ExtremeSustainedDPSPotionTimingBreakpointChoice] = []
        for boundary in breakpoints:
            if boundary < limit - _EPSILON:
                choices.append(
                    ExtremeSustainedDPSPotionTimingBreakpointChoice(
                        first_use_seconds=boundary,
                        kind="boundary",
                        source_boundary_seconds=boundary,
                    )
                )

        for left, right in zip(breakpoints, breakpoints[1:]):
            if right - left <= _EPSILON:
                continue
            midpoint = _seconds((left + right) / 2.0)
            if midpoint >= limit - _EPSILON:
                continue
            choices.append(
                ExtremeSustainedDPSPotionTimingBreakpointChoice(
                    first_use_seconds=midpoint,
                    kind="open_interval_representative",
                    source_boundary_seconds=None,
                )
            )

        unique: dict[float, ExtremeSustainedDPSPotionTimingBreakpointChoice] = {}
        for choice in choices:
            unique.setdefault(choice.first_use_seconds, choice)
        ordered = tuple(unique[key] for key in sorted(unique))

        named_closed = bool(ordered and not unresolved)
        omitted: list[str] = []
        if not instant_restoration_timing_closed:
            omitted.append(
                "potion instant-restoration timing is not closed by named-buff breakpoint coverage"
            )

        return ExtremeSustainedDPSPotionTimingBreakpointFrontier(
            choices=ordered,
            candidate_count=len(ordered),
            named_buff_state_denominator_proven=named_closed,
            full_potion_timing_closed=bool(
                named_closed and instant_restoration_timing_closed
            ),
            omitted_scope=tuple(omitted),
            evidence=(
                f"Finite potion runtime observation points: {len(observations)}",
                f"Effective named-buff durations: {len(durations)}",
                f"Continuous first-use domain: [0, {limit:g}) seconds",
                f"State-change boundaries: {len(breakpoints)}",
                f"Finite representative first-use offsets: {len(ordered)}",
                (
                    "Named-buff first-use timing denominator is closed over supplied observations"
                    if named_closed
                    else "Named-buff first-use timing denominator remains open"
                ),
                "Representatives include every exact activation/expiry boundary plus one point from each open interval between boundaries",
                "When a boundary coincides with an observed action timestamp, downstream policy materialization must still enumerate before/after same-timestamp ordering",
                "Offsets at or beyond the finite domain limit are equivalent to explicit no-use within the modeled horizon",
            ),
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "ExtremeSustainedDPSPotionTimingBreakpointChoice",
    "ExtremeSustainedDPSPotionTimingBreakpointFrontier",
    "ExtremeSustainedDPSPotionTimingBreakpointFrontierService",
]
