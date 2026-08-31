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


def _combat_prayer_cost(
    tmp_path: Path,
    *,
    light_count: int,
) -> int:
    weights = ["Light"] * light_count + ["Medium"] * (7 - light_count)
    build = PlayerBuild(Race="Breton", Armor=_armor(*weights))
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
    return result.final_cost.for_resource(ResourceType.MAGICKA).final_amount


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
    build = PlayerBuild(Armor=_armor("Light", "Light", "Medium", "Medium", "Medium", "Medium", "Medium"))

    without_owned = _resolver(tmp_path).resolve(build)
    assert without_owned.modifiers.modifiers == ()

    progression = CharacterProgression(owned_skill_lines=("Light Armor",))
    with_owned = _resolver(tmp_path).resolve(build, progression=progression)

    assert with_owned.unresolved == ()
    assert len(with_owned.modifiers.modifiers) == 1
    modifier = with_owned.modifiers.modifiers[0]
    assert modifier.source == "Light Armor: Evocation (2 pieces; live verified)"
    assert modifier.value == 0.03
    assert modifier.resources == (ResourceType.MAGICKA,)


def test_evocation_live_one_piece_matches_combat_prayer_4223(tmp_path: Path) -> None:
    assert _combat_prayer_cost(tmp_path, light_count=1) == 4223


def test_evocation_live_two_pieces_matches_combat_prayer_4131(tmp_path: Path) -> None:
    assert _combat_prayer_cost(tmp_path, light_count=2) == 4131


def test_evocation_live_six_pieces_matches_combat_prayer_3764(tmp_path: Path) -> None:
    assert _combat_prayer_cost(tmp_path, light_count=6) == 3764


def test_unverified_evocation_piece_count_stays_explicitly_unresolved(tmp_path: Path) -> None:
    build = PlayerBuild(
        Race="Breton",
        Armor=_armor("Light", "Light", "Light", "Medium", "Medium", "Medium", "Medium"),
    )
    progression = CharacterProgression(owned_skill_lines=("Light Armor",))

    result = _resolver(tmp_path).resolve(build, progression=progression)

    assert len(result.unresolved) == 1
    assert "not live-verified for 3 equipped Light pieces" in result.unresolved[0]
    assert [modifier.value for modifier in result.modifiers.modifiers] == [0.07]


def test_build_final_cost_withholds_result_for_unverified_evocation_count(tmp_path: Path) -> None:
    build = PlayerBuild(
        Race="Breton",
        Armor=_armor("Light", "Light", "Light", "Medium", "Medium", "Medium", "Medium"),
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

    assert result.final_cost is None
    assert len(result.unresolved) == 1
