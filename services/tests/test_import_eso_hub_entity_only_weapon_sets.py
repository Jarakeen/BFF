from __future__ import annotations

import json
import sqlite3

from importers.import_eso_hub_entity_only_weapon_sets import (
    apply_plan,
    build_plan,
)


def _database(path):
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE entity (
                id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                name TEXT NOT NULL
            );
            CREATE TABLE gear_set (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT,
                max_equip_count INTEGER
            );
            CREATE TABLE gear_set_bonus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                piece_count INTEGER NOT NULL,
                description TEXT,
                UNIQUE(set_id, piece_count)
            );
            CREATE TABLE gear_set_piece (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                set_id INTEGER NOT NULL,
                equip_type INTEGER,
                armor_type INTEGER,
                weapon_type INTEGER,
                UNIQUE(set_id, equip_type, armor_type, weapon_type)
            );
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                skill_line TEXT
            );

            INSERT INTO entity VALUES (
                'gear_set:grand_rejuvenation', 'gear_set', 'Grand Rejuvenation'
            );
            INSERT INTO skill VALUES (1, 'Grand Healing', 'Restoration Staff');
            INSERT INTO skill VALUES (2, 'Healing Springs', 'Restoration Staff');
            INSERT INTO skill VALUES (3, 'Illustrious Healing', 'Restoration Staff');
            """
        )


def test_build_plan_and_apply_additive_restoration_staff_set(tmp_path):
    db_path = tmp_path / "eso.db"
    source = tmp_path / "sets.json"
    _database(db_path)
    source.write_text(
        json.dumps(
            [
                {
                    "name": "Grand Rejuvenation",
                    "type": "Arena",
                    "location": "Dragonstar Arena",
                    "bonuses": ["(2 items) Restore resources after Grand Healing."],
                    "modified_skills": [
                        "Grand Healing",
                        "Healing Springs",
                        "Illustrious Healing",
                    ],
                    "unresolved": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    plan = build_plan(db_path, source)

    assert plan.proven is True
    assert len(plan.rows) == 1
    assert plan.rows[0].skill_line == "Restoration Staff"
    assert plan.rows[0].weapon_rows == ((11, 9),)

    inserted = apply_plan(db_path, plan)
    assert inserted == (1, 1, 1)

    with sqlite3.connect(db_path) as db:
        assert db.execute(
            "SELECT name, category, max_equip_count FROM gear_set"
        ).fetchall() == [("Grand Rejuvenation", "Arena", 2)]
        assert db.execute(
            "SELECT piece_count, description FROM gear_set_bonus"
        ).fetchall() == [
            (2, "(2 items) Restore resources after Grand Healing.")
        ]
        assert db.execute(
            "SELECT equip_type, armor_type, weapon_type FROM gear_set_piece"
        ).fetchall() == [(11, 0, 9)]


def test_build_plan_fails_closed_when_set_already_exists(tmp_path):
    db_path = tmp_path / "eso.db"
    source = tmp_path / "sets.json"
    _database(db_path)
    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT INTO gear_set(id, name, category, max_equip_count) VALUES (99, 'Grand Rejuvenation', 'Arena', 2)"
        )

    source.write_text(
        json.dumps(
            [
                {
                    "name": "Grand Rejuvenation",
                    "type": "Arena",
                    "location": "Dragonstar Arena",
                    "bonuses": ["(2 items) Restore resources."],
                    "modified_skills": ["Grand Healing"],
                    "unresolved": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    plan = build_plan(db_path, source)

    assert plan.proven is False
    assert any("already exists" in issue for issue in plan.unresolved)


def test_build_plan_prefers_single_supported_weapon_line_over_same_name_class_collision(tmp_path):
    db_path = tmp_path / "eso.db"
    source = tmp_path / "sets.json"
    _database(db_path)

    with sqlite3.connect(db_path) as db:
        db.execute(
            "INSERT INTO entity VALUES ('gear_set:disciplined_slash', 'gear_set', 'Disciplined Slash')"
        )
        db.execute("INSERT INTO skill VALUES (10, 'Executioner', 'Assassination')")
        db.execute("INSERT INTO skill VALUES (11, 'Executioner', 'Two Handed')")
        db.execute("INSERT INTO skill VALUES (12, 'Reverse Slash', 'Two Handed')")
        db.execute("INSERT INTO skill VALUES (13, 'Reverse Slice', 'Two Handed')")

    source.write_text(
        json.dumps(
            [
                {
                    "name": "Disciplined Slash",
                    "type": "Trial",
                    "location": "Asylum Sanctorium",
                    "bonuses": ["(2 items) Reverse Slash generates Ultimate."],
                    "modified_skills": ["Reverse Slash", "Reverse Slice", "Executioner"],
                    "unresolved": [],
                }
            ]
        ),
        encoding="utf-8",
    )

    plan = build_plan(db_path, source)

    assert plan.proven is True
    assert len(plan.rows) == 1
    assert plan.rows[0].skill_line == "Two Handed"
