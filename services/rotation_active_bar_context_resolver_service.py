from __future__ import annotations

"""Resolve canonical static build context from the bar active at an action instant."""

from dataclasses import dataclass

from minmax.build_calculation_context import BuildCalculationContext
from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_static_build_context_service import RotationStaticBuildContextResolution


@dataclass(frozen=True)
class RotationActiveBarContextResolverService:
    """Resolve front/back static context from exact plan bar-swap progression.

    Bar swaps are ordered by ``(time_seconds, sequence)``. A swap therefore affects
    later actions at the same timestamp but never earlier-sequence actions at that
    timestamp. This keeps bar ownership deterministic without inventing timing gaps.
    """

    static_context: RotationStaticBuildContextResolution
    plan: RotationPlan
    initial_bar: str = "front"

    def __post_init__(self) -> None:
        initial = self._bar(self.initial_bar, "rotation active-bar initial bar")
        if self.static_context.context_for(initial) is None:
            raise ValueError(
                f"rotation static context is missing initial bar: {initial!r}"
            )
        object.__setattr__(self, "initial_bar", initial)
        # Validate every destination up front so evaluation never becomes partially
        # bar-aware only after a candidate is already being scored.
        for action in self.plan.actions:
            if action.kind is not RotationActionKind.BAR_SWAP:
                continue
            destination = self._bar(
                action.bar,
                "bar-swap rotation action destination",
            )
            if self.static_context.context_for(destination) is None:
                raise ValueError(
                    f"rotation static context is missing bar: {destination!r}"
                )

    def active_bar_at(self, time_seconds: float, sequence: int) -> str:
        instant = float(time_seconds)
        order = int(sequence)
        if instant < 0.0:
            raise ValueError("rotation active-bar lookup time cannot be negative")
        active = self.initial_bar
        swaps = sorted(
            (
                float(action.time_seconds),
                int(action.sequence),
                self._bar(action.bar, "bar-swap rotation action destination"),
            )
            for action in self.plan.actions
            if action.kind is RotationActionKind.BAR_SWAP
        )
        for swap_time, swap_sequence, destination in swaps:
            if (swap_time, swap_sequence) > (instant, order):
                break
            active = destination
        return active

    def context_at(self, time_seconds: float, sequence: int) -> BuildCalculationContext:
        bar = self.active_bar_at(time_seconds, sequence)
        context = self.static_context.context_for(bar)
        if context is None:
            # Constructor validation should make this impossible for immutable inputs,
            # but fail closed rather than returning a fabricated/default context.
            raise ValueError(f"rotation static context is missing bar: {bar!r}")
        return context

    @staticmethod
    def _bar(value: object, label: str) -> str:
        bar = str(value or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError(f"{label} must be front or back")
        return bar


__all__ = ["RotationActiveBarContextResolverService"]
