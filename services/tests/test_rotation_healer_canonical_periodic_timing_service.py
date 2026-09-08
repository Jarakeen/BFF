import sqlite3

from minmax.skill_component_runtime_timing import RuntimeCadenceBoundKind
from services.rotation_healer_canonical_periodic_timing_service import (
    RotationHealerCanonicalPeriodicTimingService,
)


def _database(tmp_path, *, description, duration_ms=6000):
    path = tmp_path / "eso.db"
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
            "INSERT INTO skill(id, base_ability_id, name) VALUES (1, 100, 'Budding Seeds')"
        )
        db.execute(
            """
            INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph)
            VALUES (10, 1, 101, 'Budding Seeds', 4, 1)
            """
        )
        db.execute(
            """
            INSERT INTO ability(ability_id, name, coef_description, duration)
            VALUES (101, 'Budding Seeds', ?, ?)
            """,
            (description, duration_ms),
        )
        db.execute(
            """
            INSERT INTO skill_coefficient(
                skill_rank_id, coefficient_number, type, a, b, c, r, avg
            ) VALUES (10, 2, '8', 0.1, 1.0, 0.0, 1.0, NULL)
            """
        )
    return path


def test_resolves_budding_seeds_cadence_and_ability_duration(tmp_path):
    path = _database(
        tmp_path,
        description="While the field grows, you and allies are healed for $2 Health every 1 second.",
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Budding Seeds",
        coefficient_number=2,
    )

    assert result.unresolved == ()
    assert result.skill_rank_id == 10
    assert result.ability_id == 101
    assert result.cadence_seconds == 1.0
    assert result.duration_seconds == 6.0
    assert result.timing is not None
    assert result.timing.bound_kind is RuntimeCadenceBoundKind.EXPLICIT_STATE_WINDOW
    assert result.timing_ready_for_runtime_binding
    assert any("every 1 second" in item for item in result.evidence)
    assert any("ability.duration" in item for item in result.evidence)


def test_does_not_invent_first_tick_or_refresh_semantics(tmp_path):
    path = _database(
        tmp_path,
        description="While the field grows, you and allies are healed for $2 Health every 1 second.",
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Budding Seeds",
        coefficient_number=2,
    )

    assert result.timing_ready_for_runtime_binding
    assert not hasattr(result, "first_tick_offset_seconds")
    assert not hasattr(result, "refresh_policy")


def test_non_periodic_heal_text_is_rejected_as_periodic_timing(tmp_path):
    path = _database(
        tmp_path,
        description="You and allies are healed for $2 Health.",
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Budding Seeds",
        coefficient_number=2,
    )

    assert result.timing is None
    assert not result.timing_ready_for_runtime_binding
    assert result.unresolved == (
        "Budding Seeds coefficient 2: canonical/reviewed identity does not prove periodic healing",
    )


def test_missing_coefficient_owned_fragment_fails_closed(tmp_path):
    path = _database(
        tmp_path,
        description="While the field grows, you and allies are healed for $1 Health every 1 second.",
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Budding Seeds",
        coefficient_number=2,
    )

    assert result.timing is None
    assert not result.timing_ready_for_runtime_binding
    assert result.unresolved == (
        "Budding Seeds coefficient 2: coefficient-owned text fragment is unavailable",
    )


def test_missing_duration_preserves_cadence_but_blocks_runtime_ready(tmp_path):
    path = _database(
        tmp_path,
        description="While the field grows, you and allies are healed for $2 Health every 1 second.",
        duration_ms=0,
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Budding Seeds",
        coefficient_number=2,
    )

    assert result.cadence_seconds == 1.0
    assert result.duration_seconds is None
    assert not result.timing_ready_for_runtime_binding
    assert result.unresolved == (
        "no positive canonical duration evidence found for Budding Seeds",
    )


def test_unknown_skill_returns_identity_gap(tmp_path):
    path = _database(
        tmp_path,
        description="While the field grows, you and allies are healed for $2 Health every 1 second.",
    )

    result = RotationHealerCanonicalPeriodicTimingService(path).resolve(
        source_name="Imaginary Heal",
        coefficient_number=2,
    )

    assert result.skill_rank_id is None
    assert result.ability_id is None
    assert result.unresolved
    assert "not found" in result.unresolved[0].casefold()
