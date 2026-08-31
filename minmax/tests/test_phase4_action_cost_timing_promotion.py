from __future__ import annotations

import json
import sqlite3

from tools.promote_phase4_action_cost_timing import apply_promotion, build_promotion_plan


def _database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        """
        CREATE TABLE ability (
            ability_id INTEGER PRIMARY KEY,
            name TEXT,
            base_cost REAL,
            raw_json TEXT
        )
        """
    )
    return connection


def test_build_promotion_plan_preserves_compound_charge_frequency_text() -> None:
    connection = _database()
    connection.execute(
        "INSERT INTO ability VALUES (?, ?, ?, ?)",
        (
            230289,
            "Banner Bearer",
            720.0,
            json.dumps(
                {
                    "baseIsCostTime": "true",
                    "chargeFreq": "2000,2000",
                }
            ),
        ),
    )

    plan = build_promotion_plan(connection)

    assert plan["unresolved_rows"] == 0
    assert plan["recurring_rows"] == 1
    assert plan["values"] == [(1, "2000,2000", 230289)]
    assert plan["needs_base_is_cost_time_column"] is True
    assert plan["needs_charge_freq_raw_column"] is True


def test_apply_promotion_adds_columns_and_populates_values() -> None:
    connection = _database()
    connection.executemany(
        "INSERT INTO ability VALUES (?, ?, ?, ?)",
        [
            (
                103503,
                "Accelerate",
                4050.0,
                json.dumps(
                    {
                        "baseIsCostTime": "false",
                        "chargeFreq": "0",
                    }
                ),
            ),
            (
                132141,
                "Blood Frenzy",
                700.0,
                json.dumps(
                    {
                        "baseIsCostTime": "true",
                        "chargeFreq": "2000",
                    }
                ),
            ),
        ],
    )

    plan = build_promotion_plan(connection)
    apply_promotion(connection, plan)

    columns = {row[1] for row in connection.execute("PRAGMA table_info(ability)")}
    assert "base_is_cost_time" in columns
    assert "charge_freq_raw" in columns

    rows = connection.execute(
        """
        SELECT ability_id, base_is_cost_time, charge_freq_raw
        FROM ability
        ORDER BY ability_id
        """
    ).fetchall()
    assert [tuple(row) for row in rows] == [
        (103503, 0, "0"),
        (132141, 1, "2000"),
    ]


def test_apply_promotion_refuses_unresolved_rows() -> None:
    connection = _database()
    connection.execute(
        "INSERT INTO ability VALUES (?, ?, ?, ?)",
        (
            999,
            "Broken Recurring Cost",
            100.0,
            json.dumps(
                {
                    "baseIsCostTime": "true",
                    "chargeFreq": "2000,3000",
                }
            ),
        ),
    )

    plan = build_promotion_plan(connection)

    assert plan["unresolved_rows"] == 1

    try:
        apply_promotion(connection, plan)
    except RuntimeError as exc:
        assert "unresolved rows" in str(exc)
    else:
        raise AssertionError("promotion should refuse unresolved timing rows")
