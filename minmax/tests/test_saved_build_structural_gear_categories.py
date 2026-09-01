import sqlite3
from pathlib import Path

from minmax.character_build.gear_piece import GearPieceCategory, GearSlot
from minmax.character_build.saved_build_adapter import SavedBuildCharacterAdapter
from models.build_model import PlayerBuild


def _make_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE race (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                alliance TEXT,
                association TEXT
            );
            INSERT INTO race VALUES (4, 'Breton', 'Daggerfall Covenant', 'Human');

            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            INSERT INTO gear_set VALUES
                (609, 'Magma Incarnate', 'standard', 2),
                (627, 'Spaulder of Ruin', 'standard', 1),
                (641, 'Serpent''s Disdain', 'standard', 5);

            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                item_id INTEGER,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            );
            INSERT INTO gear_set_piece(set_id, item_id, equip_type, armor_type, weapon_type) VALUES
                (609, 1001, 1, 1, 0),
                (609, 1002, 4, 1, 0),
                (627, 2001, 4, 1, 0),
                (641, 3001, 1, 1, 0),
                (641, 3002, 3, 1, 0),
                (641, 3003, 4, 1, 0);

            CREATE TABLE gear_set_item (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL
            );
            INSERT INTO gear_set_item(set_id, item_id) VALUES
                (609, 1001),
                (609, 1002),
                (627, 2001),
                (641, 3001),
                (641, 3002),
                (641, 3003);
            """
        )


def test_saved_build_adapter_places_structural_mythic_in_dedicated_slot(tmp_path: Path):
    db_path = tmp_path / "eso.db"
    _make_db(db_path)

    saved = PlayerBuild(
        Name="Magrat",
        BuildName="DF Healer",
        Race="Breton",
        EsoClass="Warden",
        Role="Healer",
    )
    saved.Armor["Head"]["Set"] = "Magma Incarnate"
    saved.Armor["Shoulders"]["Set"] = "Spaulder of Ruin"
    saved.Armor["Chest"]["Set"] = "Serpent's Disdain"

    result = SavedBuildCharacterAdapter(db_path).adapt(saved)

    assert result.build is not None
    assert result.unresolved == ()
    assert result.build.mythic is not None
    assert result.build.mythic.slot == GearSlot.SHOULDERS
    assert result.build.mythic.set_id == "627"
    assert result.build.mythic.category == GearPieceCategory.MYTHIC

    by_slot = {piece.slot: piece for piece in result.build.armor}
    assert by_slot[GearSlot.HEAD].set_id == "609"
    assert by_slot[GearSlot.HEAD].category == GearPieceCategory.MONSTER_SET
    assert by_slot[GearSlot.CHEST].set_id == "641"
    assert by_slot[GearSlot.CHEST].category == GearPieceCategory.SET_PIECE
