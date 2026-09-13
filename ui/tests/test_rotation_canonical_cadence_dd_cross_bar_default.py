from ui.rotation_canonical_cadence_orchestration_support import (
    RotationCanonicalCadenceOrchestrationSupport,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_dd_dashboard_canonical_candidate_support import (
    RotationDDDashboardCanonicalCandidateSupport,
)


def test_canonical_cadence_default_uses_dd_cross_bar_generation_boundary() -> None:
    support = RotationCanonicalCadenceOrchestrationSupport()

    assert isinstance(
        support.canonical_candidates,
        RotationDDDashboardCanonicalCandidateSupport,
    )
    assert isinstance(
        support.canonical_candidates.generation,
        RotationDDCrossBarGenerationSupport,
    )
