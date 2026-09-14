from types import SimpleNamespace

import pytest

from services.extreme_gear_set_recovery_special_branch_service import ExtremeRecoverySpecialBranchKind
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_screen import (
    aggregate_recovery_semantic_branch,
    distinct_set_capacity_upper_bound,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import PairScore


def _score(value: float, *, ordinary: bool = True) -> PairScore:
    return PairScore(
        direct_recovery=float(value),
        max_magicka_flat=0.0,
        optimistic_effective_recovery=float(value),
        ordinary=ordinary,
    )


def _evidence(*descriptions: str):
    candidate = SimpleNamespace(
        source_bonuses=tuple(SimpleNamespace(description=value) for value in descriptions),
        unresolved=(),
    )
    return SimpleNamespace(
        set_name="Fixture",
        piece_count=5,
        candidate=candidate,
    )


def test_capacity_bound_uses_each_set_identity_at_most_once():
    challenger = SimpleNamespace(set_id=99, piece_count=5)
    pair_scores = {
        (1, 3): _score(300.0),
        (1, 1): _score(200.0),
        (2, 3): _score(250.0),
        (3, 1): _score(100.0),
    }

    assert distinct_set_capacity_upper_bound(challenger, pair_scores) == pytest.approx(650.0)


def test_capacity_bound_can_leave_units_unused():
    challenger = SimpleNamespace(set_id=99, piece_count=10)
    pair_scores = {
        (1, 3): _score(500.0),
        (2, 1): _score(80.0),
    }

    assert distinct_set_capacity_upper_bound(challenger, pair_scores) == pytest.approx(80.0)


def test_capacity_bound_excludes_challenger_identity_and_nonordinary_pairs():
    challenger = SimpleNamespace(set_id=7, piece_count=5)
    pair_scores = {
        (7, 1): _score(999.0),
        (1, 3): _score(300.0),
        (2, 3): _score(250.0, ordinary=False),
        (3, 1): _score(100.0),
    }

    assert distinct_set_capacity_upper_bound(challenger, pair_scores) == pytest.approx(400.0)


def test_capacity_bound_rejects_impossible_challenger_piece_count():
    challenger = SimpleNamespace(set_id=1, piece_count=13)
    assert distinct_set_capacity_upper_bound(challenger, {}) is None


def test_aggregate_semantics_recovers_split_stack_ceiling():
    evidence = _evidence(
        "Blocking an attack grants you a stack of Inflection for 10 seconds, up to 3 stacks max.",
        "Increase your Magicka and Stamina Recovery by 106 per stack of Inflection.",
    )

    row = aggregate_recovery_semantic_branch(evidence)

    assert row is not None
    assert row.kind is ExtremeRecoverySpecialBranchKind.STACKED_FLAT
    assert row.flat_ceiling == pytest.approx(318.0)


def test_aggregate_semantics_preserves_max_magicka_scaled_formula():
    evidence = _evidence(
        "Adds 1096 Maximum Magicka.",
        "Adds 1096 Maximum Magicka.",
        "Adds 1096 Maximum Magicka.",
        "Gain 1 Magicka Recovery for every 100 Max Magicka you have. Current Increase: 120 Magicka Recovery.",
    )

    row = aggregate_recovery_semantic_branch(evidence)

    assert row is not None
    assert row.kind is ExtremeRecoverySpecialBranchKind.FORMULA
    assert row.formula_numerator == pytest.approx(1.0)
    assert row.formula_denominator == pytest.approx(100.0)
    assert row.formula_resource == "max_magicka"
