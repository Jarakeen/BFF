import json
import sqlite3

from services.rotation_healer_minor_lifesteal_esologs_evidence_service import (
    RotationHealerMinorLifestealEsoLogsEvidenceService,
)


def _database(tmp_path):
    path = tmp_path / "logs.db"
    with sqlite3.connect(path) as db:
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT NOT NULL,
                fight_id INTEGER NOT NULL,
                event_index INTEGER NOT NULL,
                timestamp REAL NOT NULL,
                event_type TEXT NOT NULL,
                source_id INTEGER,
                source_is_friendly INTEGER,
                target_id INTEGER,
                target_instance INTEGER,
                target_is_friendly INTEGER,
                ability_game_id INTEGER,
                extra_ability_game_id INTEGER,
                amount REAL,
                hit_type INTEGER,
                tick INTEGER,
                cast_track_id INTEGER,
                resource_change REAL,
                resource_change_type INTEGER,
                other_resource_change REAL,
                max_resource_amount REAL,
                waste REAL,
                overheal REAL,
                absorbed REAL,
                stack INTEGER,
                raw_json TEXT NOT NULL
            )
            """
        )
        rows = [
            (0, 1000.0, "damage", 7, 99, 7001, 100.0, "Light Attack"),
            (1, 1001.0, "heal", 7, 7, 9001, 600.0, "Minor Lifesteal"),
            (2, 1500.0, "damage", 8, 99, 7002, 200.0, "Skill"),
            (3, 1501.0, "heal", 8, 9, 9001, 600.0, "Minor Lifesteal"),
            (4, 2000.0, "damage", 7, 99, 7003, 300.0, "Skill"),
            (5, 2002.0, "heal", 7, 7, 9001, 600.0, "Minor Lifesteal"),
            (6, 2100.0, "heal", 7, 7, 9999, 1000.0, "Other Heal"),
        ]
        for index, timestamp, kind, source, target, ability_id, amount, name in rows:
            raw = {
                "timestamp": timestamp,
                "type": kind,
                "sourceID": source,
                "targetID": target,
                "abilityGameID": ability_id,
                "ability": {"name": name},
                "amount": amount,
            }
            db.execute(
                """
                INSERT INTO log_event (
                    report_code, fight_id, event_index, timestamp, event_type,
                    source_id, source_is_friendly, target_id, target_instance,
                    target_is_friendly, ability_game_id, extra_ability_game_id,
                    amount, hit_type, tick, cast_track_id, resource_change,
                    resource_change_type, other_resource_change,
                    max_resource_amount, waste, overheal, absorbed, stack, raw_json
                )
                VALUES (
                    'ABC', 4, ?, ?, ?, ?, 1, ?, NULL, 1, ?, NULL, ?, NULL,
                    0, NULL, NULL, NULL, NULL, NULL, NULL, 0, NULL, NULL, ?
                )
                """,
                (
                    index,
                    timestamp,
                    kind,
                    source,
                    target,
                    ability_id,
                    amount,
                    json.dumps(raw),
                ),
            )
    return path


def test_discovers_named_minor_lifesteal_heals_and_preserves_observed_alias(tmp_path):
    report = RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(
        _database(tmp_path)
    )

    assert report.evidence_status == "candidate"
    assert report.observed_heal_ability_aliases == (9001,)
    assert len(report.observations) == 3
    assert [item.event_index for item in report.observations] == [1, 3, 5]
    assert [item.source_target_relation for item in report.observations] == [
        "self",
        "other",
        "self",
    ]
    assert report.unresolved == ()


def test_records_nearest_preceding_same_source_damage_without_calling_it_a_rule(tmp_path):
    report = RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(
        _database(tmp_path)
    )

    first, second, third = report.observations
    assert first.previous_same_source_damage_event_index == 0
    assert first.previous_same_source_damage_target_id == 99
    assert first.previous_same_source_damage_delta_seconds == 0.001
    assert second.previous_same_source_damage_event_index == 2
    assert second.previous_same_source_damage_delta_seconds == 0.001
    assert third.previous_same_source_damage_event_index == 4
    assert third.previous_same_source_damage_delta_seconds == 0.002


def test_reports_per_actor_observed_intervals_without_promoting_cooldown(tmp_path):
    report = RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(
        _database(tmp_path)
    )

    stream = next(
        item
        for item in report.cadence_streams
        if item.source_id == 7 and item.target_id == 7
    )
    assert stream.heal_event_count == 2
    assert stream.observed_intervals_seconds == (1.001,)


def test_caller_supplied_numeric_alias_is_observational_fallback_only(tmp_path):
    path = _database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute(
            """
            UPDATE log_event
            SET raw_json = '{}'
            WHERE event_index = 1
            """
        )

    without_alias = RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(
        path
    )
    with_alias = RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(
        path,
        observed_heal_ability_ids=(9001,),
    )

    assert [item.event_index for item in without_alias.observations] == [3, 5]
    assert [item.event_index for item in with_alias.observations] == [1, 3, 5]
    assert with_alias.to_candidate_fixture_payload()["effect_id"] == "minor_lifesteal"
    assert with_alias.to_candidate_fixture_payload()["evidence_status"] == "candidate"


def test_missing_log_event_table_fails_closed(tmp_path):
    path = tmp_path / "empty.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE something_else(id INTEGER)")

    report = RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(path)

    assert report.observations == ()
    assert report.cadence_streams == ()
    assert report.unresolved == ("log_event table is unavailable",)


def test_incomplete_log_event_schema_fails_closed(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE log_event(report_code TEXT, fight_id INTEGER)"
        )

    report = RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(path)

    assert report.observations == ()
    assert report.cadence_streams == ()
    assert report.unresolved[0].startswith(
        "log_event schema is missing required columns:"
    )
    assert "raw_json" in report.unresolved[0]


def test_inspection_does_not_mutate_database(tmp_path):
    path = _database(tmp_path)
    before = path.read_bytes()

    RotationHealerMinorLifestealEsoLogsEvidenceService().inspect(path)

    assert path.read_bytes() == before
