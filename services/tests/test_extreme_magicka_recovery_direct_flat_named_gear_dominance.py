from types import SimpleNamespace

import pytest

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from tools.audit_extreme_magicka_recovery_direct_flat_named_gear_dominance import (
    abstract_topology_structural_upper_bound,
    direct_flat_upper_bound,
    dominance_row,
)
from tools.audit_extreme_magicka_recovery_ordinary_named_gear_frontier import PairScore


def _challenger(**overrides):
    values = {
        "set_id": 1,
        "set_name": "Fixture",
        "piece_count": 5,
        "recovery_kind": "conditional_flat",
        "recovery_flat_ceiling": 100.0,
        "recovery_percent_ceiling": None,
        "max_magicka_recovery_ceiling": 0.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _evidence(*, description: str, mapped_flat: float = 0.0):
    effects = ()
    if mapped_flat:
        effects = (
            Effect(
                stat=StatId.MAGICKA_RECOVERY,
                operation=EffectOperation.ADD,
                value=mapped_flat,
                unit=EffectUnit.FLAT,
                source="fixture",
                condition="runtime_condition",
            ),
        )
    candidate = SimpleNamespace(
        source_effects=effects,
        source_bonuses=(SimpleNamespace(description=description),),
    )
    return SimpleNamespace(
        set_name="Fixture",
        piece_count=5,
        candidate=candidate,
    )


def _pair(value: float, *, ordinary: bool = True) -> PairScore:
    return PairScore(
        direct_recovery=value,
        max_magicka_flat=0.0,
        optimistic_effective_recovery=value,
        ordinary=ordinary,
    )


def test_bastion_style_per_stack_description_raises_upper_bound_without_undercounting():
    challenger = _challenger(recovery_flat_ceiling=106.0)
    evidence = _evidence(
        mapped_flat=106.0,
        description=(
            "Blocking an attack grants you a stack of Inflection for 10 seconds, up to 3 stacks max. "
            "Increase your Magicka and Stamina Recovery by 106 per stack of Inflection."
        ),
    )

    upper = direct_flat_upper_bound(challenger, evidence)

    assert upper.mapped_flat == 106.0
    assert upper.triaged_flat == 106.0
    assert upper.description_flat == 318.0
    assert upper.total_special_ceiling == 424.0
    assert upper.pending_nonflat == ()


def test_description_percent_branch_stays_pending_instead_of_being_flattened():
    challenger = _challenger(recovery_kind="mapped_conditional_flat", recovery_flat_ceiling=129.0)
    evidence = _evidence(
        mapped_flat=129.0,
        description="Increases your Health, Magicka, and Stamina Recovery by 18%.",
    )

    upper = direct_flat_upper_bound(challenger, evidence)

    assert upper.pending_nonflat
    assert any("conditional_percent" in item for item in upper.pending_nonflat)


def test_max_magicka_cross_stat_headroom_is_granted_to_direct_flat_challenger():
    challenger = _challenger(
        recovery_flat_ceiling=160.0,
        max_magicka_recovery_ceiling=15.376,
    )
    evidence = _evidence(description="Each stack grants 160 Magicka Recovery.")

    upper = direct_flat_upper_bound(challenger, evidence)

    assert upper.max_magicka_recovery_ceiling == pytest.approx(15.376)
    assert upper.total_special_ceiling >= 175.376


def test_abstract_topology_bound_can_reuse_same_best_identity_and_stays_optimistic():
    challenger = _challenger(set_id=99, piece_count=5)
    topology = SimpleNamespace(
        topologies=(
            SimpleNamespace(counts=(5, 3, 3, 1)),
            SimpleNamespace(counts=(5, 5, 2)),
        )
    )
    scores = {
        (10, 3): _pair(300.0),
        (11, 3): _pair(250.0),
        (12, 1): _pair(100.0),
        (13, 5): _pair(400.0),
        (14, 2): _pair(80.0),
    }

    upper = abstract_topology_structural_upper_bound(challenger, scores, topology)

    # The 5+3+3+1 topology is allowed to reuse the same 300-point 3pc score twice.
    # That is intentionally impossible/optimistic and therefore safe for pruning.
    assert upper == pytest.approx(700.0)


def test_abstract_topology_bound_excludes_challenger_ordinary_identity():
    challenger = _challenger(set_id=99, piece_count=5)
    topology = SimpleNamespace(topologies=(SimpleNamespace(counts=(5, 3, 1)),))
    scores = {
        (99, 3): _pair(9999.0),
        (10, 3): _pair(300.0),
        (11, 1): _pair(100.0),
    }

    upper = abstract_topology_structural_upper_bound(challenger, scores, topology)

    assert upper == pytest.approx(400.0)


def test_dominance_row_preserves_survivor_at_or_above_incumbent():
    challenger = _challenger(set_id=7, set_name="Survivor")
    row = dominance_row(
        challenger=challenger,
        structural_score=900.0,
        special_ceiling=450.0,
        incumbent=1332.0,
    )

    assert row.optimistic_total == pytest.approx(1350.0)
    assert row.margin == pytest.approx(-18.0)
    assert not row.dominated


def test_dominance_row_closes_upper_bound_below_incumbent():
    challenger = _challenger(set_id=8, set_name="Dominated")
    row = dominance_row(
        challenger=challenger,
        structural_score=800.0,
        special_ceiling=400.0,
        incumbent=1332.0,
    )

    assert row.optimistic_total == pytest.approx(1200.0)
    assert row.margin == pytest.approx(132.0)
    assert row.dominated
