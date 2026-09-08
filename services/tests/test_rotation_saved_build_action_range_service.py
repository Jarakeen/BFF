from __future__ import annotations

import sqlite3
from types import SimpleNamespace

from minmax.rotation_plan import RotationActionKind
from services.rotation_saved_build_action_range_service import (
    RotationSavedBuildActionRangeService,
)


def _create_range_database(path) -> None:
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
                min_range REAL,
                max_range REAL
            );
            """
        )
        db.execute("INSERT INTO skill(id, name) VALUES(1, 'Ranged Skill')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(101, 'Ranged Skill')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name, min_range, max_range
            ) VALUES(1, 1, 101, 4, 'Ranged Skill', 5, 28)
            """
        )
        db.execute("INSERT INTO skill(id, name) VALUES(2, 'Ranged Ultimate')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(202, 'Ranged Ultimate')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name, min_range, max_range
            ) VALUES(2, 2, 202, 4, 'Ranged Ultimate', 0, 35)
            """
        )
        db.execute("INSERT INTO skill(id, name) VALUES(3, 'No Hard Range')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(303, 'No Hard Range')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name, min_range, max_range
            ) VALUES(3, 3, 303, 4, 'No Hard Range', 0, 0)
            """
        )
        db.commit()


def _build(front, back=()):
    return SimpleNamespace(
        FrontBarSkills=tuple(front),
        BackBarSkills=tuple(back),
    )


def test_saved_build_range_preserves_imported_limits_and_action_kind(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_range_database(database)
    build = _build(
        (
            "Ranged Skill",
            "No Hard Range",
            "No Hard Range",
            "No Hard Range",
            "No Hard Range",
            "Ranged Ultimate",
        )
    )

    evidence = RotationSavedBuildActionRangeService(database).resolve(build)

    assert evidence.unresolved == ()
    assert [
        (item.action_name, item.action_kind, item.minimum_range, item.maximum_range)
        for item in evidence.range_requirements
    ] == [
        ("Ranged Skill", RotationActionKind.SKILL, 5.0, 28.0),
        ("Ranged Ultimate", RotationActionKind.ULTIMATE, 0.0, 35.0),
    ]


def test_saved_build_range_dedupes_across_bars_and_skips_unbounded_rows(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_range_database(database)
    build = _build(
        ("Ranged Skill", "No Hard Range", "No Hard Range", "No Hard Range", "No Hard Range", "Ranged Ultimate"),
        ("Ranged Skill", "No Hard Range", "No Hard Range", "No Hard Range", "No Hard Range", "Ranged Ultimate"),
    )

    evidence = RotationSavedBuildActionRangeService(database).resolve(build)

    assert len(evidence.range_requirements) == 2
    assert all(item.action_name != "No Hard Range" for item in evidence.range_requirements)


def test_saved_build_range_surfaces_missing_exact_skill_without_guessing(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_range_database(database)
    build = _build(("Unknown Skill",))

    evidence = RotationSavedBuildActionRangeService(database).resolve(build)

    assert evidence.range_requirements == ()
    assert evidence.unresolved == (
        "canonical skill range not found by exact saved name: Unknown Skill",
    )


def test_saved_build_range_tolerates_minimal_build_stubs(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_range_database(database)

    evidence = RotationSavedBuildActionRangeService(database).resolve(object())

    assert evidence.range_requirements == ()
    assert evidence.unresolved == ()


def test_saved_build_range_rejects_conflicting_exact_name_rows(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_range_database(database)
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO skill(id, name) VALUES(4, 'Ranged Skill')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(404, 'Ranged Skill')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name, min_range, max_range
            ) VALUES(4, 4, 404, 4, 'Ranged Skill', 0, 22)
            """
        )
        db.commit()

    evidence = RotationSavedBuildActionRangeService(database).resolve(
        _build(("Ranged Skill",))
    )

    assert evidence.range_requirements == ()
    assert evidence.unresolved == (
        "canonical skill range is ambiguous for exact saved name: Ranged Skill",
    )


def test_saved_build_range_accepts_duplicate_rows_when_range_agrees(tmp_path) -> None:
    database = tmp_path / "eso.db"
    _create_range_database(database)
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO skill(id, name) VALUES(4, 'Ranged Skill')")
        db.execute("INSERT INTO ability(ability_id, name) VALUES(404, 'Ranged Skill')")
        db.execute(
            """
            INSERT INTO skill_rank(
                id, skill_id, ability_id, rank, raw_name, min_range, max_range
            ) VALUES(4, 4, 404, 3, 'Ranged Skill', 5, 28)
            """
        )
        db.commit()

    evidence = RotationSavedBuildActionRangeService(database).resolve(
        _build(("Ranged Skill",))
    )

    assert evidence.unresolved == ()
    assert len(evidence.range_requirements) == 1
    requirement = evidence.range_requirements[0]
    assert requirement.minimum_range == 5.0
    assert requirement.maximum_range == 28.0
