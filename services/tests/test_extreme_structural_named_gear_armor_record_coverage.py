from types import SimpleNamespace

import services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service as module
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
    _GEAR_DEFERRED_AXIS,
    _REMAINING_EQUIPMENT_TRAIT_AXIS,
    _REVIEWED_ARMOR_SCOPE,
)


class _Optimizer:
    database_path = "fake.db"


class _GearRealization:
    denominator_proven = True
    unresolved = ()
    breakpoints_reviewed = 12
    breakpoints_pruned_irrelevant = 7
    assignments_considered = 5
    assignments_realized = 2
    assignments_rejected = 3
    realization = SimpleNamespace(
        topologies=(
            SimpleNamespace(
                realizations=(
                    SimpleNamespace(set_ids=(10,), counts=(5,), weapon_shape=SimpleNamespace(value="none"), assignments=()),
                    SimpleNamespace(set_ids=(20,), counts=(5,), weapon_shape=SimpleNamespace(value="none"), assignments=()),
                )
            ),
        )
    )


class _ArmorCatalog:
    objective_key = "physical_resistance"
    reviewed_traits = ("None", "Divines", "Reinforced", "Nirnhoned", "Invigorating")
    reviewed_source_denominator_proven = True
    unresolved = ()
    states = (
        SimpleNamespace(identity=(("Head", "Heavy", "Reinforced"),)),
        SimpleNamespace(identity=(("Head", "Light", "Divines"),)),
        SimpleNamespace(identity=(("Head", "Medium", "None"),)),
    )


class _ArmorStateService:
    REVIEWED_OBJECTIVES = ("physical_resistance",)

    @classmethod
    def build(cls, key):
        assert key == "physical_resistance"
        return _ArmorCatalog()


class _ArmorOuterEvaluator:
    def __init__(self, *, gear_realization, armor_catalog, evaluator_factory):
        self.gear_realization = gear_realization
        self.armor_catalog = armor_catalog
        self.evaluator_factory = evaluator_factory
        self.gear_denominator_proven = True
        self.reviewed_armor_denominator_proven = True

    def gear_realizations(self):
        return tuple(self.gear_realization.realization.topologies[0].realizations)

    def armor_states(self):
        return tuple(self.armor_catalog.states)

    def __call__(self, objective_key, candidate):
        return 33000.0, {
            "potion": "alchemy_formula:test",
            "active_buffs": ("Major Resolve",),
            "armor_states_scored": 3,
        }, ()


class _Probe:
    def potion_states(self):
        return (1, 2)

    food_evaluator = SimpleNamespace(
        food_choices=lambda: ("", "Food A"),
        mundus_evaluator=SimpleNamespace(mundus_choices=lambda: ("", "Lady", "Lord", "Steed")),
    )


class _ArmorFactory:
    def __init__(self, **kwargs):
        pass

    def __call__(self, realization, armor_state):
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
    def __init__(self, universe_service, *, scorer):
        self.scorer = scorer

    def search(self, key):
        return SimpleNamespace(
            structural_scope=("races", "routes", "attributes", "bars"),
            deferred_dynamic_axes=_UniverseService.DEFERRED,
            structural_denominator_proven=True,
            candidates_scored=10,
            unresolved=(),
            best=SimpleNamespace(
                value=33000.0,
                payload={
                    "potion": "alchemy_formula:test",
                    "active_buffs": ("Major Resolve",),
                    "armor_states_scored": 3,
                },
            ),
        )


def test_reviewed_armor_axis_is_searched_and_residual_traits_remain_omitted(monkeypatch):
    monkeypatch.setattr(module, "ExtremeCanonicalStructuralStatEvaluator", lambda **kwargs: object())
    monkeypatch.setattr(module, "ExtremeHypotheticalClassProgressionService", lambda path: object())
    monkeypatch.setattr(module, "MundusRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "ProvisioningStaticRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "PotionAvailabilityRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "ExtremeArmorWeightTraitStateService", _ArmorStateService)
    monkeypatch.setattr(module, "ExtremeNamedGearArmorFiniteAxisEvaluatorFactory", _ArmorFactory)
    monkeypatch.setattr(module, "ExtremeBestNamedGearArmorMundusFoodPotionStructuralStatEvaluator", _ArmorOuterEvaluator)
    monkeypatch.setattr(module, "ExtremeGlobalSearchUniverseService", _UniverseService)
    monkeypatch.setattr(module, "ExtremeStructuralGlobalSearchService", _SearchService)
    monkeypatch.setattr(
        ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
        "_gear_realization",
        lambda self, key: _GearRealization(),
    )

    record = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        optimizer=_Optimizer()
    ).record("physical_resistance")

    assert _REVIEWED_ARMOR_SCOPE in record.search_coverage.searched
    assert _GEAR_DEFERRED_AXIS not in record.search_coverage.omitted
    assert "armor, jewelry, and weapon traits" not in record.search_coverage.omitted
    assert _REMAINING_EQUIPMENT_TRAIT_AXIS in record.search_coverage.omitted
    assert record.search_coverage.candidates_screened == 10 * 2 * 3 * 4 * 2 * 2
    assert record.search_coverage.candidates_optimized == 10 * 2 * 3 * 4 * 2 * 2
    assert record.search_coverage.denominator_proven is False
    assert record.self_provided_conditions == ("Major Resolve",)
