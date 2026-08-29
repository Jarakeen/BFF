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
