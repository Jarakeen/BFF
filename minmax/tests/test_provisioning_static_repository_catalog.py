import json
import sqlite3

from minmax.provisioning_static_repository import ProvisioningStaticRepository


def test_list_names_merges_entity_and_legacy_catalogs_deterministically(tmp_path) -> None:
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE entity (
            id TEXT PRIMARY KEY,
            entity_type TEXT NOT NULL,
            name TEXT NOT NULL,
            slug TEXT NOT NULL
        );
        CREATE TABLE entity_source (
            id INTEGER PRIMARY KEY,
            entity_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_entity_type TEXT,
            source_id TEXT,
            source_name TEXT,
            raw_json TEXT
        );
        CREATE TABLE food (
            name TEXT NOT NULL,
            description TEXT
        );
        """
    )
    connection.execute(
        "INSERT INTO entity VALUES ('food:a', 'food', 'Bewitched Sugar Skulls', 'bewitched-sugar-skulls')"
    )
    connection.execute(
        "INSERT INTO entity VALUES ('drink:b', 'drink', 'Clockwork Citrus Filet', 'clockwork-citrus-filet')"
    )
    connection.execute(
        "INSERT INTO entity VALUES ('skill:c', 'skill', 'Not Provisioning', 'not-provisioning')"
    )
    connection.execute(
        "INSERT INTO food VALUES (?, ?)",
        ("clockwork citrus filet", json.dumps({"description": "duplicate spelling"})),
    )
    connection.execute(
        "INSERT INTO food VALUES (?, ?)",
        ("Ghastly Eye Bowl", "Increase Max Magicka by 4592"),
    )
    connection.commit()
    connection.close()

    names = ProvisioningStaticRepository(path).list_names()

    assert names == (
        "Bewitched Sugar Skulls",
        "Clockwork Citrus Filet",
        "Ghastly Eye Bowl",
    )
