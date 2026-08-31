from __future__ import annotations

import sqlite3

from importers.abilities_importer import AbilitiesImporter


def _record(*, ability_id: int, base_is_cost_time: str, charge_freq: str) -> dict[str, object]:
    return {
        "id": str(ability_id),
        "name": "Test Ability",
        "baseCost": "720",
        "baseMechanic": "36",
        "baseIsCostTime": base_is_cost_time,
        "chargeFreq": charge_freq,
    }


def test_fresh_ability_table_includes_phase4_timing_columns() -> None:
    connection = sqlite3.connect(":memory:")
    importer = AbilitiesImporter()

    importer._create_table(connection)
    importer._ensure_phase4_cost_timing_columns(connection)
    importer._verify_schema(connection)

    columns = {row[1] for row in connection.execute("PRAGMA table_info(ability)")}
    assert "base_is_cost_time" in columns
    assert "charge_freq_raw" in columns


def test_legacy_ability_table_is_migrated_non_destructively() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE ability (ability_id INTEGER PRIMARY KEY, raw_json TEXT)"
    )
    connection.execute(
        "INSERT INTO ability (ability_id, raw_json) VALUES (123, '{}')"
    )

    AbilitiesImporter._ensure_phase4_cost_timing_columns(connection)

    columns = {row[1] for row in connection.execute("PRAGMA table_info(ability)")}
    assert "base_is_cost_time" in columns
    assert "charge_freq_raw" in columns
    assert connection.execute("SELECT ability_id FROM ability").fetchone()[0] == 123


def test_insert_preserves_compound_charge_frequency_text() -> None:
    connection = sqlite3.connect(":memory:")
    importer = AbilitiesImporter()
    importer._create_table(connection)
    importer._ensure_phase4_cost_timing_columns(connection)
    importer._verify_schema(connection)

    importer._insert_ability(
        connection,
        _record(
            ability_id=230289,
            base_is_cost_time="true",
            charge_freq="2000,2000",
        ),
    )

    row = connection.execute(
        """
        SELECT base_is_cost_time, charge_freq_raw, charge_freq
        FROM ability
        WHERE ability_id = 230289
        """
    ).fetchone()

    assert row[0] == 1
    assert row[1] == "2000,2000"
    assert row[2] is None


def test_insert_preserves_numeric_charge_frequency_in_both_forms() -> None:
    connection = sqlite3.connect(":memory:")
    importer = AbilitiesImporter()
    importer._create_table(connection)
    importer._ensure_phase4_cost_timing_columns(connection)
    importer._verify_schema(connection)

    importer._insert_ability(
        connection,
        _record(
            ability_id=132141,
            base_is_cost_time="true",
            charge_freq="2000",
        ),
    )

    row = connection.execute(
        """
        SELECT base_is_cost_time, charge_freq_raw, charge_freq
        FROM ability
        WHERE ability_id = 132141
        """
    ).fetchone()

    assert row == (1, "2000", 2000.0)
