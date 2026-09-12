from __future__ import annotations

"""Resolve canonical static build context from the bar active at an action instant."""

from dataclasses import dataclass, field

from minmax.build_calculation_context import BuildCalculationContext
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationActionKind, RotationPlan
from services.rotation_static_build_context_service import RotationStaticBuildContextResolution


@dataclass(frozen=True)
class RotationActiveBarContextResolverService:
    """Join canonical active-bar progression to resolved front/back static contexts.

    ``RotationActiveBarAssessor`` remains the single authority for ordered BAR_SWAP
    progression. This service only maps that already-resolved bar identity to the
    canonical static ``BuildCalculationContext`` for the saved build.
    """

    static_context: RotationStaticBuildContextResolution
    plan: RotationPlan
    initial_bar: str = "front"
    active_bar_assessor: RotationActiveBarAssessor = field(
        default_factory=RotationActiveBarAssessor,
        compare=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        # Normalize/validate through the existing bar authority rather than growing a
        # second private definition of valid rotation bars here.
        initial = self.active_bar_assessor.active_bar_at(
            self.plan,
            time_seconds=0.0,
            sequence=-0 if False else 0,
            initial_bar=self.initial_bar,
        )
        if self.static_context.context_for(initial) is None:
            raise ValueError(
                f"rotation static context is missing initial bar: {initial!r}"
            )
        object.__setattr__(self, "initial_bar", initial)

        # Validate all explicit destinations up front so later evaluation cannot become
        # only partially bar-aware after a candidate has already entered scoring.
        for action in self.plan.actions:
            if action.kind is not RotationActionKind.BAR_SWAP:
                continue
            destination = str(action.bar or "").strip().casefold()
            if self.static_context.context_for(destination) is None:
                raise ValueError(
                    f"rotation static context is missing bar: {destination!r}"
                )

    def active_bar_at(self, time_seconds: float, sequence: int | None = None) -> str:
        return self.active_bar_assessor.active_bar_at(
            self.plan,
            time_seconds=float(time_seconds),
            sequence=sequence,
            initial_bar=self.initial_bar,
        )

    def context_at(
        self,
        time_seconds: float,
        sequence: int | None = None,
    ) -> BuildCalculationContext:
        bar = self.active_bar_at(time_seconds, sequence)
        context = self.static_context.context_for(bar)
        if context is None:
            # Constructor validation should make this impossible for immutable inputs,
            # but fail closed rather than returning a fabricated/default context.
            raise ValueError(f"rotation static context is missing bar: {bar!r}")
        return context


__all__ = ["RotationActiveBarContextResolverService"]
