from __future__ import annotations

import sqlite3

from minmax.rotation_plan import RotationActionKind
from services.rotation_skill_timing_evidence_service import (
    RotationSkillTimingEvidenceService,
)


def _database(tmp_path, *, cast_time, channel_time, is_channeled, name="Test Skill"):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER NOT NULL,
                name TEXT
            )
            """
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
        db.execute(
            "INSERT INTO skill (id, base_ability_id, name) VALUES (1, 100, ?)",
            (name,),
        )
        db.execute(
            """
            INSERT INTO skill_rank (id, skill_id, ability_id, raw_name, rank, morph)
            VALUES (10, 1, 101, ?, 4, 0)
            """,
            (name,),
        )
        db.execute(
            """
            INSERT INTO ability (ability_id, name, cast_time, channel_time, is_channeled)
            VALUES (101, ?, ?, ?, ?)
            """,
            (name, cast_time, channel_time, int(is_channeled)),
        )
        db.commit()
    return path


def test_resolves_exact_cast_timing_and_converts_milliseconds(tmp_path) -> None:
    service = RotationSkillTimingEvidenceService(
        _database(tmp_path, cast_time=1100.0, channel_time=0.0, is_channeled=False)
    )

    resolution = service.resolve_skill("test_skill")

    assert resolution.unresolved == ()
    assert resolution.evidence is not None
    assert resolution.evidence.skill_id == "test_skill"
    assert resolution.evidence.ability_id == 101
    assert resolution.evidence.cast_time_seconds == 1.1
    assert resolution.evidence.channel_time_seconds == 0.0
    assert resolution.evidence.occupancy_seconds == 1.1
    assert resolution.evidence.source == "canonical ability table ability_id=101"


def test_channeled_skill_uses_channel_time_not_cast_time(tmp_path) -> None:
    service = RotationSkillTimingEvidenceService(
        _database(tmp_path, cast_time=500.0, channel_time=3000.0, is_channeled=True)
    )

    evidence = service.resolve_skill("Test Skill").evidence

    assert evidence is not None
    assert evidence.cast_time_seconds == 0.5
    assert evidence.channel_time_seconds == 3.0
    assert evidence.occupancy_seconds == 3.0


def test_instant_skill_does_not_invent_gcd_occupancy(tmp_path) -> None:
    service = RotationSkillTimingEvidenceService(
        _database(tmp_path, cast_time=0.0, channel_time=0.0, is_channeled=False)
    )

    evidence = service.resolve_skill("test_skill").evidence
    rule, unresolved = service.occupancy_rule(
        skill_id="test_skill",
        blocked_action_kinds=(RotationActionKind.SKILL,),
    )

    assert evidence is not None
    assert evidence.occupancy_seconds is None
    assert rule is None
    assert unresolved == ()


def test_occupancy_bridge_preserves_explicit_blocking_policy(tmp_path) -> None:
    service = RotationSkillTimingEvidenceService(
        _database(tmp_path, cast_time=1250.0, channel_time=0.0, is_channeled=False)
    )

    rule, unresolved = service.occupancy_rule(
        skill_id="test_skill",
        blocked_action_kinds=(
            RotationActionKind.SKILL,
            RotationActionKind.BAR_SWAP,
        ),
    )

    assert unresolved == ()
    assert rule is not None
    assert rule.action_kind is RotationActionKind.SKILL
    assert rule.action_name == "Test Skill"
    assert rule.occupancy_seconds == 1.25
    assert rule.blocked_action_kinds == (
        RotationActionKind.SKILL,
        RotationActionKind.BAR_SWAP,
    )
    assert rule.source == "canonical ability table ability_id=101"


def test_missing_skill_identity_fails_closed(tmp_path) -> None:
    service = RotationSkillTimingEvidenceService(
        _database(tmp_path, cast_time=1000.0, channel_time=0.0, is_channeled=False)
    )

    resolution = service.resolve_skill("not_a_real_skill")

    assert resolution.evidence is None
    assert resolution.unresolved
    assert "not found" in resolution.unresolved[0].casefold()


def test_invalid_source_timing_fails_closed(tmp_path) -> None:
    service = RotationSkillTimingEvidenceService(
        _database(tmp_path, cast_time=-1.0, channel_time=0.0, is_channeled=False)
    )

    resolution = service.resolve_skill("test_skill")

    assert resolution.evidence is None
    assert resolution.unresolved == ("canonical cast_time is invalid: -1.0",)


def test_missing_database_fails_closed(tmp_path) -> None:
    service = RotationSkillTimingEvidenceService(tmp_path / "missing.db")

    resolution = service.resolve_skill("test_skill")

    assert resolution.evidence is None
    assert "database is unavailable" in resolution.unresolved[0]
