import json
import sqlite3
from types import SimpleNamespace

from services.rotation_dd_periodic_esologs_runtime_evidence_service import (
    RotationDDPeriodicEsoLogsRuntimeEvidenceService,
)


class _Coefficients:
    def resolve_entity_id(self, entity_id):
        assert entity_id == "stampede"
        return SimpleNamespace(
            rank=SimpleNamespace(
                skill_id=7,
                morph=1,
                base_ability_id=100,
            ),
            unresolved=(),
        )


class _Review:
    def by_component(self):
        return {
            ("stampede", 2): SimpleNamespace(duration_seconds=15.0),
        }


def _create_database(path, *, with_log_event=True):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE skill_rank (
                id INTEGER PRIMARY KEY,
                skill_id INTEGER NOT NULL,
                ability_id INTEGER NOT NULL,
                rank INTEGER,
                morph INTEGER
            )
            """
        )
        db.execute(
            "INSERT INTO skill_rank (id, skill_id, ability_id, rank, morph) VALUES (1, 7, 200, 4, 1)"
        )
        if with_log_event:
            db.execute(
                """
                CREATE TABLE log_event (
                    report_code TEXT NOT NULL,
                    fight_id INTEGER NOT NULL,
                    event_index INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    source_id INTEGER,
                    target_id INTEGER,
                    ability_game_id INTEGER,
                    amount REAL,
                    tick INTEGER,
                    cast_track_id INTEGER,
                    raw_json TEXT NOT NULL
                )
                """
            )
        db.commit()


def _insert_event(
    path,
    *,
    index,
    timestamp,
    event_type,
    ability_id=200,
    ability_name="Stampede",
    tick=None,
    amount=None,
    target_id=99,
    source_id=42,
    report_code="REPORT",
    fight_id=3,
):
    raw = {} if ability_name is None else {"ability": {"name": ability_name}}
    with sqlite3.connect(path) as db:
        db.execute(
            """
            INSERT INTO log_event (
                report_code, fight_id, event_index, timestamp, event_type,
                source_id, target_id, ability_game_id, amount, tick,
                cast_track_id, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_code,
                fight_id,
                index,
                timestamp,
                event_type,
                source_id,
                target_id,
                ability_id,
                amount,
                tick,
                index,
                json.dumps(raw),
            ),
        )
        db.commit()


def _service(path):
    return RotationDDPeriodicEsoLogsRuntimeEvidenceService(
        path,
        coefficient_repository=_Coefficients(),
        review_service=_Review(),
    )


def test_isolated_cast_reports_observed_first_tick_and_intervals(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _create_database(path)
    _insert_event(path, index=1, timestamp=1000, event_type="cast", tick=0)
    _insert_event(path, index=2, timestamp=2000, event_type="damage", tick=1, amount=100)
    _insert_event(path, index=3, timestamp=3000, event_type="damage", tick=1, amount=105)
    _insert_event(path, index=4, timestamp=4000, event_type="damage", tick=1, amount=110)

    report = _service(path).inspect_skill("Stampede")

    assert report.skill_entity_id == "stampede"
    assert report.unresolved == ()
    assert report.observed_ability_ids == (100, 200)
    assert len(report.casts) == 1
    cast = report.casts[0]
    assert cast.first_tick_offset_seconds == 1.0
    assert cast.tick_intervals_seconds == (1.0, 1.0)
    assert cast.isolated_from_recast is True
    assert cast.exact_recast_boundary_event_count == 0
    assert cast.unresolved == ()
    assert tuple(event.amount for event in cast.periodic_events) == (100.0, 105.0, 110.0)


def test_translated_raw_name_wins_over_matching_numeric_alias(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _create_database(path)
    _insert_event(path, index=1, timestamp=1000, event_type="cast", tick=0)
    _insert_event(path, index=2, timestamp=2000, event_type="damage", tick=1, amount=100)
    _insert_event(
        path,
        index=3,
        timestamp=2500,
        event_type="damage",
        ability_name="Completely Different Skill",
        ability_id=200,
        tick=1,
        amount=999,
    )
    _insert_event(
        path,
        index=4,
        timestamp=3000,
        event_type="damage",
        ability_name=None,
        ability_id=200,
        tick=1,
        amount=110,
    )

    report = _service(path).inspect_skill("stampede")

    cast = report.casts[0]
    assert tuple(event.timestamp_ms for event in cast.periodic_events) == (2000.0, 3000.0)
    assert tuple(event.amount for event in cast.periodic_events) == (100.0, 110.0)


def test_recast_overlap_is_reported_without_promoting_refresh_semantics(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _create_database(path)
    _insert_event(path, index=1, timestamp=1000, event_type="cast", tick=0)
    _insert_event(path, index=2, timestamp=2000, event_type="damage", tick=1, amount=100)
    _insert_event(path, index=3, timestamp=5000, event_type="damage", tick=1, amount=100)
    _insert_event(path, index=4, timestamp=5000, event_type="cast", tick=0)
    _insert_event(path, index=5, timestamp=6000, event_type="damage", tick=1, amount=100)

    report = _service(path).inspect_skill("stampede")

    assert len(report.casts) == 2
    first = report.casts[0]
    assert first.isolated_from_recast is False
    assert first.exact_recast_boundary_event_count == 1
    assert any("recast overlaps" in message for message in first.unresolved)


def test_missing_log_event_table_fails_closed(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _create_database(path, with_log_event=False)

    report = _service(path).inspect_skill("stampede")

    assert report.casts == ()
    assert "log_event table is unavailable" in report.unresolved
