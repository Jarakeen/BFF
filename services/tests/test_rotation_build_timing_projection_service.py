from __future__ import annotations

import sqlite3

import pytest

from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild, IllegalBuildError
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.role import Role
from minmax.rotation_plan import RotationActionKind
from services.rotation_build_timing_projection_service import (
    RotationBuildTimingPolicy,
    RotationBuildTimingProjectionService,
)


def _database(tmp_path):
    path = tmp_path / "eso.db"
    rows = (
        (1, 100, "Class Cast", 101, 1100.0, 0.0, 0),
        (2, 200, "Weapon Channel", 201, 0.0, 3000.0, 1),
        (3, 300, "Class Ultimate", 301, 500.0, 0.0, 0),
        (4, 400, "Instant Skill", 401, 0.0, 0.0, 0),
    )
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE skill (id INTEGER PRIMARY KEY, base_ability_id INTEGER NOT NULL, name TEXT)"
        )
        db.execute(
            """
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            )
            """
        )
        db.execute(
            """
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                cast_time REAL,
                channel_time REAL,
                is_channeled INTEGER
            )
            """
        )
        for skill_id, base_id, name, ability_id, cast, channel, channeled in rows:
            db.execute(
                "INSERT INTO skill (id, base_ability_id, name) VALUES (?, ?, ?)",
                (skill_id, base_id, name),
            )
            db.execute(
                """
                INSERT INTO skill_rank (id, skill_id, ability_id, raw_name, rank, morph)
                VALUES (?, ?, ?, ?, 4, 0)
                """,
                (skill_id * 10, skill_id, ability_id, name),
            )
            db.execute(
                """
                INSERT INTO ability (ability_id, name, cast_time, channel_time, is_channeled)
                VALUES (?, ?, ?, ?, ?)
                """,
                (ability_id, name, cast, channel, channeled),
            )
        db.commit()
    return path


def _slot(skill_id: str, line: str, *, ultimate: bool = False) -> SlottedSkill:
    return SlottedSkill(
        skill_id=skill_id,
        skill_line_id=line,
        is_ultimate=ultimate,
        is_cast=True,
    )


def _build(*, weapon_line: str = "restoration_staff") -> CharacterBuild:
    return CharacterBuild(
        name="All Combat Timing Build",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.RESTORATION_STAFF),
            off_hand=None,
            slots=(
                _slot("class_cast", "animal_companions"),
                _slot("weapon_channel", weapon_line),
                _slot("class_cast", "animal_companions"),
                _slot("instant_skill", "animal_companions"),
                _slot("class_cast", "animal_companions"),
                _slot("class_ultimate", "animal_companions", ultimate=True),
            ),
        ),
    )


def _policy() -> RotationBuildTimingPolicy:
    return RotationBuildTimingPolicy(
        skill_blocked_action_kinds=(
            RotationActionKind.SKILL,
            RotationActionKind.BAR_SWAP,
        ),
        ultimate_blocked_action_kinds=(RotationActionKind.SKILL,),
    )


def test_projects_class_weapon_and_ultimate_timing_through_one_path(tmp_path) -> None:
    projection = RotationBuildTimingProjectionService(_database(tmp_path)).project(
        build=_build(),
        policy=_policy(),
    )

    assert projection.unresolved == ()
    assert {item.skill_id for item in projection.evidence} == {
        "class_cast",
        "weapon_channel",
        "instant_skill",
        "class_ultimate",
    }
    rules = {(rule.action_kind, rule.action_name): rule for rule in projection.rules}
    assert rules[(RotationActionKind.SKILL, "Class Cast")].occupancy_seconds == 1.1
    assert rules[(RotationActionKind.SKILL, "Weapon Channel")].occupancy_seconds == 3.0
    assert rules[(RotationActionKind.ULTIMATE, "Class Ultimate")].occupancy_seconds == 0.5
    assert (RotationActionKind.SKILL, "Instant Skill") not in rules


def test_duplicate_slotted_copies_do_not_duplicate_timing_rules(tmp_path) -> None:
    projection = RotationBuildTimingProjectionService(_database(tmp_path)).project(
        build=_build(),
        policy=_policy(),
    )

    class_rules = [
        rule
        for rule in projection.rules
        if rule.action_kind is RotationActionKind.SKILL and rule.action_name == "Class Cast"
    ]
    assert len(class_rules) == 1


def test_projection_preserves_separate_skill_and_ultimate_blocking_policy(tmp_path) -> None:
    projection = RotationBuildTimingProjectionService(_database(tmp_path)).project(
        build=_build(),
        policy=_policy(),
    )

    by_name = {rule.action_name: rule for rule in projection.rules}
    assert by_name["Class Cast"].blocked_action_kinds == (
        RotationActionKind.SKILL,
        RotationActionKind.BAR_SWAP,
    )
    assert by_name["Class Ultimate"].blocked_action_kinds == (
        RotationActionKind.SKILL,
    )


def test_illegal_weapon_skill_line_is_rejected_before_timing_projection(tmp_path) -> None:
    service = RotationBuildTimingProjectionService(_database(tmp_path))

    with pytest.raises(IllegalBuildError) as exc_info:
        service.project(build=_build(weapon_line="destruction_staff"), policy=_policy())

    assert "weapon skill line 'destruction_staff'" in str(exc_info.value)
    assert "restoration_staff" in str(exc_info.value)


def test_missing_canonical_skill_timing_remains_explicitly_unresolved(tmp_path) -> None:
    build = _build()
    slots = list(build.front_bar.slots)
    slots[4] = _slot("unknown_skill", "animal_companions")
    build = CharacterBuild(
        name=build.name,
        character_class=build.character_class,
        role=build.role,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.RESTORATION_STAFF),
            off_hand=None,
            slots=tuple(slots),
        ),
    )

    projection = RotationBuildTimingProjectionService(_database(tmp_path)).project(
        build=build,
        policy=_policy(),
    )

    assert projection.rules
    assert any("unknown_skill" in item for item in projection.unresolved)
    assert any("not found" in item.casefold() for item in projection.unresolved)
