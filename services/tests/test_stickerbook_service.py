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
