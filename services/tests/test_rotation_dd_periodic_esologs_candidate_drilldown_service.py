import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_candidate_drilldown_service import (
    RotationDDPeriodicEsoLogsCandidateDrilldownService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "detonating_siphon"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=8, morph=1, base_ability_id=500),
            unresolved=(),
        )


def _canonical(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER, ability_id INTEGER, morph INTEGER)")
        db.execute("INSERT INTO skill_rank VALUES (1,8,500,1)")
        db.commit()


def _logs(path):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT, fight_id INTEGER, event_index INTEGER,
                timestamp REAL, event_type TEXT, source_id INTEGER,
                target_id INTEGER, ability_game_id INTEGER,
                cast_track_id INTEGER, raw_json TEXT
            )
            """
        )
        db.commit()


def _event(path, *, index, timestamp, event_type, ability_id, name, cast_track_id, target_id=99):
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                "R", 1, index, timestamp, event_type, 42, target_id,
                ability_id, cast_track_id,
                json.dumps({"ability": {"name": name}}),
            ),
        )
        db.commit()


def _service(canonical, logs):
    service = RotationDDPeriodicEsoLogsCandidateDrilldownService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    return service


def test_reports_exact_same_track_offsets_and_active_end_clustering(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", ability_id=500, name="Detonating Siphon", cast_track_id=77)
    _event(logs, index=2, timestamp=1020, event_type="damage", ability_id=118766, name="Siphon Damage", cast_track_id=77, target_id=99)
    _event(logs, index=3, timestamp=1021, event_type="damage", ability_id=118766, name="Siphon Damage", cast_track_id=77, target_id=100)
    _event(logs, index=4, timestamp=2020, event_type="damage", ability_id=118766, name="Siphon Damage", cast_track_id=77)
    _event(logs, index=5, timestamp=21000, event_type="damage", ability_id=118766, name="Siphon Damage", cast_track_id=77)
    _event(logs, index=6, timestamp=1500, event_type="damage", ability_id=118766, name="Siphon Damage", cast_track_id=88)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_id=118766,
        active_window_seconds=20.0,
    )

    assert report.cast_count == 1
    assert report.linked_cast_count == 1
    assert report.event_count == 5
    assert report.linked_event_count == 4
    assert report.ability_names == ("Siphon Damage",)
    assert report.event_types == (("damage", 5),)
    assert report.target_count == 2
    assert report.first_offsets_seconds == (0.02,)
    assert report.last_offsets_seconds == (20.0,)
    assert report.within_cast_intervals_seconds == (1.0, 18.98)
    assert report.near_active_end_count == 1
    assert report.unresolved == ()


def test_unlinked_candidate_remains_unresolved(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", ability_id=500, name="Detonating Siphon", cast_track_id=77)
    _event(logs, index=2, timestamp=1500, event_type="damage", ability_id=118766, name="Candidate", cast_track_id=88)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_id=118766,
        active_window_seconds=20.0,
    )

    assert report.linked_cast_count == 0
    assert report.linked_event_count == 0
    assert any("no exact same-cast-track observations" in message for message in report.unresolved)
