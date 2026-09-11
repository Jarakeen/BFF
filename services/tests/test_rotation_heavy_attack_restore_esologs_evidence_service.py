import json
import sqlite3

import pytest

from services.rotation_heavy_attack_restore_esologs_evidence_service import (
    RotationHeavyAttackRestoreEsoLogsEvidenceService,
)


def _database(tmp_path):
    path = tmp_path / "esologs.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript(
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
            );
            """
        )
    return path


def _insert(
    path,
    *,
    event_index,
    ability_id,
    ability_name,
    resource_change,
    source_id=42,
    resource_type=1,
    event_type="resourcechange",
    waste=0.0,
    report_code="REPORT",
    fight_id=7,
):
    with sqlite3.connect(path) as db:
        db.execute(
            """
            INSERT INTO log_event (
                report_code, fight_id, event_index, timestamp, event_type,
                source_id, source_is_friendly, target_id, target_instance,
                target_is_friendly, ability_game_id, extra_ability_game_id,
                amount, hit_type, tick, cast_track_id, resource_change,
                resource_change_type, other_resource_change, max_resource_amount,
                waste, overheal, absorbed, stack, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_code, fight_id, event_index, float(event_index), event_type,
                source_id, 1, source_id, 1, 1, ability_id, None,
                None, None, None, None, resource_change,
                resource_type, 0.0, 31109.0, waste, None, None, None,
                json.dumps({"ability": {"name": ability_name}}),
            ),
        )


def test_discovers_positive_restore_by_reviewed_name_alias(tmp_path):
    path = _database(tmp_path)
    _insert(
        path,
        event_index=1,
        ability_id=101,
        ability_name="Frost Staff Heavy Attack",
        resource_change=2823.0,
        resource_type=9,
        waste=17.0,
    )
    _insert(
        path,
        event_index=2,
        ability_id=202,
        ability_name="Natural Recovery",
        resource_change=400.0,
    )

    report = RotationHeavyAttackRestoreEsoLogsEvidenceService().discover(
        path,
        report_code="REPORT",
        fight_id=7,
        ability_names=("frost staff heavy attack",),
    )

    assert report.unresolved == ()
    assert len(report.observations) == 1
    row = report.observations[0]
    assert row.ability_game_id == 101
    assert row.ability_name == "Frost Staff Heavy Attack"
    assert row.resource_change == pytest.approx(2823.0)
    assert row.resource_change_type == 9
    assert row.waste == pytest.approx(17.0)
    assert row.max_resource_amount == pytest.approx(31109.0)


def test_numeric_alias_and_source_filter_are_explicit(tmp_path):
    path = _database(tmp_path)
    _insert(
        path,
        event_index=1,
        ability_id=777,
        ability_name="Unknown Localized Name",
        resource_change=3001.0,
        source_id=42,
    )
    _insert(
        path,
        event_index=2,
        ability_id=777,
        ability_name="Unknown Localized Name",
        resource_change=9999.0,
        source_id=99,
    )

    report = RotationHeavyAttackRestoreEsoLogsEvidenceService().discover(
        path,
        report_code="REPORT",
        fight_id=7,
        ability_game_ids=(777,),
        source_id=42,
    )

    assert [item.resource_change for item in report.observations] == [3001.0]


def test_nonpositive_or_unmatched_events_do_not_become_restore_evidence(tmp_path):
    path = _database(tmp_path)
    _insert(
        path,
        event_index=1,
        ability_id=101,
        ability_name="Frost Staff Heavy Attack",
        resource_change=0.0,
    )
    _insert(
        path,
        event_index=2,
        ability_id=202,
        ability_name="Something Else",
        resource_change=5000.0,
    )

    report = RotationHeavyAttackRestoreEsoLogsEvidenceService().discover(
        path,
        report_code="REPORT",
        fight_id=7,
        ability_names=("Frost Staff Heavy Attack",),
    )

    assert report.observations == ()
    assert "no positive resource-change events" in report.unresolved[0]


def test_requires_reviewed_alias_boundary(tmp_path):
    path = _database(tmp_path)

    with pytest.raises(ValueError, match="reviewed ability alias"):
        RotationHeavyAttackRestoreEsoLogsEvidenceService().discover(
            path,
            report_code="REPORT",
            fight_id=7,
        )


def test_corpus_discovery_preserves_report_fight_and_source_provenance(tmp_path):
    path = _database(tmp_path)
    _insert(
        path,
        report_code="REPORT_A",
        fight_id=1,
        event_index=1,
        ability_id=101,
        ability_name="Frost Staff Heavy Attack",
        resource_change=2823.0,
        source_id=42,
    )
    _insert(
        path,
        report_code="REPORT_B",
        fight_id=9,
        event_index=2,
        ability_id=101,
        ability_name="Frost Staff Heavy Attack",
        resource_change=2900.0,
        source_id=42,
    )
    _insert(
        path,
        report_code="REPORT_B",
        fight_id=10,
        event_index=3,
        ability_id=101,
        ability_name="Frost Staff Heavy Attack",
        resource_change=9999.0,
        source_id=99,
    )

    report = RotationHeavyAttackRestoreEsoLogsEvidenceService().discover_corpus(
        path,
        ability_names=("Frost Staff Heavy Attack",),
        source_id=42,
    )

    assert report.unresolved == ()
    assert [
        (item.report_code, item.fight_id, item.resource_change)
        for item in report.observations
    ] == [
        ("REPORT_A", 1, 2823.0),
        ("REPORT_B", 9, 2900.0),
    ]


def test_corpus_discovery_can_scope_to_one_report(tmp_path):
    path = _database(tmp_path)
    _insert(
        path,
        report_code="REPORT_A",
        fight_id=1,
        event_index=1,
        ability_id=101,
        ability_name="Frost Staff Heavy Attack",
        resource_change=2823.0,
    )
    _insert(
        path,
        report_code="REPORT_B",
        fight_id=2,
        event_index=2,
        ability_id=101,
        ability_name="Frost Staff Heavy Attack",
        resource_change=2900.0,
    )

    report = RotationHeavyAttackRestoreEsoLogsEvidenceService().discover_corpus(
        path,
        ability_names=("Frost Staff Heavy Attack",),
        report_code="REPORT_B",
    )

    assert [item.report_code for item in report.observations] == ["REPORT_B"]
    assert [item.resource_change for item in report.observations] == [2900.0]
