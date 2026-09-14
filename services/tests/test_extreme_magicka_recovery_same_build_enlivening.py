from types import SimpleNamespace

import pytest

from services.extreme_recovery_class_route_frontier_service import (
    ExtremeRecoveryClassRouteCandidate,
)
from tools.audit_extreme_magicka_recovery_same_build_enlivening import (
    exact_enlivening_value,
    prove_route_lock,
)


def _candidate(name: str, *, delta: float, slope: float):
    return ExtremeRecoveryClassRouteCandidate(
        objective_key="magicka_recovery",
        base_class=name,
        equipped_skill_lines=(name,),
        is_pure_class=False,
        static_flat=0.0,
        static_percent=slope,
        slot_projected_delta=0.0,
        mastery_projected_delta=0.0,
        projected_delta=delta,
        slot_counts=(),
        reviewed_sources=(),
        runtime_obligations=(),
    )


class _FrontierService:
    def __init__(self, *, winner_slope: float, challenger_slope: float):
        self.winner_slope = winner_slope
        self.challenger_slope = challenger_slope

    def frontier(self, objective_key: str, *, reference_value: float):
        assert objective_key == "magicka_recovery"
        winner = _candidate(
            "winner",
            delta=100.0 + reference_value * self.winner_slope,
            slope=self.winner_slope,
        )
        challenger = _candidate(
            "challenger",
            delta=90.0 + reference_value * self.challenger_slope,
            slope=self.challenger_slope,
        )
        rows = tuple(sorted((winner, challenger), key=lambda row: -row.projected_delta))
        return SimpleNamespace(
            candidates=rows,
            best_reviewed_candidate=rows[0],
        )


def test_exact_enlivening_value_scales_below_cap():
    assert exact_enlivening_value(25932.744) == pytest.approx(129.66372)


def test_exact_enlivening_value_caps_at_thirty_thousand_magicka():
    assert exact_enlivening_value(30000.0) == 150.0
    assert exact_enlivening_value(50000.0) == 150.0


def test_route_lock_accepts_winner_that_starts_ahead_and_has_higher_slope():
    proof = prove_route_lock(
        _FrontierService(winner_slope=0.53, challenger_slope=0.38),
        reference_value=3000.0,
    )

    assert proof.winner is not None
    assert proof.winner.base_class == "winner"
    assert proof.winner_slope == pytest.approx(0.53)
    assert proof.minimum_margin is not None and proof.minimum_margin > 0.0
    assert proof.globally_locked_above_reference is True


def test_route_lock_rejects_winner_when_challenger_has_higher_slope():
    proof = prove_route_lock(
        _FrontierService(winner_slope=0.20, challenger_slope=0.30),
        reference_value=0.0,
    )

    assert proof.winner is not None
    assert proof.winner.base_class == "winner"
    assert proof.globally_locked_above_reference is False
