from __future__ import annotations

import json
import sqlite3

from importers.repair_eso_hub_entity_only_weapon_set_piece_ids import (
    apply_plan,
    build_plan,
)


def _database(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE gear_set(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_piece(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER,
                UNIQUE(set_id, equip_type, armor_type, weapon_type)
            );
            CREATE TABLE skill(
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                skill_line TEXT
            );

            INSERT INTO gear_set VALUES(1, 'Grand Rejuvenation', 'Arena', 2);
            INSERT INTO gear_set_piece(set_id, equip_type, armor_type, weapon_type)
            VALUES(1, 11, 0, 9);
            INSERT INTO skill VALUES(1, 'Grand Healing', 'Restoration Staff');
            INSERT INTO skill VALUES(2, 'Healing Springs', 'Restoration Staff');
            INSERT INTO skill VALUES(3, 'Illustrious Healing', 'Restoration Staff');
            """
        )


def test_repair_adds_canonical_two_hand_row_without_deleting_legacy_row(tmp_path) -> None:
    database = tmp_path / "eso.db"
    source = tmp_path / "sets.json"
    _database(database)
    source.write_text(
        json.dumps(
            [
                {
                    "name": "Grand Rejuvenation",
                    "modified_skills": [
                        "Grand Healing",
                        "Healing Springs",
                        "Illustrious Healing",
                    ],
                }
            ]
        ),
        encoding="utf-8",
    )

    plan = build_plan(database, source)

    assert plan.proven is True
    assert len(plan.rows) == 1
    assert (plan.rows[0].equip_type, plan.rows[0].weapon_type) == (6, 9)

    assert apply_plan(database, plan) == 1

    with sqlite3.connect(database) as db:
        rows = db.execute(
            """
            SELECT equip_type, armor_type, weapon_type
            FROM gear_set_piece
            WHERE set_id = 1
            ORDER BY equip_type, weapon_type
            """
        ).fetchall()

    assert rows == [(6, 0, 9), (11, 0, 9)]


def test_repair_is_idempotent_after_canonical_row_exists(tmp_path) -> None:
    database = tmp_path / "eso.db"
    source = tmp_path / "sets.json"
    _database(database)
    source.write_text(
        json.dumps(
            [
                {
                    "name": "Grand Rejuvenation",
                    "modified_skills": ["Grand Healing"],
                }
            ]
        ),
        encoding="utf-8",
    )

    first = build_plan(database, source)
    assert apply_plan(database, first) == 1

    second = build_plan(database, source)
    assert second.proven is True
    assert second.rows == ()
    assert apply_plan(database, second) == 0
