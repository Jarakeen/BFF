from __future__ import annotations

import json
import sqlite3

from minmax.provisioning_static_repository import ProvisioningStaticRepository


def _write_db(path) -> None:
    payload = json.dumps(
        {
            "abilityDesc": "Increase Max Magicka by 5000 and Magicka Recovery by 500"
        }
    )
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE entity (
                id INTEGER PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL
            );
            CREATE TABLE entity_source (
                id INTEGER PRIMARY KEY,
                entity_id INTEGER NOT NULL,
                raw_json TEXT
            );
            """
        )
        db.execute(
            "INSERT INTO entity(id, entity_type, name) VALUES (1, 'drink', 'Test Tonic')"
        )
        db.execute(
            "INSERT INTO entity_source(id, entity_id, raw_json) VALUES (1, 1, ?)",
            (payload,),
        )


def test_provisioning_cache_holds_instance_snapshot_and_returns_fresh_containers(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    repo = ProvisioningStaticRepository(path)

    assert repo.list_names() == ("Test Tonic",)
    effects, unresolved = repo.resolve("Test Tonic")
    assert unresolved == []
    assert len(effects) == 2

    effects.clear()
    unresolved.append("caller mutation")

    replacement = json.dumps({"abilityDesc": "Increase Max Magicka by 7000"})
    with sqlite3.connect(path) as db:
        db.execute("UPDATE entity SET name='Changed Tonic' WHERE id=1")
        db.execute("UPDATE entity_source SET raw_json=? WHERE id=1", (replacement,))

    assert repo.list_names() == ("Test Tonic",)
    cached_effects, cached_unresolved = repo.resolve("Test Tonic")
    assert cached_unresolved == []
    assert len(cached_effects) == 2

    fresh = ProvisioningStaticRepository(path)
    assert fresh.list_names() == ("Changed Tonic",)
    fresh_effects, fresh_unresolved = fresh.resolve("Changed Tonic")
    assert fresh_unresolved == []
    assert len(fresh_effects) == 1
