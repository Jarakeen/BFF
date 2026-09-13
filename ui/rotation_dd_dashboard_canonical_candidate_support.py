from __future__ import annotations

from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_dd_execute_generation_context import (
    RotationDDExecuteGenerationContextResolver,
)


class RotationDDDashboardCanonicalCandidateSupport(
    RotationDashboardCanonicalCandidateSupport
):
    """Dashboard canonical candidate support with DD routing and execute wiring.

    The inherited canonical candidate pipeline is unchanged. This subclass only changes
    the default seed-generation dependency so DD plans with explicit complete priorities
    may consume the already-proven cross-bar WAIT routing path and, when the caller
    supplies explicit runtime execute context, the reviewed execute filler policy.
    Non-DD roles and ineligible DD requests are delegated unchanged by
    ``RotationDDCrossBarGenerationSupport``.

    Execute context is optional and never inferred from fight duration or dashboard
    display state. Callers may still inject an explicit generation dependency,
    preserving existing test doubles and research/custom generation paths.
    """

    def __init__(
        self,
        *,
        generation=None,
        execute_context_resolver: RotationDDExecuteGenerationContextResolver | None = None,
        **kwargs,
    ) -> None:
        if generation is None:
            generation = RotationDDCrossBarGenerationSupport(
                execute_context_resolver=execute_context_resolver,
            )
        elif (
            execute_context_resolver is not None
            and isinstance(generation, RotationDDCrossBarGenerationSupport)
        ):
            generation.execute_context_resolver = execute_context_resolver
        super().__init__(
            generation=generation,
            **kwargs,
        )


__all__ = ["RotationDDDashboardCanonicalCandidateSupport"]
