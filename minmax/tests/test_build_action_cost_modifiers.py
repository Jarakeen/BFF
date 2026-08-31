from __future__ import annotations

import sqlite3
from pathlib import Path

from models.build_model import GearSlot, PlayerBuild

from minmax.build_action_cost_modifiers import BuildActionCostModifierResolver
from minmax.jewelry_cost_modifier_repository import JewelryCostModifierRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from minmax.resource_cost_modifiers import CostModifierOperation
from minmax.resource_costs import ResourceType


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
                (2, "Glyph of Reduce Feat Cost"),
                (3, "Glyph of Reduce Skill Cost"),
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
                (2, "stamina_cost_reduction", 203, 203, "flat", "stamina"),
                (3, "resource_cost_reduction", 133, 133, "flat", "resource"),
            ],
        )
    return path


def _resolver(tmp_path: Path) -> BuildActionCostModifierResolver:
    path = _database(tmp_path)
    return BuildActionCostModifierResolver(
        JewelryCostModifierRepository(path),
        JewelryTraitRepository(path),
    )


def test_swift_reduce_spell_cost_resolves_flat_magicka_modifier(tmp_path: Path) -> None:
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Reduce Spell Cost",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )

    result = _resolver(tmp_path).resolve(build)

    assert result.unresolved == ()
    assert len(result.modifiers.modifiers) == 1
    modifier = result.modifiers.modifiers[0]
    assert modifier.operation is CostModifierOperation.FLAT_REDUCTION
    assert modifier.value == 203
    assert modifier.resources == (ResourceType.MAGICKA,)
    assert modifier.source == "Necklace: Glyph of Reduce Spell Cost"


def test_infused_gold_scales_enchantment_by_verified_sixty_percent(tmp_path: Path) -> None:
    build = PlayerBuild(
        Ring1=GearSlot(
            Enchant="Reduce Spell Cost",
            Trait="Infused",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )

    result = _resolver(tmp_path).resolve(build)

    assert result.unresolved == ()
    modifier = result.modifiers.modifiers[0]
    assert modifier.value == 324.8
    assert "Infused +60%" in modifier.source


def test_multiple_cost_glyph_slots_accumulate_separate_modifiers(tmp_path: Path) -> None:
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Reduce Spell Cost",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        ),
        Ring1=GearSlot(
            Enchant="Reduce Stamina Cost",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        ),
        Ring2=GearSlot(
            Enchant="Reduce Skill Cost",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        ),
    )

    result = _resolver(tmp_path).resolve(build)

    assert result.unresolved == ()
    assert len(result.modifiers.modifiers) == 3
    assert result.modifiers.modifiers[0].resources == (ResourceType.MAGICKA,)
    assert result.modifiers.modifiers[1].resources == (ResourceType.STAMINA,)
    assert result.modifiers.modifiers[2].resources == (
        ResourceType.HEALTH,
        ResourceType.MAGICKA,
        ResourceType.STAMINA,
    )


def test_cost_glyph_without_verified_max_level_tier_stays_unresolved(tmp_path: Path) -> None:
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Reduce Spell Cost",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="",
            Level="CP160",
        )
    )

    result = _resolver(tmp_path).resolve(build)

    assert result.modifiers.modifiers == ()
    assert len(result.unresolved) == 1
    assert "needs verified level/tier scaling" in result.unresolved[0]


def test_non_cost_jewelry_enchant_is_not_claimed_by_cost_resolver(tmp_path: Path) -> None:
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Magicka Recovery",
            Trait="Swift",
            Quality="Gold",
            EnchantTier="Truly Superb",
            Level="CP160",
        )
    )

    result = _resolver(tmp_path).resolve(build)

    assert result.modifiers.modifiers == ()
    assert result.unresolved == ()
