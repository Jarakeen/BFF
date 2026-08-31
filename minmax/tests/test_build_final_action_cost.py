from __future__ import annotations

import sqlite3
from pathlib import Path

from models.build_model import GearSlot, PlayerBuild

from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.build_final_action_cost import BuildFinalActionCostResolver
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.resource_costs import ResourceType, resolve_base_action_cost


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
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
        connection.executemany(
            "INSERT INTO jewelry_glyph(item_id, name) VALUES (?, ?)",
            [
                (1, "Glyph of Reduce Spell Cost"),
                (2, "Glyph of Reduce Skill Cost"),
            ],
        )
        connection.executemany(
            """
            INSERT INTO jewelry_glyph_effect(
                glyph_item_id, effect_type, value_min, value_max, unit, description
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (1, "magicka_cost_reduction", 203, 203, "flat", "magicka"),
                (2, "resource_cost_reduction", 133, 133, "flat", "resource"),
            ],
        )
    return path


def _resolver(tmp_path: Path) -> BuildFinalActionCostResolver:
    path = _database(tmp_path)
    modifier_resolver = BuildActionCostModifierResolver(
        JewelryCostModifierRepository(path),
        JewelryTraitRepository(path),
    )
    return BuildFinalActionCostResolver(modifier_resolver)


def test_saved_swift_spell_cost_glyph_flows_into_final_magicka_cost(tmp_path: Path) -> None:
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Reduce Spell Cost",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )
    base_cost = resolve_base_action_cost(
        ability_id=41189,
        base_cost=4590,
        base_mechanic=1,
        rank=4,
        morph=2,
    )

    result = _resolver(tmp_path).resolve(build, base_cost, skill_line="Restoration Staff")

    assert result.unresolved == ()
    assert result.final_cost is not None
    magicka = result.final_cost.for_resource(ResourceType.MAGICKA)
    assert magicka.base_amount == 4590
    assert magicka.flat_reduction == 203
    assert magicka.percent_reduction == 0
    assert magicka.final_amount == 4387
    assert magicka.applied_modifiers[0].source == "Necklace: Glyph of Reduce Spell Cost"


def test_saved_infused_spell_cost_glyph_uses_trait_scaling_in_final_cost(tmp_path: Path) -> None:
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Reduce Spell Cost",
            Trait="Infused",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )
    base_cost = resolve_base_action_cost(
        ability_id=41189,
        base_cost=4590,
        base_mechanic=1,
    )

    result = _resolver(tmp_path).resolve(build, base_cost)

    assert result.unresolved == ()
    assert result.final_cost is not None
    magicka = result.final_cost.for_resource(ResourceType.MAGICKA)
    assert magicka.flat_reduction == 324.8
    assert magicka.final_amount == 4265
    assert "Infused +60%" in magicka.applied_modifiers[0].source


def test_compound_cost_applies_saved_resource_glyph_to_each_consumed_pool(tmp_path: Path) -> None:
    build = PlayerBuild(
        Ring1=GearSlot(
            Enchant="Reduce Skill Cost",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )
    base_cost = resolve_base_action_cost(
        ability_id=23819,
        base_cost=1148,
        base_mechanic=5,
        rank=4,
        morph=1,
    )

    result = _resolver(tmp_path).resolve(build, base_cost)

    assert result.unresolved == ()
    assert result.final_cost is not None
    assert result.final_cost.for_resource(ResourceType.MAGICKA).final_amount == 1015
    assert result.final_cost.for_resource(ResourceType.STAMINA).final_amount == 1015


def test_unverified_selected_cost_glyph_blocks_partial_final_cost(tmp_path: Path) -> None:
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Reduce Spell Cost",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="",
            Level="CP160",
        )
    )
    base_cost = resolve_base_action_cost(
        ability_id=41189,
        base_cost=4590,
        base_mechanic=1,
    )

    result = _resolver(tmp_path).resolve(build, base_cost)

    assert result.final_cost is None
    assert len(result.unresolved) == 1
    assert "needs verified level/tier scaling" in result.unresolved[0]


def test_build_without_cost_glyph_resolves_unchanged_base_cost(tmp_path: Path) -> None:
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Magicka Recovery",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )
    base_cost = resolve_base_action_cost(
        ability_id=41189,
        base_cost=4590,
        base_mechanic=1,
    )

    result = _resolver(tmp_path).resolve(build, base_cost)

    assert result.unresolved == ()
    assert result.final_cost is not None
    assert result.final_cost.for_resource(ResourceType.MAGICKA).final_amount == 4590
    assert result.modifiers.modifiers == ()
