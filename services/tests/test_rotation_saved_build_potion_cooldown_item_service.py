from __future__ import annotations

from pathlib import Path
import sqlite3

from minmax.jewelry_potion_cooldown_repository import JewelryPotionCooldownRepository
from minmax.jewelry_trait_repository import JewelryTraitRepository
from models.build_model import GearSlot, PlayerBuild
from services.rotation_saved_build_potion_cooldown_item_service import (
    RotationSavedBuildPotionCooldownItemService,
)


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
        connection.execute(
            "INSERT INTO jewelry_glyph(item_id, name) VALUES(1, 'Glyph of Potion Speed')"
        )
        connection.execute(
            """
            INSERT INTO jewelry_glyph_effect(
                glyph_item_id, effect_type, value_min, value_max, unit, description
            ) VALUES(1, 'potion_cooldown_reduction', 3, 5, 'seconds', '')
            """
        )
        connection.commit()
    return path


def _service(database: Path) -> RotationSavedBuildPotionCooldownItemService:
    return RotationSavedBuildPotionCooldownItemService(
        JewelryPotionCooldownRepository(database),
        JewelryTraitRepository(database),
    )


def _slot(*, trait: str = "", quality: str = "Gold", level: str = "CP160", tier: str = "Truly Superb") -> GearSlot:
    return GearSlot(
        Enchant="Glyph of Potion Speed",
        Trait=trait,
        Quality=quality,
        Level=level,
        EnchantTier=tier,
    )


def test_resolves_multiple_jewelry_item_reductions_and_infused_potency(tmp_path: Path) -> None:
    database = _database(tmp_path)
    build = PlayerBuild(
        Necklace=_slot(),
        Ring1=_slot(trait="Infused"),
        Ring2=GearSlot(Enchant="Glyph of Magicka Recovery"),
    )

    evidence = _service(database).resolve(build)

    assert evidence.unresolved == ()
    assert [item.seconds for item in evidence.reductions] == [5.0, 8.0]
    assert evidence.total_reduction_seconds == 13.0
    assert evidence.reductions[0].source == "Necklace: Glyph of Potion Speed"
    assert evidence.reductions[1].source == "Ring 1: Glyph of Potion Speed (Infused +60%)"


def test_potion_cooldown_item_evidence_fails_closed_on_unverified_level_or_tier(tmp_path: Path) -> None:
    database = _database(tmp_path)
    build = PlayerBuild(Necklace=_slot(level="CP150", tier="Superb"))

    evidence = _service(database).resolve(build)

    assert evidence.reductions == ()
    assert evidence.unresolved == (
        "Necklace Glyph of Potion Speed: needs verified level/tier scaling (CP150, Superb)",
    )


def test_potion_named_saved_enchant_without_exact_canonical_glyph_is_unresolved(tmp_path: Path) -> None:
    database = _database(tmp_path)
    build = PlayerBuild(
        Necklace=GearSlot(
            Enchant="Potion Cooldown",
            Quality="Gold",
            Level="CP160",
            EnchantTier="Truly Superb",
        )
    )

    evidence = _service(database).resolve(build)

    assert evidence.reductions == ()
    assert evidence.unresolved == (
        "Necklace: canonical potion cooldown glyph not found by exact saved name: Potion Cooldown",
    )


def test_infused_potion_cooldown_requires_verified_trait_quality(tmp_path: Path) -> None:
    database = _database(tmp_path)
    build = PlayerBuild(Necklace=_slot(trait="Infused", quality=""))

    evidence = _service(database).resolve(build)

    assert evidence.reductions == ()
    assert evidence.unresolved == (
        "Necklace: Infused jewelry value unavailable for quality unset",
    )
