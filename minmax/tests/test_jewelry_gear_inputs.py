from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild


class EmptyGearSetRepository:
    def get_set(self, name):
        return None

    def get_set_by_id(self, set_id):
        return None

    def get_bonuses(self, set_id):
        return []


class FakeJewelryGlyphRepository:
    def get_jewelry_glyph_effect_by_name(self, glyph_name, *, use_max_value=True):
        if glyph_name == "Glyph of Magicka Recovery":
            return [
                Effect(
                    operation=EffectOperation.ADD,
                    value=169,
                    source="Glyph of Magicka Recovery",
                    stat=StatId.MAGICKA_RECOVERY,
                    unit=EffectUnit.FLAT,
                )
            ]
        return []


class FakeJewelryTraitRepository:
    def get_infused_enchantment_percent(self, quality):
        return 60.0 if quality == "Gold" else None

    def get_static_effects(self, trait_name, *, quality, level):
        if quality != "Gold" or level != "CP160":
            return []
        if trait_name == "Triune":
            return [
                Effect(EffectOperation.ADD, 473, "Triune", stat=StatId.MAX_HEALTH),
                Effect(EffectOperation.ADD, 430, "Triune", stat=StatId.MAX_MAGICKA),
                Effect(EffectOperation.ADD, 430, "Triune", stat=StatId.MAX_STAMINA),
            ]
        if trait_name == "Protective":
            return [
                Effect(EffectOperation.ADD, 1824, "Protective", stat=StatId.PHYSICAL_RESISTANCE),
                Effect(EffectOperation.ADD, 1824, "Protective", stat=StatId.SPELL_RESISTANCE),
            ]
        return []


def test_infused_gold_jewelry_multiplies_glyph_before_resource_trace():
    build = PlayerBuild()
    build.Ring2 = GearSlot(
        Quality="Gold",
        Trait="Infused",
        Enchant="Magicka Recovery",
        EnchantTier="Truly Superb",
        Level="CP160",
    )
    factory = BuildCalculationContextFactory(
        gear_set_repository=EmptyGearSetRepository(),
        jewelry_glyph_repository=FakeJewelryGlyphRepository(),
        jewelry_trait_repository=FakeJewelryTraitRepository(),
    )

    context = factory.build(
        character_id="char",
        build_id="infused-jewelry",
        build=build,
        progression=CharacterProgression(),
    )

    expected = 169 * 1.60
    trace = context.character_state.traces[StatId.MAGICKA_RECOVERY]
    assert any(
        step.label == "Ring 2: Glyph of Magicka Recovery (Infused +60%)"
        and abs(step.value - expected) < 1e-12
        for step in trace.steps
    )
    assert context.gear_effects_applied == 1
    assert not context.unresolved_gear_effects


def test_infused_without_verified_quality_stays_unresolved():
    build = PlayerBuild()
    build.Necklace = GearSlot(
        Trait="Infused",
        Enchant="Magicka Recovery",
        EnchantTier="Truly Superb",
        Level="CP160",
    )
    resolver = GearStatInputResolver(
        EmptyGearSetRepository(),
        jewelry_glyph_repository=FakeJewelryGlyphRepository(),
        jewelry_trait_repository=FakeJewelryTraitRepository(),
    )

    resolved = resolver.resolve(build)

    assert resolved.magicka_recovery.item_flat == 0
    assert any("Infused jewelry value unavailable" in entry for entry in resolved.unresolved)


def test_gold_cp160_triune_feeds_all_three_resource_traces():
    build = PlayerBuild()
    build.Necklace = GearSlot(Quality="Gold", Trait="Triune", Level="CP160")
    factory = BuildCalculationContextFactory(
        gear_set_repository=EmptyGearSetRepository(),
        jewelry_trait_repository=FakeJewelryTraitRepository(),
    )

    context = factory.build(
        character_id="char",
        build_id="triune",
        build=build,
        progression=CharacterProgression(),
    )

    assert context.character_state.max_health == 10473
    assert context.character_state.max_magicka == 12430
    assert context.character_state.max_stamina == 12430
    assert any(step.label == "Necklace: Triune" and step.value == 473 for step in context.character_state.traces[StatId.MAX_HEALTH].steps)
    assert any(step.label == "Necklace: Triune" and step.value == 430 for step in context.character_state.traces[StatId.MAX_MAGICKA].steps)
    assert any(step.label == "Necklace: Triune" and step.value == 430 for step in context.character_state.traces[StatId.MAX_STAMINA].steps)
    assert context.gear_effects_applied == 3


def test_gold_cp160_protective_feeds_both_resistance_traces():
    build = PlayerBuild()
    build.Ring1 = GearSlot(Quality="Gold", Trait="Protective", Level="CP160")
    factory = BuildCalculationContextFactory(
        gear_set_repository=EmptyGearSetRepository(),
        jewelry_trait_repository=FakeJewelryTraitRepository(),
    )

    context = factory.build(
        character_id="char",
        build_id="protective",
        build=build,
        progression=CharacterProgression(),
    )

    physical = context.core_state.derived[StatId.PHYSICAL_RESISTANCE]
    spell = context.core_state.derived[StatId.SPELL_RESISTANCE]
    assert physical.final_value == 1824
    assert spell.final_value == 1824
    assert any(label == "Ring 1: Protective" and value == 1824 for label, operation, value, result in physical.steps)
    assert any(label == "Ring 1: Protective" and value == 1824 for label, operation, value, result in spell.steps)
    assert context.gear_effects_applied == 2


def test_arcane_is_explicitly_unresolved_when_numeric_source_is_missing():
    build = PlayerBuild()
    build.Ring2 = GearSlot(Quality="Gold", Trait="Arcane", Level="CP160")
    resolver = GearStatInputResolver(
        EmptyGearSetRepository(),
        jewelry_trait_repository=FakeJewelryTraitRepository(),
    )

    resolved = resolver.resolve(build)

    assert resolved.magicka.item_flat == 0
    assert any("numeric trait value is not present" in entry for entry in resolved.unresolved)
