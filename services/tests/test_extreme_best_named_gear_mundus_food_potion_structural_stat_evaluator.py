from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_best_named_gear_mundus_food_potion_structural_stat_evaluator import (
    ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator,
)
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_gear_set_topology_catalog_service import ExtremeGearSetCountTopology
from services.extreme_named_gear_set_catalog_realization_service import (
    ExtremeNamedGearSetCatalogRealizationResult,
    ExtremeNamedGearSetTopologyRealizationResult,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationResult,
)


def _realization(set_id: int, name: str) -> ExtremeNamedGearSetRealization:
    return ExtremeNamedGearSetRealization(
        topology_signature="5|unused:7",
        set_ids=(set_id,),
        set_names=(name,),
        counts=(5,),
        weapon_shape=ExtremeWeaponSlotShape.NONE,
        assignments=(
            ExtremeNamedGearSlotAssignment("Chest", set_id, name),
            ExtremeNamedGearSlotAssignment("Hands", set_id, name),
            ExtremeNamedGearSlotAssignment("Waist", set_id, name),
            ExtremeNamedGearSlotAssignment("Legs", set_id, name),
            ExtremeNamedGearSlotAssignment("Feet", set_id, name),
        ),
    )


def _gear_result(*realizations, unresolved=(), denominator_proven=True):
    topology = ExtremeGearSetCountTopology(counts=(5,), unused_units=7)
    topology_result = ExtremeNamedGearSetTopologyRealizationResult(
        topology=topology,
        realizations=tuple(realizations),
        assignments_considered=len(realizations),
        assignments_rejected=0,
        truncated=not denominator_proven,
        unresolved=tuple(unresolved),
    )
    catalog = ExtremeNamedGearSetCatalogRealizationResult(
        topologies=(topology_result,),
        unresolved=tuple(unresolved),
    )
    return ExtremeObjectiveNamedGearSetCatalogRealizationResult(
        objective_key="max_health",
        realization=catalog,
        breakpoints_reviewed=4,
        breakpoints_retained_relevant=2,
        breakpoints_retained_unresolved=0,
        breakpoints_pruned_irrelevant=2,
        unresolved=tuple(unresolved),
    )


class _Scorer:
    def __init__(self, value, payload=None, unresolved=()):
        self.value = value
        self.payload = payload or {}
        self.unresolved = tuple(unresolved)
        self.calls = 0

    def __call__(self, objective_key, candidate):
        self.calls += 1
        return float(self.value), dict(self.payload), self.unresolved


def test_outer_gear_evaluator_scores_every_realization_and_picks_best():
    low = _realization(10, "Low")
    high = _realization(20, "High")
    scorers = {
        10: _Scorer(100.0, {"gear_set_ids": (10,)}),
        20: _Scorer(250.0, {"gear_set_ids": (20,)}),
    }
    evaluator = ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator(
        gear_realization=_gear_result(low, high),
        evaluator_factory=lambda realization: scorers[realization.set_ids[0]],
    )

    value, payload, unresolved = evaluator("max_health", SimpleNamespace())

    assert value == 250.0
    assert payload["gear_set_ids"] == (20,)
    assert payload["gear_candidates_scored"] == 2
    assert payload["gear_assignments_considered"] == 2
    assert payload["gear_assignments_realized"] == 2
    assert payload["gear_assignments_rejected"] == 0
    assert payload["gear_breakpoints_pruned_irrelevant"] == 2
    assert payload["gear_denominator_proven"] is True
    assert unresolved == ()
    assert scorers[10].calls == 1
    assert scorers[20].calls == 1


def test_ties_choose_deterministic_lowest_gear_identity():
    first = _realization(10, "First")
    second = _realization(20, "Second")
    evaluator = ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator(
        gear_realization=_gear_result(second, first),
        evaluator_factory=lambda realization: _Scorer(
            100.0,
            {"winner": realization.set_ids[0]},
        ),
    )

    _, payload, _ = evaluator("max_health", SimpleNamespace())

    assert payload["winner"] == 10


def test_unresolved_evidence_from_gear_and_candidate_is_preserved():
    gear = _realization(10, "Gear")
    evaluator = ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator(
        gear_realization=_gear_result(
            gear,
            unresolved=("gear catalog gap",),
            denominator_proven=False,
        ),
        evaluator_factory=lambda _realization: _Scorer(
            100.0,
            unresolved=("canonical score gap",),
        ),
    )

    _, payload, unresolved = evaluator("max_health", SimpleNamespace())

    assert payload["gear_denominator_proven"] is False
    assert unresolved == ("gear catalog gap", "canonical score gap")
    assert evaluator.gear_denominator_proven is False


def test_empty_realization_set_fails_closed():
    evaluator = ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator(
        gear_realization=_gear_result(),
        evaluator_factory=lambda _realization: _Scorer(0.0),
    )

    with pytest.raises(ValueError, match="no physically realized gear candidate"):
        evaluator("max_health", SimpleNamespace())


def test_per_gear_nested_evaluators_are_cached_between_structural_candidates():
    gear = _realization(10, "Gear")
    scorer = _Scorer(100.0)
    factory_calls = []

    def factory(realization):
        factory_calls.append(realization.set_ids)
        return scorer

    evaluator = ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator(
        gear_realization=_gear_result(gear),
        evaluator_factory=factory,
    )

    evaluator("max_health", SimpleNamespace())
    evaluator("max_health", SimpleNamespace())

    assert factory_calls == [(10,)]
    assert scorer.calls == 2
