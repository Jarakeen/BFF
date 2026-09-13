from __future__ import annotations

from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport


class RotationDDDashboardCanonicalCandidateSupport(
    RotationDashboardCanonicalCandidateSupport
):
    """Dashboard canonical candidate support with DD cross-bar generation enabled.

    The inherited canonical candidate pipeline is unchanged. This subclass only changes
    the default seed-generation dependency so DD plans with explicit complete priorities
    may consume the already-proven cross-bar WAIT routing path. Non-DD roles and ineligible
    DD requests are delegated unchanged by ``RotationDDCrossBarGenerationSupport``.

    Callers may still inject an explicit generation dependency, preserving existing test
    doubles and research/custom generation paths.
    """

    def __init__(self, *, generation=None, **kwargs) -> None:
        super().__init__(
            generation=generation or RotationDDCrossBarGenerationSupport(),
            **kwargs,
        )


__all__ = ["RotationDDDashboardCanonicalCandidateSupport"]
