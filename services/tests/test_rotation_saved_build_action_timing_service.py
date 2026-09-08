from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from minmax.rotation_plan import RotationActionKind
from services.rotation_saved_build_action_timing_service import (
    RotationSavedBuildActionTimingService,
)


def _create_timing_database(path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                rank INTEGER,
                raw_name TEXT,
                cooldown REAL,
                cast_time REAL,
                channel_time REAL
            );
            """
        )
        db.execute("INSERT INTO skill(id, name) VALUES(1, 'Channeled Skill')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(101, 'Channeled Skill')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name,
                cooldown, cast_time, channel_time
            ) VALUES(1, 1, 101, 4, 'Channeled Skill', 5000, 1500, 0)
            """
        )
        db.execute("INSERT INTO skill(id, name) VALUES(2, 'Big Ultimate')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(202, 'Big Ultimate')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name,
                cooldown, cast_time, channel_time
            ) VALUES(2, 2, 202, 4, 'Big Ultimate', 12000, 0, 2500)
            """
        )
        db.execute("INSERT INTO skill(id, name) VALUES(3, 'Instant Skill')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(303, 'Instant Skill')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name,
                cooldown, cast_time, channel_time
            ) VALUES(3, 3, 303, 4, 'Instant Skill', 0, 0, 0)
            """
        )
        db.commit()


def _build(front, back=()):
    return SimpleNamespace(
        FrontBarSkills=tuple(front),
        BackBarSkills=tuple(back),
    )


def test_saved_build_timing_converts_imported_milliseconds_and_preserves_action_kind(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_timing_database(database)
    build = _build(
        (
            "Channeled Skill",
            "Instant Skill",
            "Instant Skill",
            "Instant Skill",
            "Instant Skill",
            "Big Ultimate",
        )
    )

    evidence = RotationSavedBuildActionTimingService(database).resolve(build)

    assert evidence.unresolved == ()
    assert [
        (item.action_name, item.action_kind, item.cooldown_seconds)
        for item in evidence.cooldown_requirements
    ] == [
        ("Channeled Skill", RotationActionKind.SKILL, 5.0),
        ("Big Ultimate", RotationActionKind.ULTIMATE, 12.0),
    ]
    assert [
        (item.action_name, item.action_kind, item.occupancy_seconds)
        for item in evidence.occupancy_requirements
    ] == [
        ("Channeled Skill", RotationActionKind.SKILL, 1.5),
        ("Big Ultimate", RotationActionKind.ULTIMATE, 2.5),
    ]


def test_saved_build_timing_dedupes_same_action_across_bars_and_skips_zero_timing(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_timing_database(database)
    build = _build(
        ("Channeled Skill", "Instant Skill", "Instant Skill", "Instant Skill", "Instant Skill", "Big Ultimate"),
        ("Channeled Skill", "Instant Skill", "Instant Skill", "Instant Skill", "Instant Skill", "Big Ultimate"),
    )

    evidence = RotationSavedBuildActionTimingService(database).resolve(build)

    assert len(evidence.cooldown_requirements) == 2
    assert len(evidence.occupancy_requirements) == 2
    assert all(item.action_name != "Instant Skill" for item in evidence.cooldown_requirements)
    assert all(item.action_name != "Instant Skill" for item in evidence.occupancy_requirements)


def test_saved_build_timing_surfaces_missing_exact_skill_timing_without_guessing(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_timing_database(database)
    build = _build(("Unknown Skill",))

    evidence = RotationSavedBuildActionTimingService(database).resolve(build)

    assert evidence.cooldown_requirements == ()
    assert evidence.occupancy_requirements == ()
    assert evidence.unresolved == (
        "canonical skill timing not found by exact saved name: Unknown Skill",
    )


def test_saved_build_timing_rejects_conflicting_exact_name_rows(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_timing_database(database)
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO skill(id, name) VALUES(4, 'Channeled Skill')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(404, 'Channeled Skill')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name,
                cooldown, cast_time, channel_time
            ) VALUES(4, 4, 404, 4, 'Channeled Skill', 7000, 2000, 0)
            """
        )
        db.commit()

    evidence = RotationSavedBuildActionTimingService(database).resolve(
        _build(("Channeled Skill",))
    )

    assert evidence.cooldown_requirements == ()
    assert evidence.occupancy_requirements == ()
    assert evidence.unresolved == (
        "canonical skill timing is ambiguous for exact saved name: Channeled Skill",
    )


def test_saved_build_timing_accepts_duplicate_rows_when_timing_agrees(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_timing_database(database)
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO skill(id, name) VALUES(4, 'Channeled Skill')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(404, 'Channeled Skill')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name,
                cooldown, cast_time, channel_time
            ) VALUES(4, 4, 404, 3, 'Channeled Skill', 5000, 1500, 0)
            """
        )
        db.commit()

    evidence = RotationSavedBuildActionTimingService(database).resolve(
        _build(("Channeled Skill",))
    )

    assert evidence.unresolved == ()
    assert len(evidence.cooldown_requirements) == 1
    assert evidence.cooldown_requirements[0].cooldown_seconds == 5.0
    assert len(evidence.occupancy_requirements) == 1
    assert evidence.occupancy_requirements[0].occupancy_seconds == 1.5
