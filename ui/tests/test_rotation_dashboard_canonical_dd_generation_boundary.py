from __future__ import annotations

from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_dd_cross_bar_generation_support import RotationDDCrossBarGenerationSupport
from ui.rotation_generation_support import RotationGenerationSupport


class _CustomGeneration:
    pass


def test_real_dashboard_generation_is_wrapped_for_dd_cross_bar_routing() -> None:
    base = RotationGenerationSupport()
    support = RotationDashboardCanonicalCandidateSupport(generation=base)

    assert isinstance(support.generation, RotationDDCrossBarGenerationSupport)
    assert support.generation.base is base


def test_existing_dd_cross_bar_wrapper_is_not_double_wrapped() -> None:
    wrapped = RotationDDCrossBarGenerationSupport()
    support = RotationDashboardCanonicalCandidateSupport(generation=wrapped)

    assert support.generation is wrapped


def test_custom_generation_adapter_is_preserved_unchanged() -> None:
    custom = _CustomGeneration()
    support = RotationDashboardCanonicalCandidateSupport(generation=custom)  # type: ignore[arg-type]

    assert support.generation is custom
