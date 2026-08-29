from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.gear_sets import GearSet, GearSetBonus
from minmax.gear_stat_inputs import GearStatInputResolver
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild


class FakeGearSetRepository:
    def __init__(self):
        self.set = GearSet(id=1, name="Test Set", category="test", max_equip_count=5)
        self.bonuses = [
            GearSetBonus(id=1, set_id=1, piece_count=2, description="Adds 1096 Maximum Magicka"),
            GearSetBonus(id=2, set_id=1, piece_count=3, description="Adds 129 Weapon and Spell Damage"),
            GearSetBonus(id=3, set_id=1, piece_count=4, description="Adds 657 Critical Chance"),
        ]

    def get_set(self, name):
        return self.set if name == self.set.name else None

    def get_set_by_id(self, set_id):
        return self.set if set_id == self.set.id else None

    def get_bonuses(self, set_id):
        return list(self.bonuses) if set_id == self.set.id else []


class FakeArmorGlyphRepository:
    def get_armor_glyph_effect_by_name(self, glyph_name, *, use_max_value=True):
        if glyph_name == "Glyph of Magicka":
            return [
                Effect(
                    operation=EffectOperation.ADD,
                    value=868,
                    source="Glyph of Magicka",
                    stat=StatId.MAX_MAGICKA,
                    unit=EffectUnit.FLAT,
                )
            ]
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
        if glyph_name == "Glyph of Increase Physical Harm":
            return [
                Effect(
                    operation=EffectOperation.ADD,
                    value=174,
                    source="Glyph of Increase Physical Harm",
                    stat=StatId.WEAPON_DAMAGE,
                    unit=EffectUnit.FLAT,
                )
            ]
        return []


def _four_piece_build():
    build = PlayerBuild(AttributeMagicka=64)
    build.Armor["Head"]["Set"] = "Test Set"
    build.Armor["Chest"]["Set"] = "Test Set"
    build.Ring1 = GearSlot(Set="Test Set")
    build.FrontBarWeapon = GearSlot(Set="Test Set")
    return build


def test_equipped_set_counts_only_active_weapon_bar():
    build = PlayerBuild()
    build.Armor["Head"]["Set"] = "Body Set"
    build.Necklace = GearSlot(Set="Body Set")
    build.FrontBarWeapon = GearSlot(Set="Front Set", Set2="Front Set")
    build.BackBarWeapon = GearSlot(Set="Back Set", Set2="Back Set")

    front = GearStatInputResolver.equipped_set_counts(build, active_bar="front")
    back = GearStatInputResolver.equipped_set_counts(build, active_bar="back")

    assert front == {"Body Set": 2, "Front Set": 2}
    assert back == {"Body Set": 2, "Back Set": 2}


def test_static_set_bonuses_feed_resource_damage_and_critical_inputs():
    resolver = GearStatInputResolver(FakeGearSetRepository())
    resolved = resolver.resolve(_four_piece_build(), active_bar="front")

    assert resolved.magicka.set_flat == 1096
    assert resolved.magicka.set_contributions[0].label == "Test Set (2)"
    assert resolved.core.weapon_damage.flat[0].value == 129
    assert resolved.core.spell_damage.flat[0].value == 129

    expected_crit = 657 / (2 * 66 * 166)
    assert abs(resolved.core.weapon_critical.additive_after_percent[0].value - expected_crit) < 1e-12
    assert abs(resolved.core.spell_critical.additive_after_percent[0].value - expected_crit) < 1e-12
    assert resolved.applied_effect_count == 5


def test_context_factory_applies_static_gear_to_character_sheet_state():
    factory = BuildCalculationContextFactory(gear_set_repository=FakeGearSetRepository())
    build = _four_piece_build()
    context = factory.build(
        character_id="char",
        build_id="build",
        build=build,
        progression=CharacterProgression(attributes=AttributeAllocation(magicka=64)),
        active_bar="front",
    )

    assert context.character_state.max_magicka == 20200
    assert context.core_state is not None
    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1129
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1129
    assert abs(context.core_state.derived[StatId.WEAPON_CRITICAL].final_value - 0.12998357064622125) < 1e-12
    assert abs(context.core_state.derived[StatId.SPELL_CRITICAL].final_value - 0.12998357064622125) < 1e-12
    assert context.gear_effects_applied == 5
    assert context.gear_set_counts == (("Test Set", 4),)


def test_cp160_truly_superb_armor_glyph_adds_item_resource_with_named_trace():
    build = PlayerBuild(AttributeMagicka=64)
    build.Armor["Chest"].update({"Enchant": "Max Magicka", "EnchantTier": "Truly Superb", "Level": "CP160"})
    factory = BuildCalculationContextFactory(
        gear_set_repository=FakeGearSetRepository(),
        armor_glyph_repository=FakeArmorGlyphRepository(),
    )

    context = factory.build(
        character_id="char",
        build_id="glyph-build",
        build=build,
        progression=CharacterProgression(attributes=AttributeAllocation(magicka=64)),
    )

    assert context.character_state.max_magicka == 19972
    trace = context.character_state.traces[StatId.MAX_MAGICKA]
    assert any(step.label == "Chest: Glyph of Magicka" and step.value == 868 for step in trace.steps)
    assert context.gear_effects_applied == 1


def test_non_max_armor_glyph_is_left_unresolved_until_scaling_is_verified():
    build = PlayerBuild()
    build.Armor["Chest"].update({"Enchant": "Max Magicka", "EnchantTier": "Superb", "Level": "CP150"})
    resolver = GearStatInputResolver(FakeGearSetRepository(), armor_glyph_repository=FakeArmorGlyphRepository())

    resolved = resolver.resolve(build)

    assert resolved.magicka.item_flat == 0
    assert any("needs verified level/tier scaling" in entry for entry in resolved.unresolved)


def test_cp160_truly_superb_jewelry_recovery_glyph_adds_named_resource_trace():
    build = PlayerBuild()
    build.Necklace = GearSlot(Enchant="Magicka Recovery", EnchantTier="Truly Superb", Level="CP160")
    factory = BuildCalculationContextFactory(
        gear_set_repository=FakeGearSetRepository(),
        jewelry_glyph_repository=FakeJewelryGlyphRepository(),
    )

    context = factory.build(
        character_id="char",
        build_id="jewelry-recovery",
        build=build,
        progression=CharacterProgression(),
    )

    trace = context.character_state.traces[StatId.MAGICKA_RECOVERY]
    assert any(step.label == "Necklace: Glyph of Magicka Recovery" and step.value == 169 for step in trace.steps)
    assert context.gear_effects_applied == 1


def test_cp160_truly_superb_jewelry_damage_glyph_feeds_core_trace():
    build = PlayerBuild()
    build.Ring1 = GearSlot(Enchant="Weapon Damage", EnchantTier="Truly Superb", Level="CP160")
    factory = BuildCalculationContextFactory(
        gear_set_repository=FakeGearSetRepository(),
        jewelry_glyph_repository=FakeJewelryGlyphRepository(),
    )

    context = factory.build(
        character_id="char",
        build_id="jewelry-damage",
        build=build,
        progression=CharacterProgression(),
    )

    trace = context.core_state.derived[StatId.WEAPON_DAMAGE]
    assert trace.final_value == 1174
    assert any(label == "Ring 1: Glyph of Increase Physical Harm" and value == 174 for label, operation, value, result in trace.steps)
    assert context.gear_effects_applied == 1


def test_infused_jewelry_without_trait_repository_stays_unresolved():
    build = PlayerBuild()
    build.Ring2 = GearSlot(
        Trait="Infused",
        Enchant="Magicka Recovery",
        EnchantTier="Truly Superb",
        Level="CP160",
    )
    resolver = GearStatInputResolver(
        FakeGearSetRepository(),
        jewelry_glyph_repository=FakeJewelryGlyphRepository(),
    )

    resolved = resolver.resolve(build)

    assert resolved.magicka_recovery.item_flat == 0
    assert any("Infused jewelry trait repository unavailable" in entry for entry in resolved.unresolved)


def test_non_max_jewelry_glyph_is_left_unresolved_until_scaling_is_verified():
    build = PlayerBuild()
    build.Necklace = GearSlot(Enchant="Stamina Recovery", EnchantTier="Superb", Level="CP150")
    resolver = GearStatInputResolver(
        FakeGearSetRepository(),
        jewelry_glyph_repository=FakeJewelryGlyphRepository(),
    )

    resolved = resolver.resolve(build)

    assert resolved.stamina_recovery.item_flat == 0
    assert any("needs verified level/tier scaling" in entry for entry in resolved.unresolved)
