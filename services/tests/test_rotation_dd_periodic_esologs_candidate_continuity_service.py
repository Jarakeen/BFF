import hashlib
import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_candidate_continuity_service import (
    RotationDDPeriodicEsoLogsCandidateContinuityService,
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
        db.execute(
            "CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER, ability_id INTEGER, morph INTEGER)"
        )
        db.execute("INSERT INTO skill_rank VALUES (1,8,500,1)")
        db.commit()


def _logs(path):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT, fight_id INTEGER, event_index INTEGER,
                timestamp REAL, event_type TEXT, source_id INTEGER,
                ability_game_id INTEGER, cast_track_id INTEGER, raw_json TEXT
            )
            """
        )
        db.commit()


def _event(path, *, index, timestamp, event_type, source_id, ability_id, cast_track_id, name=""):
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "R",
                1,
                index,
                timestamp,
                event_type,
                source_id,
                ability_id,
                cast_track_id,
                json.dumps({"ability": {"name": name}}) if name else "{}",
            ),
        )
        db.commit()


def _service(canonical, logs):
    service = RotationDDPeriodicEsoLogsCandidateContinuityService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    return service


def test_clusters_near_simultaneous_fanout_before_gap_measurement(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=1100, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=3, timestamp=1120, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=4, timestamp=2100, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=5, timestamp=3100, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=6, timestamp=7100, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=7, timestamp=22000, event_type="other", source_id=99, ability_id=1, cast_track_id=None)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766,),
        active_window_seconds=20.0,
        cluster_tolerance_seconds=0.05,
    )

    assert report.cast_count == 1
    summary = report.summaries[0]
    assert summary.linked_cast_count == 1
    five = next(item for item in summary.thresholds if item.threshold_seconds == 5.0)
    assert five.qualifying_cast_count == 1
    assert five.median_occurrence_count == 4.0
    assert five.median_first_offset_seconds == 0.1
    assert five.median_last_offset_seconds == 6.1
    assert five.median_gap_seconds == 1.0
    assert five.median_max_gap_seconds == 4.0
    assert five.maximum_gap_seconds == 4.0
    ten = next(item for item in summary.thresholds if item.threshold_seconds == 10.0)
    assert ten.qualifying_cast_count == 0


def test_recast_censors_old_stream_and_audit_is_read_only(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=2000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=3, timestamp=5000, event_type="cast", source_id=42, ability_id=500, cast_track_id=78, name="Detonating Siphon")
    _event(logs, index=4, timestamp=9000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=5, timestamp=6000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=78)
    _event(logs, index=6, timestamp=12000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=78)
    _event(logs, index=7, timestamp=26000, event_type="other", source_id=99, ability_id=1, cast_track_id=None)

    before = hashlib.sha256(logs.read_bytes()).hexdigest()
    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766,),
        active_window_seconds=20.0,
    )
    after = hashlib.sha256(logs.read_bytes()).hexdigest()

    assert before == after
    summary = report.summaries[0]
    assert summary.linked_cast_count == 2
    five = next(item for item in summary.thresholds if item.threshold_seconds == 5.0)
    assert five.qualifying_cast_count == 1
    assert five.median_first_offset_seconds == 1.0
    assert five.median_last_offset_seconds == 7.0
    assert five.median_gap_seconds == 6.0
