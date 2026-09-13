import hashlib
import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_candidate_lifetime_topology_service import (
    RotationDDPeriodicEsoLogsCandidateLifetimeTopologyService,
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
                target_id INTEGER, ability_game_id INTEGER,
                cast_track_id INTEGER, raw_json TEXT
            )
            """
        )
        db.commit()


def _event(
    path,
    *,
    index,
    timestamp,
    event_type,
    source_id,
    target_id,
    ability_id,
    cast_track_id,
    name="",
):
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                "R",
                1,
                index,
                timestamp,
                event_type,
                source_id,
                target_id,
                ability_id,
                cast_track_id,
                json.dumps({"ability": {"name": name}}) if name else "{}",
            ),
        )
        db.commit()


def _service(canonical, logs):
    service = RotationDDPeriodicEsoLogsCandidateLifetimeTopologyService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    return service


def test_reports_source_track_target_and_lifetime_bands(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(
        logs,
        index=1,
        timestamp=1000,
        event_type="cast",
        source_id=42,
        target_id=99,
        ability_id=500,
        cast_track_id=77,
        name="Detonating Siphon",
    )
    _event(logs, index=2, timestamp=1020, event_type="damage", source_id=42, target_id=99, ability_id=118766, cast_track_id=77)
    _event(logs, index=3, timestamp=3500, event_type="damage", source_id=42, target_id=99, ability_id=118766, cast_track_id=88)
    _event(logs, index=4, timestamp=12000, event_type="damage", source_id=7, target_id=100, ability_id=118766, cast_track_id=None)
    _event(logs, index=5, timestamp=3300, event_type="damage", source_id=42, target_id=99, ability_id=123082, cast_track_id=77)
    _event(logs, index=6, timestamp=22000, event_type="damage", source_id=42, target_id=99, ability_id=118766, cast_track_id=77)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766, 123082),
        active_window_seconds=20.0,
    )

    assert report.cast_count == 1
    assert report.observation_count == 4
    assert report.unique_event_count == 4
    assert report.overlapping_window_reuse_count == 0
    assert report.censored_same_source_observation_count == 3
    assert report.censored_same_source_unique_event_count == 3
    assert report.unresolved == ()

    groups = {
        (item.candidate_ability_id, item.time_band, item.source_relation, item.track_relation): item
        for item in report.groups
    }
    early = groups[(118766, "0-2s", "same_source", "same_track")]
    assert early.observation_count == 1
    assert early.cast_window_count == 1
    assert early.distinct_source_count == 1
    assert early.distinct_target_count == 1
    assert early.distinct_track_count == 1
    assert early.latest_offset_seconds == 0.02

    middle = groups[(118766, "2-5s", "same_source", "other_track")]
    assert middle.latest_offset_seconds == 2.5

    late = groups[(118766, "10s+", "other_source", "missing_track")]
    assert late.latest_offset_seconds == 11.0
    assert late.distinct_target_count == 1

    delayed = groups[(123082, "2-5s", "same_source", "same_track")]
    assert delayed.latest_offset_seconds == 2.3

    censored = {
        (item.candidate_ability_id, item.time_band, item.track_relation): item
        for item in report.censored_same_source_groups
    }
    assert censored[(118766, "0-2s", "same_track")].latest_offset_seconds == 0.02
    assert censored[(118766, "2-5s", "other_track")].latest_offset_seconds == 2.5
    assert censored[(123082, "2-5s", "same_track")].latest_offset_seconds == 2.3
    assert all(item.source_relation == "same_source" for item in report.censored_same_source_groups)


def test_censored_same_source_view_stops_at_next_recast_and_does_not_reuse_event(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, target_id=99, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=5000, event_type="cast", source_id=42, target_id=99, ability_id=500, cast_track_id=78, name="Detonating Siphon")
    _event(logs, index=3, timestamp=6000, event_type="damage", source_id=42, target_id=99, ability_id=118766, cast_track_id=78)
    _event(logs, index=4, timestamp=7000, event_type="damage", source_id=7, target_id=99, ability_id=118766, cast_track_id=91)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766,),
        active_window_seconds=20.0,
    )

    assert report.cast_count == 2
    assert report.observation_count == 4
    assert report.unique_event_count == 2
    assert report.overlapping_window_reuse_count == 2
    assert report.censored_same_source_observation_count == 1
    assert report.censored_same_source_unique_event_count == 1

    censored = report.censored_same_source_groups
    assert len(censored) == 1
    assert censored[0].time_band == "0-2s"
    assert censored[0].source_relation == "same_source"
    assert censored[0].track_relation == "same_track"
    assert censored[0].observation_count == 1
    assert censored[0].latest_offset_seconds == 1.0


def test_reports_overlapping_window_reuse_and_does_not_mutate_logs(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, target_id=99, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=5000, event_type="cast", source_id=42, target_id=99, ability_id=500, cast_track_id=78, name="Detonating Siphon")
    _event(logs, index=3, timestamp=6000, event_type="damage", source_id=42, target_id=99, ability_id=118766, cast_track_id=None)

    before = hashlib.sha256(logs.read_bytes()).hexdigest()
    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766,),
        active_window_seconds=20.0,
    )
    after = hashlib.sha256(logs.read_bytes()).hexdigest()

    assert report.cast_count == 2
    assert report.observation_count == 2
    assert report.unique_event_count == 1
    assert report.overlapping_window_reuse_count == 1
    assert report.censored_same_source_observation_count == 1
    assert report.censored_same_source_unique_event_count == 1
    assert before == after
