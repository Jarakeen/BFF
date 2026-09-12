import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_cast_track_topology_service import (
    RotationDDPeriodicEsoLogsCastTrackTopologyService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "unnerving_boneyard"
        return SimpleNamespace(
            rank=SimpleNamespace(skill_id=9, morph=1, base_ability_id=600),
            unresolved=(),
        )


def _canonical(path):
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE skill_rank (id INTEGER PRIMARY KEY, skill_id INTEGER, ability_id INTEGER, morph INTEGER)"
        )
        db.execute("INSERT INTO skill_rank VALUES (1,9,600,1)")
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


def _event(path, *, index, timestamp, event_type, ability_id, name, cast_track_id, source_id=42):
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?,?)",
            (
                "R", 1, index, timestamp, event_type, source_id,
                ability_id, cast_track_id,
                json.dumps({"ability": {"name": name}}),
            ),
        )
        db.commit()


def _service(canonical, logs):
    service = RotationDDPeriodicEsoLogsCastTrackTopologyService(
        canonical_database_path=canonical,
        logs_database_path=logs,
    )
    service.coefficients = _Coefficients()
    return service


def test_reports_same_track_component_order_and_first_offsets(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", ability_id=600, name="Unnerving Boneyard", cast_track_id=77)
    _event(logs, index=2, timestamp=1300, event_type="applydebuff", ability_id=700, name="Boneyard Placement", cast_track_id=77)
    _event(logs, index=3, timestamp=1360, event_type="damage", ability_id=117809, name="Boneyard Damage", cast_track_id=77)
    _event(logs, index=4, timestamp=2360, event_type="damage", ability_id=117809, name="Boneyard Damage", cast_track_id=77)

    _event(logs, index=5, timestamp=5000, event_type="cast", ability_id=600, name="Unnerving Boneyard", cast_track_id=88)
    _event(logs, index=6, timestamp=5320, event_type="applydebuff", ability_id=700, name="Boneyard Placement", cast_track_id=88)
    _event(logs, index=7, timestamp=5380, event_type="damage", ability_id=117809, name="Boneyard Damage", cast_track_id=88)

    report = _service(canonical, logs).inspect(
        "unnerving_boneyard",
        active_window_seconds=10.0,
    )

    assert report.cast_count == 2
    assert report.unresolved == ()
    assert len(report.components) == 2

    placement, damage = report.components
    assert placement.ability_game_id == 700
    assert placement.event_type == "applydebuff"
    assert placement.cast_track_count == 2
    assert placement.event_count == 2
    assert placement.first_offsets_seconds == (0.3, 0.32)

    assert damage.ability_game_id == 117809
    assert damage.event_type == "damage"
    assert damage.cast_track_count == 2
    assert damage.event_count == 3
    assert damage.first_offsets_seconds == (0.36, 0.38)


def test_different_track_and_source_are_excluded(tmp_path) -> None:
    canonical = tmp_path / "eso.db"
    logs = tmp_path / "logs.db"
    _canonical(canonical)
    _logs(logs)

    _event(logs, index=1, timestamp=1000, event_type="cast", ability_id=600, name="Unnerving Boneyard", cast_track_id=77)
    _event(logs, index=2, timestamp=1300, event_type="damage", ability_id=117809, name="Wrong Track", cast_track_id=88)
    _event(logs, index=3, timestamp=1310, event_type="damage", ability_id=117809, name="Wrong Source", cast_track_id=77, source_id=43)

    report = _service(canonical, logs).inspect(
        "unnerving_boneyard",
        active_window_seconds=10.0,
    )

    assert report.components == ()
    assert any("no exact same-cast-track component events" in message for message in report.unresolved)
