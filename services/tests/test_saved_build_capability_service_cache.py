from __future__ import annotations

import sqlite3
from pathlib import Path
from types import SimpleNamespace

from services.saved_build_capability_service import SavedBuildCapabilityService


def _write_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE ability (
                ability_id INTEGER,
                name TEXT,
                class_type TEXT,
                rank INTEGER,
                morph INTEGER,
                is_crafted INTEGER
            );
            INSERT INTO ability(ability_id, name, class_type, rank, morph, is_crafted) VALUES
                (1001, 'Combat Prayer', 'Templar', 4, 2, 0),
                (1002, 'Combat Prayer', 'Warden', 4, 2, 0),
                (1003, 'Energy Orb', '', 4, 2, 0),
                (4001, 'Ulfsilds Contingency', '', 1, 0, 1);
            """
        )


def _service(path: Path) -> SavedBuildCapabilityService:
    builds = SimpleNamespace(canonical=SimpleNamespace(catalog_service=object()))
    placeholder = object()
    return SavedBuildCapabilityService(
        builds,
        path,
        context_factory=placeholder,
        progression=placeholder,
        skills=placeholder,
        gear=placeholder,
        potions=placeholder,
    )


def test_ability_id_cache_reuses_same_name_and_class(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = _service(path)

    assert service._ability_id(" Combat Prayer ", "Templar") == 1001

    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE ability SET ability_id=2001 WHERE name='Combat Prayer' AND class_type='Templar'"
        )

    assert service._ability_id("combat prayer", " templar ") == 1001
    assert service._ability_id("Combat Prayer", "Warden") == 1002


def test_unresolved_ability_id_is_cached_for_service_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = _service(path)

    assert service._ability_id("Missing Skill", "Templar") is None

    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO ability(ability_id, name, class_type, rank, morph, is_crafted) "
            "VALUES (3001, 'Missing Skill', 'Templar', 4, 2, 0)"
        )

    assert service._ability_id(" missing skill ", "templar") is None
    assert _service(path)._ability_id("Missing Skill", "Templar") == 3001


def test_crafted_ability_check_is_cached_for_service_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = _service(path)

    assert service._ability_is_crafted(4001) is True

    with sqlite3.connect(path) as db:
        db.execute("UPDATE ability SET is_crafted=0 WHERE ability_id=4001")

    assert service._ability_is_crafted(4001) is True
    assert _service(path)._ability_is_crafted(4001) is False


def test_noncrafted_ability_check_is_cached_for_service_lifetime(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _write_db(path)
    service = _service(path)

    assert service._ability_is_crafted(1001) is False

    with sqlite3.connect(path) as db:
        db.execute("UPDATE ability SET is_crafted=1 WHERE ability_id=1001")

    assert service._ability_is_crafted(1001) is False
    assert _service(path)._ability_is_crafted(1001) is True
