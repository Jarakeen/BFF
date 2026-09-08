import sqlite3

from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingService,
)
from services.rotation_healer_u50_skill_component_repository import (
    RotationHealerU50SkillComponentRepository,
)


def _database(tmp_path, *, name, description, duration_ms, rank_id=10):
    path = tmp_path / f"{name.replace(' ', '_').lower()}.db"
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE skill (
                id INTEGER PRIMARY KEY,
                base_ability_id INTEGER NOT NULL,
                name TEXT
            );
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                raw_name TEXT,
                rank INTEGER,
                morph INTEGER
            );
            CREATE TABLE ability (
                ability_id INTEGER PRIMARY KEY,
                name TEXT,
                coef_description TEXT,
                duration REAL
            );
            CREATE TABLE skill_coefficient (
                skill_rank_id INTEGER NOT NULL,
                coefficient_number INTEGER NOT NULL,
                type TEXT,
                a REAL,
                b REAL,
                c REAL,
                r REAL,
                avg REAL
            );
            """
        )
        db.execute(
            "INSERT INTO skill(id, base_ability_id, name) VALUES (1, 100, ?)",
            (name,),
        )
        db.execute(
            """
            INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph)
            VALUES (?, 1, 101, ?, 4, 1)
            """,
            (rank_id, name),
        )
        db.execute(
            """
            INSERT INTO ability(ability_id, name, coef_description, duration)
            VALUES (101, ?, ?, ?)
            """,
            (name, description, duration_ms),
        )
        db.execute(
            """
            INSERT INTO skill_coefficient(
                skill_rank_id, coefficient_number, type, a, b, c, r, avg
            ) VALUES (?, 1, '8', 0.1, 1.0, 0.0, 1.0, NULL)
            """,
            (rank_id,),
        )
    return path


def test_illustrious_healing_uses_reviewed_one_second_static_hot_cadence(tmp_path):
    path = _database(
        tmp_path,
        name="Illustrious Healing",
        description=(
            "Summon restoring spirits with your staff, healing you and your allies "
            "in the target area for $1 Health over 15 seconds."
        ),
        duration_ms=15000,
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Illustrious Healing",
        coefficient_number=1,
    )

    assert result.unresolved == ()
    assert result.cadence_seconds == 1.0
    assert result.duration_seconds == 15.0
    assert result.timing_ready_for_runtime_binding
    assert any("reviewed U50 cadence" in item for item in result.evidence)
    assert any("v8.1.5" in item for item in result.evidence)
    assert any("static-based" in item for item in result.evidence)


def test_echoing_vigor_uses_reviewed_two_second_target_hot_cadence(tmp_path):
    path = _database(
        tmp_path,
        name="Echoing Vigor",
        description=(
            "Let loose a battle cry, instilling you and your allies with resolve "
            "and healing for $1 Health over 16 seconds."
        ),
        duration_ms=16000,
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Echoing Vigor",
        coefficient_number=1,
    )

    assert result.unresolved == ()
    assert result.cadence_seconds == 2.0
    assert result.duration_seconds == 16.0
    assert result.timing_ready_for_runtime_binding
    assert any("target-based" in item for item in result.evidence)


def test_radiating_regeneration_combines_reviewed_periodic_identity_with_reviewed_cadence(tmp_path):
    path = _database(
        tmp_path,
        name="Radiating Regeneration",
        description=(
            "Share your staff's life-giving energy, healing you or up to 3 nearby "
            "allies for $1 over 10 seconds."
        ),
        duration_ms=10000,
        rank_id=RotationHealerU50SkillComponentRepository.RADIATING_REGENERATION_RANK_ID,
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Radiating Regeneration",
        coefficient_number=1,
    )

    assert result.unresolved == ()
    assert result.cadence_seconds == 2.0
    assert result.duration_seconds == 10.0
    assert result.timing_ready_for_runtime_binding
    assert any("HEAL / PERIODIC" in item for item in result.evidence)
    assert any("target-based" in item for item in result.evidence)


def test_reviewed_cadence_still_does_not_create_periodic_identity_for_wrong_rank(tmp_path):
    path = _database(
        tmp_path,
        name="Radiating Regeneration",
        description=(
            "Share your staff's life-giving energy, healing you or up to 3 nearby "
            "allies for $1 over 10 seconds."
        ),
        duration_ms=10000,
        rank_id=10,
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Radiating Regeneration",
        coefficient_number=1,
    )

    assert result.timing is None
    assert not result.timing_ready_for_runtime_binding
    assert result.unresolved == (
        "Radiating Regeneration coefficient 1: canonical/reviewed identity does not prove periodic healing",
    )
