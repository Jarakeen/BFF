import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_secondary_effect_discovery_service import (
    RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "stampede"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=7, morph=1, base_ability_id=100),
            unresolved=(),
        )


class _Review:
    def __init__(self, *, duration=15.0, interval=1.0):
        self.duration = duration
        self.interval = interval

    def by_component(self):
        return {
            ("stampede", 2): SimpleNamespace(
                duration_seconds=self.duration,
                reviewed_interval_seconds=self.interval,
            )
        }


def _canonical(path):
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER, ability_id INTEGER, morph INTEGER)"
        )
        db.execute("INSERT INTO skill_rank VALUES (1, 7, 200, 1)")
        db.commit()


def _logs(path):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT, fight_id INTEGER, event_index INTEGER,
                timestamp REAL, event_type TEXT, source_id INTEGER,
                ability_game_id INTEGER, tick INTEGER, cast_track_id INTEGER,
                raw_json TEXT
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
    name,
    ability_id,
    source_id=42,
    tick=0,
    cast_track_id=None,
):
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                "REPORT",
                3,
                index,
                timestamp,
                event_type,
                source_id,
                ability_id,
                tick,
                cast_track_id,
                json.dumps({"ability": {"name": name}}),
            ),
        )
        db.commit()


def _service(canonical, logs, *, review=None):
    service = RotationDDPeriodicEsoLogsSecondaryEffectDiscoveryService(
        canonical_database_path=canonical,
        logs_database_path=logs,
        review_service=review or _Review(),
    )
    service.coefficients = _Coefficients()
    return service


def test_discovers_secondary_damage_identity_and_ranks_reviewed_cadence(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", name="Stampede", ability_id=200, cast_track_id=77)
    _event(logs, index=2, timestamp=2000, event_type="damage", name="Stampede Ground Damage", ability_id=900, tick=0)
    _event(logs, index=3, timestamp=3000, event_type="damage", name="Stampede Ground Damage", ability_id=900, tick=0)
    _event(logs, index=4, timestamp=4000, event_type="damage", name="Stampede Ground Damage", ability_id=900, tick=0)
    _event(logs, index=5, timestamp=2500, event_type="damage", name="Other Dot", ability_id=901, tick=1)
    _event(logs, index=6, timestamp=4500, event_type="damage", name="Other Dot", ability_id=901, tick=1)

    report = _service(canonical, logs).inspect_skill("Stampede")

    assert report.cast_count == 1
    assert report.reviewed_duration_seconds == 15.0
    assert report.reviewed_interval_seconds == 1.0
    assert report.unresolved == ()
    assert report.candidates
    top = report.candidates[0]
    assert top.ability_entity_id == "stampede_ground_damage"
    assert top.ability_game_ids == (900,)
    assert top.cast_windows_observed == 1
    assert top.occurrence_count == 3
    assert top.reviewed_interval_match_count == 2
    assert top.median_first_offset_seconds == 1.0
    assert top.interval_samples_seconds == (1.0, 1.0)


def test_cast_track_linked_secondary_identity_ranks_above_unlinked_candidates(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", name="Stampede", ability_id=200, cast_track_id=77)
    _event(logs, index=2, timestamp=2000, event_type="damage", name="Linked Effect", ability_id=910, cast_track_id=77)
    _event(logs, index=3, timestamp=5000, event_type="damage", name="Unlinked Regular Dot", ability_id=911)
    _event(logs, index=4, timestamp=6000, event_type="damage", name="Unlinked Regular Dot", ability_id=911)
    _event(logs, index=5, timestamp=7000, event_type="damage", name="Unlinked Regular Dot", ability_id=911)

    report = _service(canonical, logs).inspect_skill("stampede")

    assert report.candidates[0].ability_entity_id == "linked_effect"
    assert report.candidates[0].cast_track_linked_event_count == 1


def test_translated_cast_name_wins_over_numeric_alias(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", name="Different Skill", ability_id=200)
    _event(logs, index=2, timestamp=2000, event_type="damage", name="Candidate", ability_id=900)
    _event(logs, index=3, timestamp=3000, event_type="damage", name="Candidate", ability_id=900)

    report = _service(canonical, logs).inspect_skill("stampede")

    assert report.cast_count == 0
    assert report.candidates == ()
    assert any("no matching ESO Logs cast observations" in message for message in report.unresolved)


def test_missing_reviewed_duration_fails_closed(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    report = _service(canonical, logs, review=_Review(duration=None)).inspect_skill("stampede")

    assert report.cast_count == 0
    assert report.candidates == ()
    assert any("reviewed duration is required" in message for message in report.unresolved)
