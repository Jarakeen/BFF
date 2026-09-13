import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_pet_source_discovery_service import (
    RotationDDPeriodicEsoLogsPetSourceDiscoveryService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "skeletal_archer"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=7, morph=1, base_ability_id=114317),
            unresolved=(),
        )


class _Review:
    def by_component(self):
        return {
            ("skeletal_archer", 1): SimpleNamespace(
                duration_seconds=20.0,
                reviewed_interval_seconds=2.0,
            )
        }


def _canonical(path):
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER, ability_id INTEGER, morph INTEGER)"
        )
        db.execute("INSERT INTO skill_rank VALUES (1, 7, 118680, 1)")
        db.commit()


def _logs(path):
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE log_actor (
                report_code TEXT,
                fight_id INTEGER,
                actor_id INTEGER,
                actor_type TEXT
            );
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
                event_index INTEGER,
                timestamp REAL,
                event_type TEXT,
                source_id INTEGER,
                source_is_friendly INTEGER,
                ability_game_id INTEGER,
                tick INTEGER,
                raw_json TEXT
            );
            """
        )
        db.execute("INSERT INTO log_actor VALUES ('REPORT', 3, 42, 'Necromancer')")
        db.execute("INSERT INTO log_actor VALUES ('REPORT', 3, 99, 'Templar')")
        db.commit()


def _event(
    path,
    *,
    index,
    timestamp,
    event_type,
    source_id,
    friendly,
    ability_id,
    name,
    tick=0,
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
                friendly,
                ability_id,
                tick,
                json.dumps({"ability": {"name": name}}),
            ),
        )
        db.commit()


def _service(canonical, logs):
    service = RotationDDPeriodicEsoLogsPetSourceDiscoveryService(
        canonical_database_path=canonical,
        logs_database_path=logs,
        review_service=_Review(),
    )
    service.coefficients = _Coefficients()
    return service


def test_discovers_friendly_nonplayer_pet_stream_and_excludes_players(tmp_path) -> None:
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
        friendly=1,
        ability_id=118680,
        name="Skeletal Archer",
    )
    for index, timestamp in enumerate((3000, 5000, 7000), start=2):
        _event(
            logs,
            index=index,
            timestamp=timestamp,
            event_type="damage",
            source_id=500,
            friendly=1,
            ability_id=900,
            name="Skeleton Arrow",
            tick=1,
        )
    for index, timestamp in enumerate((3000, 5000, 7000), start=10):
        _event(
            logs,
            index=index,
            timestamp=timestamp,
            event_type="damage",
            source_id=99,
            friendly=1,
            ability_id=900,
            name="Skeleton Arrow",
            tick=1,
        )
    _event(
        logs,
        index=20,
        timestamp=4000,
        event_type="damage",
        source_id=600,
        friendly=0,
        ability_id=901,
        name="Hostile Damage",
        tick=1,
    )

    report = _service(canonical, logs).inspect_skill("skeletal_archer")

    assert report.cast_count == 1
    assert report.reviewed_interval_seconds == 2.0
    assert report.candidates
    candidate = report.candidates[0]
    assert candidate.ability_game_id == 900
    assert candidate.event_count == 3
    assert candidate.source_actor_count == 1
    assert candidate.reviewed_interval_match_count == 2
    assert candidate.median_first_offset_seconds == 2.0
    assert candidate.interval_samples_seconds == (2.0, 2.0)
    assert any("not owner-linked" in item for item in report.unresolved)


def test_explicit_pet_actor_metadata_is_eligible(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)
    with sqlite3.connect(logs) as db:
        db.execute("INSERT INTO log_actor VALUES ('REPORT', 3, 501, 'Pet')")
        db.commit()

    _event(
        logs,
        index=1,
        timestamp=1000,
        event_type="cast",
        source_id=42,
        friendly=1,
        ability_id=118680,
        name="Skeletal Archer",
    )
    _event(
        logs,
        index=2,
        timestamp=3000,
        event_type="damage",
        source_id=501,
        friendly=1,
        ability_id=902,
        name="Pet Arrow",
        tick=1,
    )
    _event(
        logs,
        index=3,
        timestamp=5000,
        event_type="damage",
        source_id=501,
        friendly=1,
        ability_id=902,
        name="Pet Arrow",
        tick=1,
    )

    report = _service(canonical, logs).inspect_skill("skeletal_archer")

    assert report.candidates[0].ability_game_id == 902
    assert report.candidates[0].reviewed_interval_match_count == 1


def test_non_pet_skill_fails_closed_before_log_discovery(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    report = _service(canonical, logs).inspect_skill("stampede")

    assert report.candidates == ()
    assert any("reviewed runtime source is not pet-owned" in item for item in report.unresolved)
