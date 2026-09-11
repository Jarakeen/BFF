from types import SimpleNamespace

import services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service as module
from services.extreme_record_result import ExtremeRecordProofStatus
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
    _GEAR_DEFERRED_AXIS,
)


class _Optimizer:
    database_path = "fake.db"


class _GearRealization:
    def __init__(self, *, proven=True, unresolved=()):
        self.denominator_proven = proven
        self.unresolved = tuple(unresolved)
        self.breakpoints_reviewed = 12
        self.breakpoints_pruned_irrelevant = 7
        self.assignments_considered = 5
        self.assignments_realized = 3
        self.assignments_rejected = 2
        self.realization = SimpleNamespace(
            topologies=(
                SimpleNamespace(
                    realizations=(
                        SimpleNamespace(set_ids=(10,), counts=(5,), weapon_shape=SimpleNamespace(value="none"), assignments=()),
                        SimpleNamespace(set_ids=(20,), counts=(5,), weapon_shape=SimpleNamespace(value="none"), assignments=()),
                        SimpleNamespace(set_ids=(30,), counts=(2,), weapon_shape=SimpleNamespace(value="none"), assignments=()),
                    )
                ),
            )
        )


class _OuterEvaluator:
    current = None

    def __init__(self, *, gear_realization, evaluator_factory):
        self.gear_realization = gear_realization
        self.evaluator_factory = evaluator_factory
        self.gear_denominator_proven = bool(gear_realization.denominator_proven)
        _OuterEvaluator.current = self

    @property
    def unresolved(self):
        return tuple(self.gear_realization.unresolved)

    def gear_realizations(self):
        return tuple(self.gear_realization.realization.topologies[0].realizations)

    def __call__(self, objective_key, candidate):
        return 12345.0, {
            "potion": "alchemy_formula:test",
            "active_buffs": ("Major Fortitude",),
            "gear_set_names": ("Winner",),
        }, self.unresolved


class _Probe:
    def potion_states(self):
        return (1, 2)

    food_evaluator = SimpleNamespace(
        food_choices=lambda: ("", "Food A", "Food B"),
        mundus_evaluator=SimpleNamespace(mundus_choices=lambda: ("", "Lord", "Mage", "Ritual")),
    )


class _Factory:
    def __init__(self, **kwargs):
        pass

    def __call__(self, realization):
        return _Probe()


class _UniverseService:
    DEFERRED = (
        _GEAR_DEFERRED_AXIS,
        "armor, jewelry, and weapon traits",
        "glyphs/enchants",
        "Mundus",
        "food/drink",
        "potions",
        "skill-bar choices and morphs",
    )

    def __init__(self, path):
        pass


class _SearchService:
    current_result = None

    def __init__(self, universe_service, *, scorer):
        self.scorer = scorer

    def search(self, key):
        return _SearchService.current_result


def _patch(monkeypatch):
    monkeypatch.setattr(module, "ExtremeCanonicalStructuralStatEvaluator", lambda **kwargs: object())
    monkeypatch.setattr(module, "ExtremeHypotheticalClassProgressionService", lambda path: object())
    monkeypatch.setattr(module, "MundusRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "ProvisioningStaticRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "PotionAvailabilityRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "ExtremeNamedGearFiniteAxisEvaluatorFactory", _Factory)
    monkeypatch.setattr(module, "ExtremeBestNamedGearMundusFoodPotionStructuralStatEvaluator", _OuterEvaluator)
    monkeypatch.setattr(module, "ExtremeGlobalSearchUniverseService", _UniverseService)
    monkeypatch.setattr(module, "ExtremeStructuralGlobalSearchService", _SearchService)


def _result(*, omitted, unresolved=()):
    return SimpleNamespace(
        structural_scope=("races", "routes", "attributes", "bars"),
        deferred_dynamic_axes=tuple(omitted),
        structural_denominator_proven=True,
        candidates_scored=10,
        unresolved=tuple(unresolved),
        best=SimpleNamespace(
            value=12345.0,
            payload={
                "potion": "alchemy_formula:test",
                "active_buffs": ("Major Fortitude",),
                "gear_set_names": ("Winner",),
            },
        ),
    )


def test_proven_gear_axis_moves_from_omitted_to_searched_and_counts_full_product(monkeypatch):
    _patch(monkeypatch)
    gear = _GearRealization(proven=True)
    monkeypatch.setattr(
        ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
        "_gear_realization",
        lambda self, key: gear,
    )
    _SearchService.current_result = _result(omitted=_UniverseService.DEFERRED)

    # Physical penetration intentionally remains on the gear-only branch. The
    # max-resource objectives now exercise the joint resource armor/glyph branch.
    record = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        optimizer=_Optimizer()
    ).record("physical_penetration")

    assert _GEAR_DEFERRED_AXIS not in record.search_coverage.omitted
    assert "armor, jewelry, and weapon traits" in record.search_coverage.omitted
    assert "glyphs/enchants" in record.search_coverage.omitted
    assert record.search_coverage.candidates_screened == 10 * 3 * 4 * 3 * 2
    assert record.search_coverage.candidates_optimized == 10 * 3 * 4 * 3 * 2
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND
    assert record.runtime_prerequisites
    assert record.self_provided_conditions == ("Major Fortitude",)


def test_unproven_gear_axis_remains_omitted_and_propagates_unresolved(monkeypatch):
    _patch(monkeypatch)
    gear = _GearRealization(proven=False, unresolved=("unmapped gear bonus",))
    monkeypatch.setattr(
        ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
        "_gear_realization",
        lambda self, key: gear,
    )
    _SearchService.current_result = _result(omitted=_UniverseService.DEFERRED)

    record = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        optimizer=_Optimizer()
    ).record("physical_penetration")

    assert _GEAR_DEFERRED_AXIS in record.search_coverage.omitted
    assert record.search_coverage.denominator_proven is False
    assert "unmapped gear bonus" in record.unresolved
    assert record.proof_status is ExtremeRecordProofStatus.LOWER_BOUND


def test_no_scored_candidate_returns_unresolved_record(monkeypatch):
    _patch(monkeypatch)
    gear = _GearRealization(proven=True)
    monkeypatch.setattr(
        ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
        "_gear_realization",
        lambda self, key: gear,
    )
    result = _result(omitted=_UniverseService.DEFERRED)
    result.best = None
    _SearchService.current_result = result

    record = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        optimizer=_Optimizer()
    ).record("physical_penetration")

    assert record.raw_value is None
    assert record.proof_status is ExtremeRecordProofStatus.UNRESOLVED
    assert any("produced no scored candidate" in item for item in record.unresolved)


def test_cataloged_but_non_core_objective_fails_closed():
    service = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        optimizer=_Optimizer()
    )

    try:
        service.record("critical_heal")
    except ValueError as exc:
        assert "does not support objective" in str(exc)
    else:
        raise AssertionError("expected non-core objective to fail closed")
