from types import SimpleNamespace

import services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service as module
from services.extreme_structural_named_gear_mundus_food_potion_core_stat_record_service import (
    ExtremeStructuralNamedGearMundusFoodPotionCoreStatRecordService,
    _GEAR_DEFERRED_AXIS,
    _PASSIVE_DEFERRED_AXIS,
    _RESOURCE_ACTIVE_BAR_SCOPE,
    _RESOURCE_ARMOR_SCOPE,
    _RESOURCE_JEWELRY_GLYPH_IRRELEVANCE_SCOPE,
    _RESOURCE_JEWELRY_STATIC_TRAIT_SCOPE,
    _RESOURCE_JUGGERNAUT_SCOPE,
    _RESOURCE_MAX_HEALTH_RUNTIME_SCOPE,
    _RESOURCE_REMAINING_EQUIPMENT_TRAIT_AFTER_WEAPON_AXIS,
    _RESOURCE_REMAINING_PASSIVE_AFTER_REVIEWED_RESOURCE_AXIS,
    _RESOURCE_REMAINING_RUNTIME_STATE_AXIS,
    _RESOURCE_REMAINING_SKILL_BAR_AXIS,
    _RESOURCE_UNDAUNTED_SCOPE,
    _RESOURCE_WEAPON_IRRELEVANCE_SCOPE,
    _RUNTIME_STATE_DEFERRED_AXIS,
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


_JEWELRY_STATE = SimpleNamespace(
    objective_key="max_health",
    identity=(("Necklace", "Healthy"), ("Ring1", "Healthy"), ("Ring2", "Healthy")),
    direct_delta=2895.0,
)


class _JewelryTraitCatalog:
    objective_key = "max_health"
    denominator_proven = True
    unresolved = ()
    states = (_JEWELRY_STATE,)
    raw_loadouts_reviewed = 216


class _JewelryTraitService:
    def __init__(self, path):
        self.path = path

    def build(self, key):
        assert key == "max_health"
        return _JewelryTraitCatalog()


class _JewelryGlyphAudit:
    denominator_proven = True
    objective_irrelevance_proven = True
    glyphs_reviewed = 17
    relevant_glyphs = ()
    unresolved = ()


class _JewelryGlyphService:
    def __init__(self, path):
        self.path = path

    def build(self, key):
        assert key == "max_health"
        return _JewelryGlyphAudit()


class _WeaponAudit:
    denominator_proven = True
    objective_irrelevance_proven = True
    traits_reviewed = 9
    enchantments_reviewed = 21
    relevant_traits = ()
    relevant_enchantments = ()
    unresolved = ()


class _WeaponService:
    def __init__(self, path):
        self.path = path

    def build(self, key):
        assert key == "max_health"
        return _WeaponAudit()


_WINNER_PAYLOAD = {
    "potion": "alchemy_formula:test",
    "active_buffs": ("Major Fortitude",),
    "resource_armor_states_scored": 24,
    "jewelry_resource_static_trait_state": _JEWELRY_STATE.identity,
    "resource_active_bar_skills": (
        "Shadow Skill 1",
        "Shadow Skill 2",
        "Shadow Skill 3",
        "Shadow Skill 4",
        "Shadow Skill 5",
        "Shadow Ultimate",
    ),
    "resource_active_bar_shadow_slots": 6,
    "resource_active_bar_siphoning_slots": 0,
    "resource_active_bar_mages_guild_slots": 0,
    "resource_active_bar_reviewed_percent_bonus": 0.30,
    "resource_active_bar_denominator_proven": True,
    "resource_active_skills_reviewed": 88,
    "resource_max_health_runtime_state": (
        "nothing_wasted_10_stack",
        False,
        10,
        (123456,),
    ),
    "resource_max_health_runtime_label": "Nothing Wasted 10 stacks",
    "resource_max_health_runtime_permanent_pet_active": False,
    "resource_max_health_runtime_nothing_wasted_stacks": 10,
    "resource_max_health_runtime_class_mastery_ability_ids": (123456,),
    "resource_max_health_runtime_reviewed_percent_bonus": 0.20,
    "resource_max_health_runtime_conditions": (
        "Maximum 10-stack Nothing Wasted state; stacks require Corpse Consumption activity.",
    ),
    "resource_max_health_runtime_denominator_proven": True,
}


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
        return 50000.0, dict(_WINNER_PAYLOAD), ()


class _Probe:
    def potion_states(self):
        return (1, 2)

    food_evaluator = SimpleNamespace(
        food_choices=lambda: ("", "Food A"),
        mundus_evaluator=SimpleNamespace(mundus_choices=lambda: ("", "Lord", "Mage", "Tower")),
    )


class _ResourceFactory:
    captured_jewelry_state = None

    def __init__(self, **kwargs):
        type(self).captured_jewelry_state = kwargs.get("jewelry_state")

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
        _RUNTIME_STATE_DEFERRED_AXIS,
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
                payload=dict(_WINNER_PAYLOAD),
            ),
        )


def test_resource_armor_jewelry_weapon_mettle_juggernaut_bar_runtime_and_glyph_irrelevance_are_recorded(monkeypatch):
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
    monkeypatch.setattr(module, "ExtremeJewelryResourceStaticTraitStateService", _JewelryTraitService)
    monkeypatch.setattr(module, "ExtremeJewelryResourceGlyphRelevanceService", _JewelryGlyphService)
    monkeypatch.setattr(module, "ExtremeWeaponResourceRelevanceService", _WeaponService)
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
    assert _ResourceFactory.captured_jewelry_state is _JEWELRY_STATE
    assert _RESOURCE_ARMOR_SCOPE in record.search_coverage.searched
    assert _RESOURCE_UNDAUNTED_SCOPE in record.search_coverage.searched
    assert _RESOURCE_JUGGERNAUT_SCOPE in record.search_coverage.searched
    assert _RESOURCE_ACTIVE_BAR_SCOPE in record.search_coverage.searched
    assert _RESOURCE_MAX_HEALTH_RUNTIME_SCOPE in record.search_coverage.searched
    assert _RESOURCE_JEWELRY_STATIC_TRAIT_SCOPE in record.search_coverage.searched
    assert _RESOURCE_JEWELRY_GLYPH_IRRELEVANCE_SCOPE in record.search_coverage.searched
    assert _RESOURCE_WEAPON_IRRELEVANCE_SCOPE in record.search_coverage.searched
    assert _GEAR_DEFERRED_AXIS not in record.search_coverage.omitted
    assert "armor, jewelry, and weapon traits" not in record.search_coverage.omitted
    assert "glyphs/enchants" not in record.search_coverage.omitted
    assert _PASSIVE_DEFERRED_AXIS not in record.search_coverage.omitted
    assert "skill-bar choices and morphs" not in record.search_coverage.omitted
    assert _RUNTIME_STATE_DEFERRED_AXIS not in record.search_coverage.omitted
    assert _RESOURCE_REMAINING_EQUIPMENT_TRAIT_AFTER_WEAPON_AXIS in record.search_coverage.omitted
    assert _RESOURCE_REMAINING_PASSIVE_AFTER_REVIEWED_RESOURCE_AXIS in record.search_coverage.omitted
    assert _RESOURCE_REMAINING_SKILL_BAR_AXIS in record.search_coverage.omitted
    assert _RESOURCE_REMAINING_RUNTIME_STATE_AXIS in record.search_coverage.omitted
    assert not any("weapon trait" in row for row in record.search_coverage.omitted)
    assert not any("weapon glyph" in row for row in record.search_coverage.omitted)
    assert not any("jewelry and weapon glyphs/enchants" in row for row in record.search_coverage.omitted)
    assert record.search_coverage.candidates_screened == 10 * 2 * 24 * 4 * 2 * 2
    assert record.search_coverage.candidates_optimized == 10 * 2 * 24 * 4 * 2 * 2
    assert record.search_coverage.denominator_proven is False
    assert record.self_provided_conditions == ("Major Fortitude",)
    assert "Nothing Wasted" in " ".join(record.runtime_prerequisites)
    assert "10-stack" in " ".join(record.runtime_prerequisites)
    assert any("2,187" in row for row in record.explanation)
    assert any("216" in row for row in record.explanation)
    assert any("17" in row and "jewelry glyph" in row for row in record.explanation)
    assert any("9" in row and "21" in row and "weapon" in row for row in record.explanation)
    assert any("Undaunted Mettle" in row for row in record.explanation)
    assert any("Juggernaut" in row and "Heavy Armor" in row for row in record.explanation)
    assert any("88" in row and "active" in row.casefold() and "Dark Vigor" in row for row in record.explanation)
    assert any("Nothing Wasted 10 stacks" in row and "20%" in row for row in record.explanation)
