from types import SimpleNamespace

import services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service as module
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
    _GEAR_DEFERRED_AXIS,
    _PASSIVE_DEFERRED_AXIS,
    _RESOURCE_ARMOR_SCOPE,
    _RESOURCE_REMAINING_EQUIPMENT_TRAIT_AXIS,
    _RESOURCE_REMAINING_GLYPH_AXIS,
    _RESOURCE_REMAINING_PASSIVE_AXIS,
    _RESOURCE_UNDAUNTED_SCOPE,
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
                    SimpleNamespace(
                        set_ids=(10,), counts=(5,), weapon_shape=SimpleNamespace(value="none"), assignments=()
                    ),
                    SimpleNamespace(
                        set_ids=(20,), counts=(5,), weapon_shape=SimpleNamespace(value="none"), assignments=()
                    ),
                )
            ),
        )
    )


class _ResourceArmorCatalog:
    objective_key = "max_health"
    denominator_proven = True
    unresolved = ()
    states = tuple(SimpleNamespace(identity=(("weights", i), ("traits", i))) for i in range(24))
    weight_catalog = SimpleNamespace(
        states=(1, 2, 3),
        raw_loadouts_reviewed=2187,
        dominated_loadouts_pruned=2184,
    )
    trait_glyph_catalog = SimpleNamespace(
        glyph_choices_reviewed=2,
        dominated_states_pruned=100,
    )


class _TraitGlyphService:
    def __init__(self, path):
        self.path = path


class _CombinedResourceArmorStateService:
    SUPPORTED_OBJECTIVES = ("max_health", "max_magicka", "max_stamina")

    @classmethod
    def from_services(cls, key, *, trait_glyph_service):
        assert key == "max_health"
        assert isinstance(trait_glyph_service, _TraitGlyphService)
        return cls()

    def build(self, key):
        assert key == "max_health"
        return _ResourceArmorCatalog()


class _ResourceOuterEvaluator:
    def __init__(self, *, gear_realization, armor_catalog, evaluator_factory):
        self.gear_realization = gear_realization
        self.armor_catalog = armor_catalog
        self.evaluator_factory = evaluator_factory
        self.gear_denominator_proven = True
        self.reviewed_resource_armor_denominator_proven = True

    def gear_realizations(self):
        return tuple(self.gear_realization.realization.topologies[0].realizations)

    def armor_states(self):
        return tuple(self.armor_catalog.states)

    def __call__(self, objective_key, candidate):
        return 50000.0, {
            "potion": "alchemy_formula:test",
            "active_buffs": ("Major Fortitude",),
            "resource_armor_states_scored": 24,
        }, ()


class _Probe:
    def potion_states(self):
        return (1, 2)

    food_evaluator = SimpleNamespace(
        food_choices=lambda: ("", "Food A"),
        mundus_evaluator=SimpleNamespace(mundus_choices=lambda: ("", "Lord", "Mage", "Tower")),
    )


class _ResourceFactory:
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
        _PASSIVE_DEFERRED_AXIS,
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
                value=50000.0,
                payload={
                    "potion": "alchemy_formula:test",
                    "active_buffs": ("Major Fortitude",),
                    "resource_armor_states_scored": 24,
                },
            ),
        )


def test_resource_armor_weight_trait_glyph_and_mettle_are_searched_with_residuals(monkeypatch):
    undaunted_progression = object()
    captured = {}

    def canonical_factory(**kwargs):
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(module, "ExtremeCanonicalStructuralStatEvaluator", canonical_factory)
    monkeypatch.setattr(module, "ExtremeHypotheticalClassProgressionService", lambda path: object())
    monkeypatch.setattr(
        module,
        "ExtremeHypotheticalUndauntedProgressionService",
        lambda path: undaunted_progression,
    )
    monkeypatch.setattr(module, "MundusRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "ProvisioningStaticRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "PotionAvailabilityRepository", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "ExtremeArmorResourceTraitGlyphStateService", _TraitGlyphService)
    monkeypatch.setattr(
        module,
        "ExtremeArmorResourceWeightTraitGlyphStateService",
        _CombinedResourceArmorStateService,
    )
    monkeypatch.setattr(module, "ExtremeNamedGearResourceArmorFiniteAxisEvaluatorFactory", _ResourceFactory)
    monkeypatch.setattr(
        module,
        "ExtremeBestNamedGearResourceArmorMundusFoodPotionStructuralStatEvaluator",
        _ResourceOuterEvaluator,
    )
    monkeypatch.setattr(module, "ExtremeGlobalSearchUniverseService", _UniverseService)
    monkeypatch.setattr(module, "ExtremeStructuralGlobalSearchService", _SearchService)
    monkeypatch.setattr(
        ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
        "_gear_realization",
        lambda self, key: _GearRealization(),
    )

    record = ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService(
        optimizer=_Optimizer()
    ).record("max_health")

    assert captured["progression_service"] is undaunted_progression
    assert _RESOURCE_ARMOR_SCOPE in record.search_coverage.searched
    assert _RESOURCE_UNDAUNTED_SCOPE in record.search_coverage.searched
    assert _GEAR_DEFERRED_AXIS not in record.search_coverage.omitted
    assert "armor, jewelry, and weapon traits" not in record.search_coverage.omitted
    assert "glyphs/enchants" not in record.search_coverage.omitted
    assert _PASSIVE_DEFERRED_AXIS not in record.search_coverage.omitted
    assert _RESOURCE_REMAINING_EQUIPMENT_TRAIT_AXIS in record.search_coverage.omitted
    assert _RESOURCE_REMAINING_GLYPH_AXIS in record.search_coverage.omitted
    assert _RESOURCE_REMAINING_PASSIVE_AXIS in record.search_coverage.omitted
    assert "armor weight/passive interactions" not in " ".join(record.search_coverage.omitted)
    assert record.search_coverage.candidates_screened == 10 * 2 * 24 * 4 * 2 * 2
    assert record.search_coverage.candidates_optimized == 10 * 2 * 24 * 4 * 2 * 2
    assert record.search_coverage.denominator_proven is False
    assert record.self_provided_conditions == ("Major Fortitude",)
    assert any("2,187" in row for row in record.explanation)
    assert any("Undaunted Mettle" in row for row in record.explanation)
