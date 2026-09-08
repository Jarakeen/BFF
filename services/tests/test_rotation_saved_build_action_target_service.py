from __future__ import annotations

from pathlib import Path
import sqlite3
from types import SimpleNamespace

from minmax.rotation_action_target_legality import RotationTargetKind
from minmax.rotation_plan import RotationActionKind
from services.rotation_saved_build_action_target_service import (
    RotationSavedBuildActionTargetService,
)


def _database(path: Path, rows: tuple[tuple[str, str | None, int, int], ...]) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                name TEXT,
                target TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                rank INTEGER,
                raw_name TEXT
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT
            );
            """
        )
        for index, (name, target, rank, ability_id) in enumerate(rows, start=1):
            db.execute(
                "INSERT INTO skill (id, name, target) VALUES (?, ?, ?)",
                (index, name, target),
            )
            db.execute(
                "INSERT INTO skill_rank (id, skill_id, ability_id, rank, raw_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (index, index, ability_id, rank, name),
            )


def _build(front=(), back=()):
    return SimpleNamespace(FrontBarSkills=tuple(front), BackBarSkills=tuple(back))


def test_unambiguous_text_targets_become_explicit_requirements(tmp_path: Path) -> None:
    path = tmp_path / "eso.db"
    _database(
        path,
        (
            ("Enemy Skill", "Enemy", 4, 101),
            ("Self Skill", "Self", 4, 102),
            ("Ground Skill", "Ground", 4, 103),
        ),
    )

    result = RotationSavedBuildActionTargetService(path).resolve(
        _build(front=("Enemy Skill", "Self Skill", "Ground Skill"))
    )

    by_name = {item.action_name: item for item in result.target_requirements}
    assert by_name["Enemy Skill"].allowed_targets == (RotationTargetKind.ENEMY,)
    assert by_name["Self Skill"].allowed_targets == (RotationTargetKind.SELF,)
    assert by_name["Ground Skill"].allowed_targets == (RotationTargetKind.GROUND,)
    assert result.unresolved == ()
    assert result.unresolved_action_names == ()


def test_area_cone_and_blank_targets_remain_unresolved_identity(tmp_path: Path) -> None:
    path = tmp_path / "eso.db"
    _database(
        path,
        (
            ("Area Skill", "Area", 4, 201),
            ("Cone Skill", "Cone", 4, 202),
            ("Blank Skill", "", 4, 203),
        ),
    )

    result = RotationSavedBuildActionTargetService(path).resolve(
        _build(front=("Area Skill", "Cone Skill", "Blank Skill"))
    )

    assert result.target_requirements == ()
    assert set(result.unresolved_action_names) == {
        "Area Skill",
        "Cone Skill",
        "Blank Skill",
    }
    assert any("topology rather than target identity" in item for item in result.unresolved)
    assert any("blank" in item for item in result.unresolved)


def test_highest_rank_conflict_fails_closed_and_lower_rank_difference_does_not(
    tmp_path: Path,
) -> None:
    path = tmp_path / "eso.db"
    _database(
        path,
        (
            ("Progressed Skill", "Self", 1, 301),
            ("Progressed Skill", "Enemy", 4, 302),
            ("Ambiguous Skill", "Enemy", 4, 303),
            ("Ambiguous Skill", "Self", 4, 304),
        ),
    )

    result = RotationSavedBuildActionTargetService(path).resolve(
        _build(front=("Progressed Skill", "Ambiguous Skill"))
    )

    progressed = next(
        item for item in result.target_requirements if item.action_name == "Progressed Skill"
    )
    assert progressed.allowed_targets == (RotationTargetKind.ENEMY,)
    assert "Ambiguous Skill" in result.unresolved_action_names
    assert any("ambiguous at highest rank" in item for item in result.unresolved)


def test_saved_ultimate_keeps_ultimate_action_kind(tmp_path: Path) -> None:
    path = tmp_path / "eso.db"
    _database(path, (("Test Ultimate", "Enemy", 4, 401),))

    result = RotationSavedBuildActionTargetService(path).resolve(
        _build(front=("", "", "", "", "", "Test Ultimate"))
    )

    assert len(result.target_requirements) == 1
    assert result.target_requirements[0].action_kind is RotationActionKind.ULTIMATE
    assert result.target_requirements[0].allowed_targets == (RotationTargetKind.ENEMY,)
