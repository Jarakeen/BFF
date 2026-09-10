from types import SimpleNamespace

import pytest

from services.extreme_best_named_gear_armor_mundus_food_potion_structural_stat_evaluator import (
    ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator,
)


class _ArmorState:
    def __init__(self, label: str, *, objective_key: str = "max_health"):
        self.label = label
        self.objective_key = objective_key
        self.identity = (("Head", label, "None"),)


class _ArmorCatalog:
    def __init__(self, states=(), *, proven=True, unresolved=(), objective_key="max_health"):
        self.objective_key = objective_key
        self.states = tuple(states)
        self.reviewed_traits = ("None", "Divines")
        self.unresolved = tuple(unresolved)
        self.reviewed_source_denominator_proven = proven


class _Gear:
    def __init__(self, set_id: int):
        self.set_ids = (set_id,)
        self.counts = (5,)
        self.weapon_shape = SimpleNamespace(value="none")
        self.assignments = ()


class _GearResult:
    def __init__(self, rows=(), *, proven=True, unresolved=()):
        self.denominator_proven = proven
        self.unresolved = tuple(unresolved)
        self.realization = SimpleNamespace(
            topologies=(SimpleNamespace(realizations=tuple(rows)),)
        )


class _Candidate:
    pass


def _factory(scores, unresolved=()):
    calls = []

    def factory(gear, armor):
        identity = (gear.set_ids[0], armor.label)
        calls.append(identity)

        def evaluator(objective_key, candidate):
            return scores[identity], {"winner": identity}, tuple(unresolved)

        return evaluator

    factory.calls = calls
    return factory


def test_scores_full_gear_by_armor_cross_product_and_reports_counts():
    gear = _GearResult((_Gear(10), _Gear(20)))
    armor = _ArmorCatalog((_ArmorState("A"), _ArmorState("B"), _ArmorState("C")))
    scores = {
        (10, "A"): 10.0,
        (10, "B"): 20.0,
        (10, "C"): 30.0,
        (20, "A"): 40.0,
        (20, "B"): 50.0,
        (20, "C"): 60.0,
    }
    factory = _factory(scores)
    evaluator = ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=gear,
        armor_catalog=armor,
        evaluator_factory=factory,
    )

    value, payload, unresolved = evaluator("max_health", _Candidate())

    assert value == 60.0
    assert payload["winner"] == (20, "C")
    assert payload["gear_candidates_scored"] == 2
    assert payload["armor_states_scored"] == 3
    assert payload["gear_armor_candidates_scored"] == 6
    assert payload["gear_denominator_proven"] is True
    assert payload["reviewed_armor_denominator_proven"] is True
    assert unresolved == ()
    assert len(factory.calls) == 6


def test_equal_score_uses_deterministic_combined_identity():
    gear = _GearResult((_Gear(20), _Gear(10)))
    armor = _ArmorCatalog((_ArmorState("B"), _ArmorState("A")))
    factory = _factory({
        (10, "A"): 100.0,
        (10, "B"): 100.0,
        (20, "A"): 100.0,
        (20, "B"): 100.0,
    })
    evaluator = ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=gear,
        armor_catalog=armor,
        evaluator_factory=factory,
    )

    value, payload, _ = evaluator("max_health", _Candidate())

    assert value == 100.0
    assert payload["winner"] == (10, "A")


def test_unresolved_from_catalogs_and_all_candidates_is_preserved():
    gear = _GearResult((_Gear(10),), proven=False, unresolved=("gear gap",))
    armor = _ArmorCatalog(
        (_ArmorState("A"),),
        proven=False,
        unresolved=("armor gap",),
    )
    factory = _factory({(10, "A"): 1.0}, unresolved=("candidate gap",))
    evaluator = ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=gear,
        armor_catalog=armor,
        evaluator_factory=factory,
    )

    _, payload, unresolved = evaluator("max_health", _Candidate())

    assert evaluator.gear_denominator_proven is False
    assert evaluator.reviewed_armor_denominator_proven is False
    assert payload["gear_denominator_proven"] is False
    assert payload["reviewed_armor_denominator_proven"] is False
    assert unresolved == ("gear gap", "armor gap", "candidate gap")


def test_objective_mismatch_fails_closed_before_scoring():
    evaluator = ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator(
        gear_realization=_GearResult((_Gear(10),)),
        armor_catalog=_ArmorCatalog((_ArmorState("A"),), objective_key="spell_damage"),
        evaluator_factory=_factory({(10, "A"): 1.0}),
    )

    with pytest.raises(ValueError, match="objective mismatch"):
        evaluator("max_health", _Candidate())


def test_empty_gear_or_armor_denominator_fails_closed():
    with pytest.raises(ValueError, match="no physically realized gear candidate"):
        ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator(
            gear_realization=_GearResult(()),
            armor_catalog=_ArmorCatalog((_ArmorState("A"),)),
            evaluator_factory=_factory({}),
        )("max_health", _Candidate())

    with pytest.raises(ValueError, match="no armor state"):
        ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator(
            gear_realization=_GearResult((_Gear(10),)),
            armor_catalog=_ArmorCatalog(()),
            evaluator_factory=_factory({}),
        )("max_health", _Candidate())
