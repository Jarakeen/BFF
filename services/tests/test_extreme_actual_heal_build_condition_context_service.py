from __future__ import annotations

import sqlite3

from models.build_model import PlayerBuild
from services.extreme_actual_heal_build_condition_context_service import (
    ExtremeActualHealBuildConditionContextService,
)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE entity(id INTEGER PRIMARY KEY, entity_type TEXT, name TEXT)"
        )
        connection.execute(
            "INSERT INTO entity(entity_type, name) VALUES ('food', 'Dubious Food')"
        )
        connection.execute(
            "INSERT INTO entity(entity_type, name) VALUES ('drink', 'Dubious Drink')"
        )
    return path


def test_food_and_destruction_staff_are_proven_from_build(tmp_path) -> None:
    build = PlayerBuild(Food="Dubious Food")
    build.FrontBarWeapon.WeaponType = "Restoration Staff"
    build.BackBarWeapon.WeaponType = "Inferno Staff"

    result = ExtremeActualHealBuildConditionContextService(_database(tmp_path)).resolve(
        build,
        active_bar="back",
    )

    assert result.condition_context == frozenset(
        {"food_buff_active", "destruction_staff_equipped"}
    )
    assert result.unresolved == ()


def test_drink_and_explicit_transformed_form_are_proven(tmp_path) -> None:
    build = PlayerBuild(Food="Dubious Drink", TransformedForm="werewolf")

    result = ExtremeActualHealBuildConditionContextService(_database(tmp_path)).resolve(build)

    assert result.condition_context == frozenset({"drink_buff_active", "transformed"})
    assert result.unresolved == ()


def test_unknown_selected_provisioning_fails_closed(tmp_path) -> None:
    build = PlayerBuild(Food="Mystery Stew")

    result = ExtremeActualHealBuildConditionContextService(_database(tmp_path)).resolve(build)

    assert result.condition_context == frozenset()
    assert result.unresolved == (
        "Selected provisioning item has no canonical food/drink type: Mystery Stew",
    )


def test_runtime_conditions_are_not_invented(tmp_path) -> None:
    build = PlayerBuild()
    build.FrontBarSkills[0] = "Some Pet Skill"

    result = ExtremeActualHealBuildConditionContextService(_database(tmp_path)).resolve(build)

    assert "pet_active" not in result.condition_context
    assert "standing_still" not in result.condition_context
    assert "dodge" not in result.condition_context
