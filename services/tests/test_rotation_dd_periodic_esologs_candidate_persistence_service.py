import hashlib
import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_candidate_persistence_service import (
    RotationDDPeriodicEsoLogsCandidatePersistenceService,
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
    service = RotationDDPeriodicEsoLogsCandidatePersistenceService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    return service


def test_reports_last_observation_thresholds_per_censored_same_track_cast(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=1100, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=3, timestamp=6200, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=4, timestamp=12000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)

    _event(logs, index=5, timestamp=22000, event_type="cast", source_id=42, ability_id=500, cast_track_id=78, name="Detonating Siphon")
    _event(logs, index=6, timestamp=22100, event_type="damage", source_id=42, ability_id=118766, cast_track_id=78)
    _event(logs, index=7, timestamp=41100, event_type="damage", source_id=42, ability_id=118766, cast_track_id=78)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766, 123082),
        active_window_seconds=20.0,
    )

    assert report.cast_count == 2
    siphon = next(item for item in report.summaries if item.candidate_ability_id == 118766)
    assert siphon.linked_cast_count == 2
    assert siphon.minimum_last_offset_seconds == 11.0
    assert siphon.median_last_offset_seconds == 15.05
    assert siphon.maximum_last_offset_seconds == 19.1
    assert siphon.observed_at_or_after_2s == 2
    assert siphon.observed_at_or_after_5s == 2
    assert siphon.observed_at_or_after_10s == 2
    assert siphon.observed_at_or_after_15s == 1
    assert siphon.observed_at_or_after_19s == 1
    assert siphon.eligible_at_or_after_2s == 2
    assert siphon.eligible_at_or_after_5s == 2
    assert siphon.eligible_at_or_after_10s == 2
    assert siphon.eligible_at_or_after_15s == 2
    assert siphon.eligible_at_or_after_19s == 2

    delayed = next(item for item in report.summaries if item.candidate_ability_id == 123082)
    assert delayed.linked_cast_count == 0
    assert delayed.eligible_at_or_after_2s == 0
    assert delayed.eligible_at_or_after_19s == 0


def test_recast_censors_threshold_eligibility_and_other_tracks_do_not_count(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=2000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=3, timestamp=5000, event_type="cast", source_id=42, ability_id=500, cast_track_id=78, name="Detonating Siphon")
    _event(logs, index=4, timestamp=6000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=5, timestamp=6500, event_type="damage", source_id=42, ability_id=118766, cast_track_id=99)
    _event(logs, index=6, timestamp=7000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=78)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766,),
        active_window_seconds=20.0,
    )

    summary = report.summaries[0]
    assert summary.linked_cast_count == 2
    assert summary.minimum_last_offset_seconds == 1.0
    assert summary.maximum_last_offset_seconds == 2.0
    assert summary.observed_at_or_after_2s == 1
    assert summary.eligible_at_or_after_2s == 2
    assert summary.observed_at_or_after_5s == 0
    assert summary.eligible_at_or_after_5s == 0


def test_fight_end_censors_threshold_eligibility(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=1100, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=3, timestamp=4000, event_type="damage", source_id=7, ability_id=999999, cast_track_id=None)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766,),
        active_window_seconds=20.0,
    )

    summary = report.summaries[0]
    assert summary.linked_cast_count == 1
    assert summary.maximum_last_offset_seconds == 0.1
    assert summary.eligible_at_or_after_2s == 1
    assert summary.eligible_at_or_after_5s == 0
    assert summary.observed_at_or_after_2s == 0
    assert summary.observed_at_or_after_5s == 0


def test_candidate_absent_casts_do_not_enter_persistence_eligibility_cohort(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=2000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)
    _event(logs, index=3, timestamp=25000, event_type="cast", source_id=42, ability_id=500, cast_track_id=78, name="Detonating Siphon")
    _event(logs, index=4, timestamp=46000, event_type="damage", source_id=7, ability_id=999999, cast_track_id=None)

    report = _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766,),
        active_window_seconds=20.0,
    )

    summary = report.summaries[0]
    assert summary.linked_cast_count == 1
    assert summary.eligible_at_or_after_2s == 1
    assert summary.eligible_at_or_after_19s == 1


def test_read_only_audit_does_not_mutate_logs(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)
    _event(logs, index=1, timestamp=1000, event_type="cast", source_id=42, ability_id=500, cast_track_id=77, name="Detonating Siphon")
    _event(logs, index=2, timestamp=2000, event_type="damage", source_id=42, ability_id=118766, cast_track_id=77)

    before = hashlib.sha256(logs.read_bytes()).hexdigest()
    _service(canonical, logs).inspect(
        "detonating_siphon",
        candidate_ability_ids=(118766,),
        active_window_seconds=20.0,
    )
    after = hashlib.sha256(logs.read_bytes()).hexdigest()

    assert before == after
