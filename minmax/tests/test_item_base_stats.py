from minmax.character_progression import CharacterProgression
from minmax.context_factory import BuildCalculationContextFactory
from minmax.gear_stat_inputs import GearCalculationInputs
from minmax.item_base_stats import BaseItemStatResolver
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild


class EmptyGearSetRepository:
    def get_set(self, name):
        return None

    def get_set_by_id(self, set_id):
        return None

    def get_bonuses(self, set_id):
        return []


def test_cp160_gold_heavy_chest_adds_both_resistances():
    build = PlayerBuild()
    build.Armor["Chest"].update(
        {
            "Set": "Test Armor",
            "Weight": "Heavy",
            "Quality": "Gold",
            "Level": "CP160",
        }
    )

    resolved = BaseItemStatResolver().apply(GearCalculationInputs(), build)

    physical = resolved.core.physical_resistance.flat
    spell = resolved.core.spell_resistance.flat
    assert physical[-1].label == "Chest: Heavy armor base"
    assert physical[-1].value == 2772
    assert spell[-1].value == 2772
    assert resolved.applied_effect_count == 2
    assert not resolved.unresolved


def test_context_factory_exposes_armor_base_in_core_trace():
    build = PlayerBuild()
    build.Armor["Waist"].update(
        {
            "Set": "Test Armor",
            "Weight": "Light",
            "Quality": "Gold",
            "Level": "CP160",
        }
    )
    factory = BuildCalculationContextFactory(gear_set_repository=EmptyGearSetRepository())

    context = factory.build(
        character_id="char",
        build_id="armor-base",
        build=build,
        progression=CharacterProgression(),
    )

    assert context.core_state.derived[StatId.PHYSICAL_RESISTANCE].final_value == 523
    assert context.core_state.derived[StatId.SPELL_RESISTANCE].final_value == 523
    assert any(
        label == "Waist: Light armor base" and value == 523
        for label, operation, value, result in context.core_state.derived[StatId.PHYSICAL_RESISTANCE].steps
    )


def test_cp160_gold_staff_replaces_naked_power_with_1335_via_adjustment():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            Set="Test Weapon",
            WeaponType="Inferno Staff",
            Quality="Gold",
            Level="CP160",
        )
    )
    factory = BuildCalculationContextFactory(gear_set_repository=EmptyGearSetRepository())

    context = factory.build(
        character_id="char",
        build_id="staff-base",
        build=build,
        progression=CharacterProgression(),
        active_bar="front",
    )

    weapon = context.core_state.derived[StatId.WEAPON_DAMAGE]
    spell = context.core_state.derived[StatId.SPELL_DAMAGE]
    assert weapon.final_value == 1335
    assert spell.final_value == 1335
    assert any(
        label == "Front Bar: Inferno Staff base weapon power (1335)" and value == 335
        for label, operation, value, result in spell.steps
    )


def test_two_handed_base_is_1571():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            Set="Test Weapon",
            WeaponType="Two-Handed",
            Quality="Gold",
            Level="CP160",
        )
    )
    context = BuildCalculationContextFactory(gear_set_repository=EmptyGearSetRepository()).build(
        character_id="char",
        build_id="two-hand",
        build=build,
        progression=CharacterProgression(),
    )

    assert context.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1571
    assert context.core_state.derived[StatId.SPELL_DAMAGE].final_value == 1571


def test_active_bar_uses_only_that_weapon_base():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Inferno Staff", Quality="Gold", Level="CP160"),
        BackBarWeapon=GearSlot(WeaponType="Two-Handed", Quality="Gold", Level="CP160"),
    )
    factory = BuildCalculationContextFactory(gear_set_repository=EmptyGearSetRepository())

    front = factory.build(
        character_id="char",
        build_id="front",
        build=build,
        progression=CharacterProgression(),
        active_bar="front",
    )
    back = factory.build(
        character_id="char",
        build_id="back",
        build=build,
        progression=CharacterProgression(),
        active_bar="back",
    )

    assert front.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1335
    assert back.core_state.derived[StatId.WEAPON_DAMAGE].final_value == 1571


def test_dual_wield_stays_explicitly_unresolved_until_two_weapon_model_exists():
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(
            WeaponType="Dual Wield",
            Quality="Gold",
            Level="CP160",
        )
    )

    resolved = BaseItemStatResolver().apply(GearCalculationInputs(), build)

    assert not resolved.core.weapon_damage.flat
    assert any("Dual Wield requires separate main/off-hand modeling" in entry for entry in resolved.unresolved)


def test_non_gold_or_non_cp160_armor_is_not_guessed():
    build = PlayerBuild()
    build.Armor["Head"].update(
        {
            "Set": "Test Armor",
            "Weight": "Medium",
            "Quality": "Purple",
            "Level": "CP160",
        }
    )

    resolved = BaseItemStatResolver().apply(GearCalculationInputs(), build)

    assert not resolved.core.physical_resistance.flat
    assert any("CP160 Gold required" in entry for entry in resolved.unresolved)


def test_weapon_type_round_trips_and_old_builds_default_blank():
    slot = GearSlot(WeaponType="Restoration Staff", Quality="Gold", Level="CP160")
    restored = GearSlot.from_dict(slot.to_dict())
    old = GearSlot.from_dict({"Set": "Old Set", "Quality": "Gold", "Level": "CP160"})

    assert restored.WeaponType == "Restoration Staff"
    assert old.WeaponType == ""
