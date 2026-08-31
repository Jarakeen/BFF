from __future__ import annotations

import sqlite3
from pathlib import Path

from models.build_model import PlayerBuild

from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_final_action_cost import BuildFinalActionCostResolver
from minmax.character_progression import CharacterProgression
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.resource_cost_modifiers import CostModifierOperation
from minmax.resource_costs import ResourceType, resolve_base_action_cost


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    if path.exists():
        return path

    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE jewelry_glyph (
                item_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );
            CREATE TABLE jewelry_glyph_effect (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                glyph_item_id INTEGER NOT NULL,
                effect_type TEXT,
                value_min REAL,
                value_max REAL,
                unit TEXT,
                description TEXT
            );
            """
        )
    return path


def _resolver(tmp_path: Path) -> BuildActionCostModifierResolver:
    path = _database(tmp_path)
    return BuildActionCostModifierResolver(
        JewelryCostModifierRepository(path),
        JewelryTraitRepository(path),
    )


def _armor(*weights: str) -> dict[str, dict[str, str]]:
    slots = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
    result = {slot: {"Weight": ""} for slot in slots}
    for slot, weight in zip(slots, weights):
        result[slot]["Weight"] = weight
    return result


def test_breton_magicka_mastery_is_seven_percent_magicka_only(tmp_path: Path) -> None:
    result = _resolver(tmp_path).resolve(PlayerBuild(Race="Breton"))

    assert result.unresolved == ()
    assert len(result.modifiers.modifiers) == 1
    modifier = result.modifiers.modifiers[0]
    assert modifier.source == "Breton: Magicka Mastery"
    assert modifier.operation is CostModifierOperation.PERCENT_REDUCTION
    assert modifier.value == 0.07
    assert modifier.resources == (ResourceType.MAGICKA,)


def test_imperial_red_diamond_is_six_percent_all_modeled_resources(tmp_path: Path) -> None:
    result = _resolver(tmp_path).resolve(PlayerBuild(Race="Imperial"))

    modifier = result.modifiers.modifiers[0]
    assert modifier.value == 0.06
    assert modifier.resources == (
        ResourceType.HEALTH,
        ResourceType.MAGICKA,
        ResourceType.STAMINA,
        ResourceType.ULTIMATE,
    )


def test_redguard_martial_training_is_scoped_to_weapon_skill_lines(tmp_path: Path) -> None:
    result = _resolver(tmp_path).resolve(PlayerBuild(Race="Redguard"))
    modifier = result.modifiers.modifiers[0]

    resto = resolve_base_action_cost(
        ability_id=1,
        base_cost=1000,
        base_mechanic=1,
        rank=4,
        morph=0,
    )
    class_skill = resolve_base_action_cost(
        ability_id=2,
        base_cost=1000,
        base_mechanic=1,
        rank=4,
        morph=0,
    )

    assert modifier.value == 0.08
    assert modifier.applies_to(resto, skill_line="Restoration Staff")
    assert not modifier.applies_to(class_skill, skill_line="Green Balance")


def test_evocation_requires_light_armor_skill_line_ownership(tmp_path: Path) -> None:
    build = PlayerBuild(
        Armor=_armor("Light", "Light", "Light", "Light", "Light", "Medium", "Heavy")
    )

    without_owned = _resolver(tmp_path).resolve(build)
    assert without_owned.modifiers.modifiers == ()

    progression = CharacterProgression(owned_skill_lines=("Light Armor",))
    with_owned = _resolver(tmp_path).resolve(build, progression=progression)

    assert len(with_owned.modifiers.modifiers) == 1
    modifier = with_owned.modifiers.modifiers[0]
    assert modifier.source == "Light Armor: Evocation (5 pieces)"
    assert modifier.value == 0.10
    assert modifier.resources == (ResourceType.MAGICKA,)


def test_evocation_counts_only_equipped_light_pieces(tmp_path: Path) -> None:
    build = PlayerBuild(
        Armor=_armor("Light", "Light", "Light", "Light", "Light", "Light", "Medium")
    )
    progression = CharacterProgression(owned_skill_lines=("Light Armor",))

    result = _resolver(tmp_path).resolve(build, progression=progression)

    assert result.modifiers.modifiers[0].value == 0.12


def test_breton_and_evocation_accumulate_as_percentage_reductions(tmp_path: Path) -> None:
    build = PlayerBuild(
        Race="Breton",
        Armor=_armor("Light", "Light", "Light", "Light", "Light", "Light", "Medium"),
    )
    progression = CharacterProgression(owned_skill_lines=("Light Armor",))

    result = _resolver(tmp_path).resolve(build, progression=progression)

    assert [modifier.value for modifier in result.modifiers.modifiers] == [0.07, 0.12]


def test_build_final_cost_uses_racial_and_owned_armor_passives(tmp_path: Path) -> None:
    build = PlayerBuild(
        Race="Breton",
        Armor=_armor("Light", "Light", "Light", "Light", "Light", "Light", "Medium"),
    )
    progression = CharacterProgression(owned_skill_lines=("Light Armor",))
    base_cost = resolve_base_action_cost(
        ability_id=41189,
        base_cost=4590,
        base_mechanic=1,
        rank=4,
        morph=2,
    )

    result = BuildFinalActionCostResolver(_resolver(tmp_path)).resolve(
        build,
        base_cost,
        skill_line="Restoration Staff",
        progression=progression,
    )

    assert result.unresolved == ()
    assert result.final_cost is not None
    magicka = result.final_cost.for_resource(ResourceType.MAGICKA)
    assert magicka.percent_reduction == 0.19
    assert magicka.final_amount == 3718
