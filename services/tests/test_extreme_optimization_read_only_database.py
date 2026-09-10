from __future__ import annotations

import sqlite3

import pytest

from minmax.mundus_repository import MundusRepository
from services.extreme_optimization_service import ExtremeOptimizationService


def test_extreme_optimizer_construction_does_not_rewrite_canonical_database(tmp_path):
    database = tmp_path / "eso.db"
    MundusRepository(database)
    before = database.read_bytes()

    service = ExtremeOptimizationService(
        database_path=database,
        builds_path=tmp_path / "builds.json",
    )

    assert database.read_bytes() == before
    assert service.context_factory.static_build_resolver.mundus_repository is (
        service.mundus_repository
    )


def test_explicit_read_only_mundus_repository_does_not_create_a_database(tmp_path):
    database = tmp_path / "missing.db"

    MundusRepository(database, initialize=False)

    assert not database.exists()


def test_explicit_read_only_mundus_repository_can_read_seeded_records(tmp_path):
    database = tmp_path / "eso.db"
    MundusRepository(database)

    repository = MundusRepository(database, initialize=False)
    records = repository.get_records("The Shadow")

    assert {record.stat_id for record in records} == {
        "critical_damage",
        "critical_healing",
    }


def test_explicit_read_only_mundus_repository_rejects_database_writes(tmp_path):
    database = tmp_path / "eso.db"
    MundusRepository(database)
    repository = MundusRepository(database, initialize=False)

    with repository._connect() as connection:
        with pytest.raises(sqlite3.OperationalError, match="readonly|read-only"):
            connection.execute("CREATE TABLE forbidden_extreme_write(id INTEGER)")
