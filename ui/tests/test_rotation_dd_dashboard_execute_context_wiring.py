from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_dd_dashboard_canonical_candidate_support import (
    RotationDDDashboardCanonicalCandidateSupport,
)


def test_default_dd_dashboard_generation_accepts_execute_context_resolver() -> None:
    def resolver(**kwargs):
        return None

    support = RotationDDDashboardCanonicalCandidateSupport(
        execute_context_resolver=resolver,
    )

    assert isinstance(support.generation, RotationDDCrossBarGenerationSupport)
    assert support.generation.execute_context_resolver is resolver


def test_explicit_dd_generation_receives_execute_context_resolver() -> None:
    def resolver(**kwargs):
        return None

    generation = RotationDDCrossBarGenerationSupport()
    support = RotationDDDashboardCanonicalCandidateSupport(
        generation=generation,
        execute_context_resolver=resolver,
    )

    assert support.generation is generation
    assert generation.execute_context_resolver is resolver
