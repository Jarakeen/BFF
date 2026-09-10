import json
import sqlite3

import pytest

from services.rotation_healer_esologs_observation_extractor import (
    RotationHealerEsoLogsObservationExtractor,
    RotationHealerEsoLogsObservationTarget,
    RotationHealerEsoLogsTimestampUnit,
)


def _database(tmp_path):
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
            "INSERT INTO skill(id, base_ability_id, name) VALUES (1, 93807, 'Budding Seeds')"
        )
        db.execute(
            """
            INSERT INTO skill_rank(id, skill_id, ability_id, raw_name, rank, morph)
            VALUES (6910, 1, 93807, 'Budding Seeds', 4, 1)
            """
        )
        db.execute(
            "INSERT INTO ability(ability_id, name, coef_description, duration) VALUES (?, ?, ?, ?)",
            (
                93807,
                "Budding Seeds",
                "Summon a field which blooms after 6 seconds, healing for $1 Health. "
                "While the field grows, you and allies are healed for $2 Health every 1 second.",
                6000,
            ),
        )
        db.execute(
            """
            INSERT INTO skill_coefficient(
                skill_rank_id, coefficient_number, type, a, b, c, r, avg
            ) VALUES (6910, 2, '8', 0.1, 1.0, 0.0, 1.0, NULL)
            """
        )
    return path


def _event(timestamp, event_type, *, source=7, target=20, ability=93807, tick=None, cast_track=None):
    event = {
        "timestamp": timestamp,
        "type": event_type,
        "sourceID": source,
        "targetID": target,
        "sourceIsFriendly": True,
        "targetIsFriendly": True,
        "abilityGameID": ability,
        "ability": {"name": "Budding Seeds"},
    }
    if tick is not None:
        event["tick"] = tick
    if cast_track is not None:
        event["castTrackID"] = cast_track
    return event


def _raw(tmp_path, events):
    path = tmp_path / "raw.json"
    payload = {
        "report_code": "ABC123",
        "fights": {
            "4": {
                "metadata": {"id": 4, "name": "Test Fight"},
                "events": events,
                "event_count": len(events),
            }
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _corpus(tmp_path, events):
    path = tmp_path / "corpus.json"
    payload = {
        "schema_version": 1,
        "encounter": "lokkestiiz",
        "reports": {
            "ABC123": {
                "matching_fight_count": 1,
                "fights": {
                    "4": {
                        "metadata": {"id": 4, "name": "Lokkestiiz"},
                        "events": events,
                        "event_count": len(events),
                    }
                },
            },
            "OTHER": {"matching_fight_count": 0, "fights": {}},
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _target():
    return (
        RotationHealerEsoLogsObservationTarget(
            source_name="Budding Seeds",
            coefficient_number=2,
            ability_game_id=93807,
        ),
    )


def test_extracts_isolated_periodic_sample_and_deduplicates_recipient_events(tmp_path):
    events = [_event(10000, "cast", cast_track=10)]
    for timestamp in (11000, 12000, 13000, 14000, 15000, 16000):
        events.append(_event(timestamp, "hot", target=21, tick=True))
        events.append(_event(timestamp, "hot", target=22, tick=True))
    events.append(_event(16020, "damage", source=99, target=99, ability=1))

    report = RotationHealerEsoLogsObservationExtractor(_database(tmp_path)).extract(
        _raw(tmp_path, events),
        fight_id=4,
        caster_id=7,
        targets=_target(),
    )

    assert report.unresolved == ()
    assert len(report.candidates) == 1
    candidate = report.candidates[0]
    assert candidate.sample.activation_time_seconds == 10.0
    assert candidate.sample.observed_tick_times_seconds == (11.0, 12.0, 13.0, 14.0, 15.0, 16.0)
    assert candidate.raw_periodic_heal_event_count == 12
    assert candidate.sample.observation_end_seconds == 16.02


def test_candidate_payload_is_explicitly_not_reviewed(tmp_path):
    events = [_event(10000, "cast")]
    events.extend(_event(value, "hot", tick=True) for value in (11000, 12000, 13000, 14000, 15000, 16000))
    events.append(_event(16020, "damage", source=99, target=99, ability=1))

    report = RotationHealerEsoLogsObservationExtractor(_database(tmp_path)).extract(
        _raw(tmp_path, events),
        fight_id=4,
        caster_id=7,
        targets=_target(),
    )
    payload = report.to_candidate_fixture_payload(game_version="U50")

    assert payload["review_status"] == "candidate"
    assert payload["source"]["report_code"] == "ABC123"
    assert payload["samples"][0]["candidate_metadata"]["ability_game_id"] == 93807


def test_recast_before_expiry_rejects_both_overlapping_activations(tmp_path):
    events = [
        _event(10000, "cast", cast_track=10),
        _event(11000, "hot", tick=True),
        _event(12000, "hot", tick=True),
        _event(13000, "cast", cast_track=11),
    ]
    events.extend(_event(value, "hot", tick=True) for value in (14000, 15000, 16000, 17000, 18000, 19000))
    events.append(_event(19020, "damage", source=99, target=99, ability=1))

    report = RotationHealerEsoLogsObservationExtractor(_database(tmp_path)).extract(
        _raw(tmp_path, events),
        fight_id=4,
        caster_id=7,
        targets=_target(),
    )

    assert report.candidates == ()
    assert any(
        "skipped because another activation occurs before canonical expiry" in item
        for item in report.unresolved
    )
    assert any(
        "skipped because a previous activation remains active at this activation" in item
        for item in report.unresolved
    )


def test_wrong_caster_does_not_borrow_another_players_ticks(tmp_path):
    events = [_event(10000, "cast", source=8)]
    events.extend(_event(value, "hot", source=8, tick=True) for value in (11000, 12000, 13000, 14000, 15000, 16000))

    report = RotationHealerEsoLogsObservationExtractor(_database(tmp_path)).extract(
        _raw(tmp_path, events),
        fight_id=4,
        caster_id=7,
        targets=_target(),
    )

    assert report.candidates == ()
    assert any("no matching cast/completecast event for caster 7" in item for item in report.unresolved)


def test_seconds_timestamp_unit_does_not_divide_again(tmp_path):
    events = [_event(10.0, "cast")]
    events.extend(_event(value, "hot", tick=True) for value in (11.0, 12.0, 13.0, 14.0, 15.0, 16.0))
    events.append(_event(16.02, "damage", source=99, target=99, ability=1))

    report = RotationHealerEsoLogsObservationExtractor(_database(tmp_path)).extract(
        _raw(tmp_path, events),
        fight_id=4,
        caster_id=7,
        targets=_target(),
        timestamp_unit=RotationHealerEsoLogsTimestampUnit.SECONDS,
    )

    assert report.candidates[0].sample.activation_time_seconds == 10.0
    assert report.candidates[0].sample.observed_tick_times_seconds[0] == 11.0


def test_extracts_from_multi_report_corpus_when_report_code_is_explicit(tmp_path):
    events = [_event(10000, "cast")]
    events.extend(_event(value, "hot", tick=True) for value in (11000, 12000, 13000, 14000, 15000, 16000))
    events.append(_event(16020, "damage", source=99, target=99, ability=1))

    report = RotationHealerEsoLogsObservationExtractor(_database(tmp_path)).extract(
        _corpus(tmp_path, events),
        report_code="ABC123",
        fight_id=4,
        caster_id=7,
        targets=_target(),
    )

    assert report.report_code == "ABC123"
    assert report.fight_id == 4
    assert len(report.candidates) == 1


def test_multi_report_corpus_requires_explicit_report_code(tmp_path):
    with pytest.raises(ValueError, match="requires report_code"):
        RotationHealerEsoLogsObservationExtractor.load_fight(
            _corpus(tmp_path, []),
            fight_id=4,
        )


def test_multi_report_corpus_rejects_unknown_report_code(tmp_path):
    with pytest.raises(ValueError, match="is not present in corpus"):
        RotationHealerEsoLogsObservationExtractor.load_fight(
            _corpus(tmp_path, []),
            fight_id=4,
            report_code="MISSING",
        )
