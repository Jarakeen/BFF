from __future__ import annotations

import sqlite3

from minmax.rotation_plan import RotationAction, RotationActionKind
from services.rotation_candidate_periodic_damage_timing_evidence_service import (
    RotationCandidatePeriodicDamageTimingEvidenceService,
)


def _database(tmp_path, *, coef_description: str, duration_ms: int = 6000, is_dot: int = 1):
    path = tmp_path / "eso.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER,
                ability_id INTEGER,
                rank INTEGER,
                morph INTEGER,
                raw_name TEXT
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                base_ability_id INTEGER,
                morph INTEGER,
                duration INTEGER,
                coef_description TEXT
            );
            CREATE TABLE skill_coefficient (
                skill_rank_id INTEGER,
                coefficient_number INTEGER,
                type TEXT,
                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL
            );
            CREATE TABLE skill_component_classification (
                skill_rank_id INTEGER,
                coefficient_number INTEGER,
                effect_kind TEXT,
                damage_type TEXT,
                is_dot INTEGER,
                is_aoe INTEGER,
                can_crit INTEGER,
                source TEXT,
                confidence REAL
            );
            """
        )
        db.execute(
            "INSERT INTO skill VALUES (1, 100, 'Burning Test')"
        )
        db.execute(
            "INSERT INTO skill_rank VALUES (10, 1, 101, 4, 0, 'Burning Test')"
        )
        db.execute(
            "INSERT INTO ability VALUES (101, 'Burning Test', 100, 0, ?, ?)",
            (duration_ms, coef_description),
        )
        db.execute(
            "INSERT INTO skill_coefficient VALUES (10, 1, '8', 0.1, 1.0, 0.0, 1.0, NULL)"
        )
        db.execute(
            "INSERT INTO skill_component_classification VALUES (10, 1, 'damage', 'flame', ?, 0, 1, 'test', 1.0)",
            (is_dot,),
        )
    return path


def _action(kind=RotationActionKind.SKILL, name="burning_test"):
    return RotationAction(5.0, 0, kind, name=name, bar="front")


def test_periodic_damage_timing_resolves_canonical_cadence_and_duration(tmp_path) -> None:
    path = _database(
        tmp_path,
        coef_description="Deals $1 Flame Damage every 2 seconds.",
        duration_ms=6000,
    )
    service = RotationCandidatePeriodicDamageTimingEvidenceService(path)

    report = service.inspect_action(_action())

    assert report.unresolved == ()
    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.source_name == "Burning Test"
    assert entry.coefficient_number == 1
    assert entry.skill_rank_id == 10
    assert entry.ability_id == 101
    assert entry.cadence_seconds == 2.0
    assert entry.duration_seconds == 6.0
    assert entry.timing_ready_for_runtime_binding is True
    assert "first actual periodic-damage tick offset" in entry.runtime_binding_gaps[0]
    assert "recast/refresh boundary semantics" in entry.runtime_binding_gaps[1]


def test_periodic_damage_timing_uses_fixed_count_duration_without_inventing_interval(tmp_path) -> None:
    path = _database(
        tmp_path,
        coef_description="Deals $1 Flame Damage three times over 6 seconds.",
        duration_ms=6000,
    )
    service = RotationCandidatePeriodicDamageTimingEvidenceService(path)

    entry = service.inspect_action(_action()).entries[0]

    assert entry.duration_seconds == 6.0
    assert entry.cadence_seconds is None
    assert entry.timing_ready_for_runtime_binding is False
    assert any("exact within-window tick interval remains unresolved" in item for item in entry.unresolved)


def test_periodic_damage_timing_ignores_verified_non_dot_damage_components(tmp_path) -> None:
    path = _database(
        tmp_path,
        coef_description="Deals $1 Flame Damage.",
        is_dot=0,
    )
    service = RotationCandidatePeriodicDamageTimingEvidenceService(path)

    report = service.inspect_action(_action())

    assert report.entries == ()
    assert report.unresolved == ()


def test_periodic_damage_timing_fails_closed_when_cadence_is_not_proven(tmp_path) -> None:
    path = _database(
        tmp_path,
        coef_description="Deals $1 Flame Damage over time.",
        duration_ms=6000,
    )
    service = RotationCandidatePeriodicDamageTimingEvidenceService(path)

    report = service.inspect_action(_action())

    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.duration_seconds == 6.0
    assert entry.cadence_seconds is None
    assert entry.timing_ready_for_runtime_binding is False
    assert any("canonical periodic cadence is unresolved" in item for item in entry.unresolved)


def test_periodic_damage_timing_rejects_non_skill_action() -> None:
    action = _action(RotationActionKind.LIGHT_ATTACK, name=None)
    service = RotationCandidatePeriodicDamageTimingEvidenceService("missing.db")

    report = service.inspect_action(action)

    assert report.entries == ()
    assert report.unresolved == (
        "light_attack is not a scheduled skill action for periodic-damage timing",
    )
