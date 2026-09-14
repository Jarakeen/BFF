import sqlite3
from pathlib import Path
from types import SimpleNamespace

from tools import audit_phase13_xalvakka_add_taunt_acquisition_refresh as audit_module
from tools.audit_phase13_xalvakka_add_earliest_event_signal import AddSignalObservation


def _signal(actor_name="Iron Atronach", actor_id=104, instance_id=1):
    return AddSignalObservation(
        report_code="R",
        fight_id=34,
        actor_name=actor_name,
        actor_id=actor_id,
        instance_id=instance_id,
        fight_start_ms=1000.0,
        first_involving_ms=2000.0,
        first_source_ms=2100.0,
        first_cast_ms=2500.0,
        first_friendly_damage_ms=3000.0,
    )


def _db(path: Path):
    db = sqlite3.connect(path)
    db.executescript(
        """
        CREATE TABLE log_event (
            report_code TEXT,
            fight_id INTEGER,
            event_index INTEGER,
            timestamp REAL,
            event_type TEXT,
            source_id INTEGER,
            source_is_friendly INTEGER,
            target_id INTEGER,
            target_instance INTEGER,
            target_is_friendly INTEGER,
            ability_game_id INTEGER,
            raw_json TEXT
        );
        CREATE TABLE log_report_actor (
            report_code TEXT,
            actor_id INTEGER,
            name TEXT,
            display_name TEXT
        );
        """
    )
    db.execute(
        "INSERT INTO log_report_actor VALUES ('R', 1, 'Off Tank', 'Off Tank')"
    )
    return db


def test_observe_uses_first_canonical_taunt_cast_as_acquisition_and_later_casts_as_repeats(tmp_path, monkeypatch):
    path = tmp_path / "runtime.db"
    db = _db(path)
    db.executemany(
        "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            ("R", 34, 1, 2600.0, "cast", 1, 1, 104, 1, 0, 38250, "{}"),
            ("R", 34, 2, 12600.0, "cast", 1, 1, 104, 1, 0, 38250, "{}"),
            ("R", 34, 3, 13000.0, "damage", 1, 1, 104, 1, 0, 38250, "{}"),
        ),
    )
    db.commit()
    db.close()

    monkeypatch.setattr(audit_module, "observe_add_signals", lambda _path: (_signal(),))
    monkeypatch.setattr(
        audit_module,
        "canonical_taunt_abilities",
        lambda _path: (SimpleNamespace(ability_id=38250, skill_name="Puncture"),),
    )

    result = audit_module.observe(path, tmp_path / "game.db")

    assert len(result) == 1
    row = result[0]
    assert row.acquisition_lag_ms == 500.0
    assert row.taunt_cast_times_ms == (2600.0, 12600.0)
    assert row.refresh_intervals_ms == (10000.0,)
    assert row.taunt_sources == (1,)


def test_audit_keeps_untaunted_instances_visible_in_coverage(tmp_path, monkeypatch):
    path = tmp_path / "runtime.db"
    db = _db(path)
    db.commit()
    db.close()

    rows = (
        audit_module.AddTauntActionObservation(
            report_code="R",
            fight_id=34,
            actor_name="Iron Atronach",
            actor_id=104,
            instance_id=1,
            activity_boundary_ms=1000.0,
            first_taunt_cast_ms=2000.0,
            taunt_cast_times_ms=(2000.0, 12000.0),
            taunt_sources=(1,),
        ),
        audit_module.AddTauntActionObservation(
            report_code="R",
            fight_id=34,
            actor_name="Iron Atronach",
            actor_id=104,
            instance_id=2,
            activity_boundary_ms=1000.0,
            first_taunt_cast_ms=None,
            taunt_cast_times_ms=(),
            taunt_sources=(),
        ),
    )
    monkeypatch.setattr(audit_module, "observe", lambda *_args, **_kwargs: rows)

    lines = audit_module.audit(path, tmp_path / "game.db")

    assert any(
        "ACTOR_SUMMARY: actor=Iron Atronach instances=2 taunted_instances=1 untaunted_instances=1"
        in line
        for line in lines
    )
    assert "TAUNTED_ADD_INSTANCES=1" in lines
    assert "REPEATED_TAUNT_ADD_INSTANCES=1" in lines
