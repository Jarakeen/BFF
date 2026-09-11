import sqlite3

from models.build_model import GearSlot, PlayerBuild
from services.extreme_resource_runtime_condition_state_service import (
    ExtremeResourceRuntimeConditionStateService,
)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE entity (id INTEGER PRIMARY KEY, entity_type TEXT, name TEXT)"
        )
        connection.execute(
            "INSERT INTO entity(entity_type, name) VALUES (?, ?)",
            ("food", "Bewitched Sugar Skulls"),
        )
        connection.execute(
            "INSERT INTO entity(entity_type, name) VALUES (?, ?)",
            ("drink", "Witchmother's Potent Brew"),
        )
    return path


def test_finite_stack_states_are_executable_without_build_mutation(tmp_path):
    service = ExtremeResourceRuntimeConditionStateService(_database(tmp_path))

    state = service.build(
        "max_magicka",
        required_conditions=(
            "escalating_fete_stacks:30",
            "prowlers_talisman_critical_stacks:10",
        ),
        build=PlayerBuild(),
    )

    assert state.projection_complete is True
    assert state.condition_context == {
        "escalating_fete_stacks:30",
        "prowlers_talisman_critical_stacks:10",
    }
    assert state.unresolved_conditions == ()


def test_destruction_staff_condition_uses_active_bar_weapon_type(tmp_path):
    service = ExtremeResourceRuntimeConditionStateService(_database(tmp_path))
    build = PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Inferno Staff"),
        BackBarWeapon=GearSlot(WeaponType="Two-Handed"),
    )

    front = service.build(
        "max_magicka",
        required_conditions=("destruction_staff_equipped",),
        build=build,
        active_bar="front",
    )
    back = service.build(
        "max_magicka",
        required_conditions=("destruction_staff_equipped",),
        build=build,
        active_bar="back",
    )

    assert front.projection_complete is True
    assert front.active_conditions == ("destruction_staff_equipped",)
    assert back.projection_complete is False
    assert back.active_conditions == ()
    assert any("Destruction Staff witness" in item for item in back.unresolved_conditions)


def test_food_and_drink_conditions_require_matching_canonical_provisioning_type(tmp_path):
    service = ExtremeResourceRuntimeConditionStateService(_database(tmp_path))

    food = service.build(
        "max_health",
        required_conditions=("food_buff_active",),
        build=PlayerBuild(),
        food="Bewitched Sugar Skulls",
    )
    wrong = service.build(
        "max_health",
        required_conditions=("food_buff_active",),
        build=PlayerBuild(),
        food="Witchmother's Potent Brew",
    )
    drink = service.build(
        "max_magicka",
        required_conditions=("drink_buff_active",),
        build=PlayerBuild(),
        food="Witchmother's Potent Brew",
    )

    assert food.projection_complete is True
    assert drink.projection_complete is True
    assert wrong.projection_complete is False
    assert any("not proven" in item for item in wrong.unresolved_conditions)


def test_slot_and_transformation_conditions_remain_explicit_blockers(tmp_path):
    service = ExtremeResourceRuntimeConditionStateService(_database(tmp_path))

    state = service.build(
        "max_health",
        required_conditions=(
            "armor_ability_slotted",
            "pet_active",
            "transformed",
        ),
        build=PlayerBuild(),
    )

    assert state.projection_complete is False
    assert state.active_conditions == ()
    assert len(state.unresolved_conditions) == 3
    assert all("materialization witness" in item for item in state.unresolved_conditions)


def test_unknown_runtime_condition_fails_closed(tmp_path):
    service = ExtremeResourceRuntimeConditionStateService(_database(tmp_path))

    state = service.build(
        "max_stamina",
        required_conditions=("future_eso_nonsense",),
        build=PlayerBuild(),
    )

    assert state.projection_complete is False
    assert state.active_conditions == ()
    assert state.unresolved_conditions == (
        "Unreviewed Extreme resource runtime condition: future_eso_nonsense",
    )
