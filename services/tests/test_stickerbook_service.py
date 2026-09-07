import sqlite3

from services.stickerbook_service import StickerbookService


def _database(path):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT
            );
            CREATE TABLE content (
                id INTEGER PRIMARY KEY,
                content_type TEXT,
                name TEXT,
                location TEXT
            );
            CREATE TABLE content_sets (
                content_id INTEGER NOT NULL,
                set_id INTEGER NOT NULL
            );

            INSERT INTO gear_set(id, name, category, max_equip_count)
            VALUES (100, 'Test Arena Set', 'Arena', 2);
            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type)
            VALUES
                (100, 1, 1, 0),
                (100, 6, 0, 12);
            INSERT INTO gear_set_bonus(set_id, piece_count, description)
            VALUES (100, 2, 'Adds testing confidence');
            INSERT INTO content(id, content_type, name, location)
            VALUES (1, 'arena', 'Test Arena', 'Somewhere unpleasant');
            INSERT INTO content_sets(content_id, set_id) VALUES (1, 100);
            """
        )


def test_stickerbook_tracks_profile_piece_ownership(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    service = StickerbookService(path)

    rows = service.sets("Jarakeen")
    assert len(rows) == 1
    assert rows[0]["bucket"] == "Arena"
    assert rows[0]["collected"] == 0
    assert rows[0]["total"] == 2

    pieces = service.pieces(100, "Jarakeen")
    assert [piece.group for piece in pieces] == ["Armor", "Weapons"]
    assert pieces[1].label == "Inferno Staff"

    service.set_collected("Jarakeen", 100, pieces[1].piece_key, True)

    rows = service.sets("Jarakeen")
    assert rows[0]["collected"] == 1
    assert service.summary("Jarakeen") == (1, 2)
    assert service.summary("Other Profile") == (0, 2)


def test_stickerbook_exports_progress(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    service = StickerbookService(path)
    piece = service.pieces(100, "Jarakeen")[0]
    service.set_collected("Jarakeen", 100, piece.piece_key, True)

    target = service.export_csv(tmp_path / "stickerbook.csv", "Jarakeen")
    text = target.read_text(encoding="utf-8-sig")

    assert "Test Arena Set" in text
    assert "Jarakeen" in text
    assert ",1,2,50.0" in text


def test_standard_dropped_set_exposes_full_22_piece_sticker_shape(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (200, 'Full Trial Set', 'Trial', 5)"
        )
        armor_rows = [
            (200, equip_type, 2, 0)
            for equip_type in (1, 3, 4, 8, 9, 10, 13)
        ]
        weapon_rows = [
            (200, 5 if weapon_type in {1, 2, 3, 11, 14} else 6, 0, weapon_type)
            for weapon_type in (1, 2, 3, 4, 5, 6, 8, 9, 11, 12, 13, 14, 15)
        ]
        jewelry_rows = [(200, 2, 0, 0), (200, 12, 0, 0)]
        connection.executemany(
            "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (?, ?, ?, ?)",
            armor_rows + weapon_rows + jewelry_rows,
        )
        connection.execute(
            "INSERT INTO content(id, content_type, name, location) VALUES (2, 'trial', 'Test Trial', '')"
        )
        connection.execute(
            "INSERT INTO content_sets(content_id, set_id) VALUES (2, 200)"
        )
        connection.commit()

    service = StickerbookService(path)
    pieces = service.pieces(200, "Jarakeen")

    assert len(pieces) == 22
    assert sum(piece.group == "Armor" for piece in pieces) == 7
    assert sum(piece.group == "Weapons" for piece in pieces) == 13
    assert sum(piece.group == "Jewelry" for piece in pieces) == 2
    assert {piece.label for piece in pieces if piece.group == "Weapons"} == {
        "Axe",
        "Mace",
        "Sword",
        "Two-Handed Sword",
        "Two-Handed Axe",
        "Two-Handed Mace",
        "Bow",
        "Restoration Staff",
        "Dagger",
        "Inferno Staff",
        "Ice Staff",
        "Shield",
        "Lightning Staff",
    }


def test_standard_dropped_set_recovers_missing_weapon_stickers(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (250, 'Armor Only Import', 'Trial', 5)"
        )
        armor_rows = [
            (250, equip_type, 2, 0)
            for equip_type in (1, 3, 4, 8, 9, 10, 13)
        ]
        jewelry_rows = [(250, 2, 0, 0), (250, 12, 0, 0)]
        connection.executemany(
            "INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES (?, ?, ?, ?)",
            armor_rows + jewelry_rows,
        )
        connection.execute(
            "INSERT INTO content(id, content_type, name, location) VALUES (7, 'trial', 'Recovered Trial', '')"
        )
        connection.execute(
            "INSERT INTO content_sets(content_id, set_id) VALUES (7, 250)"
        )
        connection.commit()

    service = StickerbookService(path)
    pieces = service.pieces(250, "Jarakeen")
    weapons = [piece for piece in pieces if piece.group == "Weapons"]

    assert len(pieces) == 22
    assert len(weapons) == 13
    assert {piece.label for piece in weapons} == set(
        (
            "Axe", "Mace", "Sword", "Two-Handed Sword", "Two-Handed Axe",
            "Two-Handed Mace", "Bow", "Restoration Staff", "Dagger",
            "Inferno Staff", "Ice Staff", "Shield", "Lightning Staff",
        )
    )
    row = next(row for row in service.sets("Jarakeen") if row["id"] == 250)
    assert row["total"] == 22

    inferno = next(piece for piece in weapons if piece.label == "Inferno Staff")
    service.set_collected("Jarakeen", 250, inferno.piece_key, True)
    row = next(row for row in service.sets("Jarakeen") if row["id"] == 250)
    assert row["collected"] == 1


def test_stickerbook_strips_eso_color_markup_from_display_text(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            INSERT INTO gear_set(id, name, category, max_equip_count)
            VALUES (260, '|cffffff9|Color Set|r', '|cFFFFFFTrial|r', 2);
            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type)
            VALUES (260, 1, 2, 0);
            INSERT INTO gear_set_bonus(set_id, piece_count, description)
            VALUES (260, 2, '|cFFAA00Adds clean text|r');
            INSERT INTO content(id, content_type, name, location)
            VALUES (8, 'trial', '|c00FF00Color Trial|r', '');
            INSERT INTO content_sets(content_id, set_id) VALUES (8, 260);
            """
        )
        connection.commit()

    service = StickerbookService(path)
    row = next(row for row in service.sets("Jarakeen") if row["id"] == 260)

    assert row["name"] == "Color Set"
    assert row["category"] == "Trial"
    assert row["source"] == "Color Trial"
    assert service.bonuses(260) == [(2, "Adds clean text")]
    assert "|c" not in " ".join((row["name"], row["category"], row["source"]))


def test_stickerbook_classifies_monster_mythic_and_class_sets_and_excludes_crafted(tmp_path):
    path = tmp_path / "eso.db"
    _database(path)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            INSERT INTO gear_set(id, name, category, max_equip_count) VALUES
                (300, 'Test Monster Set', 'Monster Set', 2),
                (301, 'Test Mythic', 'Mythic', 1),
                (302, 'Test Class Set', 'Class', 5),
                (303, 'Test Crafted Set', 'Crafted', 5);

            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type) VALUES
                (300, 1, 1, 0),
                (300, 1, 2, 0),
                (300, 1, 3, 0),
                (300, 4, 1, 0),
                (300, 4, 2, 0),
                (300, 4, 3, 0),
                (301, 2, 0, 0),
                (302, 3, 2, 0),
                (303, 3, 2, 0);

            INSERT INTO content(id, content_type, name, location) VALUES
                (3, 'dungeon', 'Test Dungeon', ''),
                (4, 'mythic', 'Antiquities', ''),
                (5, 'class', 'Infinite Archive', ''),
                (6, 'crafted', 'Test Crafting Station', '');

            INSERT INTO content_sets(content_id, set_id) VALUES
                (3, 300),
                (4, 301),
                (5, 302),
                (6, 303);
            """
        )
        connection.commit()

    service = StickerbookService(path)
    rows = {row["name"]: row for row in service.sets("Jarakeen")}

    assert rows["Test Monster Set"]["bucket"] == "Monster"
    assert rows["Test Monster Set"]["total"] == 6
    assert rows["Test Mythic"]["bucket"] == "Mythic"
    assert rows["Test Class Set"]["bucket"] == "Class"
    assert "Test Crafted Set" not in rows


def test_unexpected_structural_piece_is_not_mislabeled_as_armor():
    label, group = StickerbookService.piece_label(99, 0, 0)

    assert label == "Equipment Slot 99"
    assert group == "Other"
