from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
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

    assert context.character_state.max_magicka == 22200
    assert context.core_state is not None
    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1129
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1129
    assert abs(context.core_state.derived[StatId.WEAPON_CRITICAL].final_value - 0.12998357064622125) < 1e-12
    assert abs(context.core_state.derived[StatId.SPELL_CRITICAL].final_value - 0.12998357064622125) < 1e-12
    assert context.gear_effects_applied == 5
    assert context.gear_set_counts == (("Test Set", 4),)
