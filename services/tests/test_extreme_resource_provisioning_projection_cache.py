from __future__ import annotations

import sqlite3

from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.provisioning_static_repository import ProvisioningStaticRepository
from minmax.stat_ids import StatId
import services.extreme_resource_provisioning_projection_service as projection_module
from services.extreme_resource_provisioning_projection_service import (
    ExtremeResourceProvisioningProjectionService,
)


class _CanonicalRepository(ProvisioningStaticRepository):
    def __init__(self, database_path, rows, effects):
        self.database_path = str(database_path)
        self._rows = tuple(rows)
        self._effects = dict(effects)
        self.resolve_calls = 0

    def list_names(self):
        return self._rows

    def resolve(self, name):
        self.resolve_calls += 1
        return list(self._effects.get(name, ())), []

    def description(self, name):
        return ""


def _effect(name: str, value: float) -> Effect:
    return Effect(
        source=f"Food/Drink: {name}",
        stat=StatId.MAX_MAGICKA,
        operation=EffectOperation.ADD,
        value=value,
        unit=EffectUnit.FLAT,
    )


def _database(tmp_path):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as connection:
        connection.execute(
            "CREATE TABLE entity (id TEXT PRIMARY KEY, entity_type TEXT NOT NULL, name TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO entity(id, entity_type, name) VALUES (?, ?, ?)",
            (
                ("1", "food", "Meal"),
                ("2", "drink", "Drink"),
            ),
        )
    return path


def test_kind_catalog_is_bulk_loaded_once_per_projection_build(tmp_path, monkeypatch) -> None:
    path = _database(tmp_path)
    repository = _CanonicalRepository(
        path,
        ("Meal", "Drink"),
        {
            "Meal": (_effect("Meal", 5000.0),),
            "Drink": (_effect("Drink", 4000.0),),
        },
    )
    ExtremeResourceProvisioningProjectionService._production_projection_cache.clear()

    real_connect = sqlite3.connect
    connect_calls = 0

    def counted_connect(*args, **kwargs):
        nonlocal connect_calls
        connect_calls += 1
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(projection_module.sqlite3, "connect", counted_connect)

    result = ExtremeResourceProvisioningProjectionService(repository).build("max_magicka")

    assert result.projection_complete is True
    assert result.choices == ("Meal", "Drink")
    assert connect_calls == 1


def test_production_projection_is_shared_by_database_and_objective(tmp_path) -> None:
    path = _database(tmp_path)
    effects = {
        "Meal": (_effect("Meal", 5000.0),),
        "Drink": (_effect("Drink", 4000.0),),
    }
    first_repository = _CanonicalRepository(path, ("Meal", "Drink"), effects)
    second_repository = _CanonicalRepository(path, ("Meal", "Drink"), effects)
    ExtremeResourceProvisioningProjectionService._production_projection_cache.clear()

    first = ExtremeResourceProvisioningProjectionService(first_repository).build("max_magicka")
    second = ExtremeResourceProvisioningProjectionService(second_repository).build("max_magicka")

    assert first is second
    assert first_repository.resolve_calls == 2
    assert second_repository.resolve_calls == 0
