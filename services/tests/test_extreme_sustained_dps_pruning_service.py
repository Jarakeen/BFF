from __future__ import annotations

import pytest

from services.extreme_sustained_dps_pruning_service import (
    ExtremeSustainedDPSBoundEvidence,
    ExtremeSustainedDPSPruningDisposition,
    ExtremeSustainedDPSPruningService,
)


def _bound(key, upper, *, safe=True, unresolved=()):
    return ExtremeSustainedDPSBoundEvidence(
        candidate_key=key,
        upper_bound_dps=upper,
        proven_safe=safe,
        source="test-bound",
        unresolved=tuple(unresolved),
    )


def test_strictly_lower_proven_upper_bound_is_pruned() -> None:
    result = ExtremeSustainedDPSPruningService.prune(
        (_bound("A", 119999.0),),
        incumbent_dps=120000.0,
    )

    assert result.pruned_count == 1
    assert result.survivor_count == 0
    assert result.forced_open_count == 0
    assert result.decisions[0].disposition is ExtremeSustainedDPSPruningDisposition.PRUNED
    assert result.proof_safe is True


def test_equal_upper_bound_survives_to_preserve_tie_semantics() -> None:
    result = ExtremeSustainedDPSPruningService.prune(
        (_bound("Tie", 120000.0),),
        incumbent_dps=120000.0,
    )

    assert result.pruned_count == 0
    assert result.survivor_count == 1
    assert result.decisions[0].disposition is ExtremeSustainedDPSPruningDisposition.SURVIVOR
    assert "match or exceed" in result.decisions[0].reason


def test_tiny_float_noise_does_not_prune_equal_ceiling() -> None:
    result = ExtremeSustainedDPSPruningService.prune(
        (_bound("Noise", 120000.0 - 5e-10),),
        incumbent_dps=120000.0,
    )

    assert result.decisions[0].disposition is ExtremeSustainedDPSPruningDisposition.SURVIVOR


def test_missing_bound_forces_branch_open() -> None:
    result = ExtremeSustainedDPSPruningService.prune(
        (_bound("Unknown", None, unresolved=("bound unavailable",)),),
        incumbent_dps=120000.0,
    )

    row = result.decisions[0]
    assert row.disposition is ExtremeSustainedDPSPruningDisposition.FORCED_OPEN
    assert row.unresolved == ("bound unavailable",)
    assert result.forced_open_count == 1


def test_unproven_bound_forces_branch_open_even_when_below_incumbent() -> None:
    result = ExtremeSustainedDPSPruningService.prune(
        (_bound("Suspicious", 1.0, safe=False),),
        incumbent_dps=120000.0,
    )

    row = result.decisions[0]
    assert row.disposition is ExtremeSustainedDPSPruningDisposition.FORCED_OPEN
    assert "not proven pruning-safe" in row.reason
    assert result.pruned_count == 0


def test_mixed_frontier_reports_disposition_counts() -> None:
    result = ExtremeSustainedDPSPruningService.prune(
        (
            _bound("Prune", 100000.0),
            _bound("Tie", 120000.0),
            _bound("Beat", 130000.0),
            _bound("Unknown", None),
            _bound("Unproven", 90000.0, safe=False),
        ),
        incumbent_dps=120000.0,
    )

    assert result.pruned_count == 1
    assert result.survivor_count == 2
    assert result.forced_open_count == 2
    assert result.proof_safe is True


def test_duplicate_candidate_keys_fail_closed() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        ExtremeSustainedDPSPruningService.prune(
            (_bound("A", 1.0), _bound("A", 2.0)),
            incumbent_dps=0.0,
        )


@pytest.mark.parametrize("value", (-1.0, -0.001))
def test_negative_upper_bounds_fail_closed(value: float) -> None:
    with pytest.raises(ValueError, match="upper bound cannot be negative"):
        ExtremeSustainedDPSPruningService.prune(
            (_bound("A", value),),
            incumbent_dps=0.0,
        )


def test_negative_incumbent_fails_closed() -> None:
    with pytest.raises(ValueError, match="incumbent cannot be negative"):
        ExtremeSustainedDPSPruningService.prune((), incumbent_dps=-1.0)
