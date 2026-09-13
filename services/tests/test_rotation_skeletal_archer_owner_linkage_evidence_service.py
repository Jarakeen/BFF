from __future__ import annotations

import json
import sqlite3

from services.rotation_skeletal_archer_owner_linkage_evidence_service import (
    RotationSkeletalArcherOwnerLinkageEvidenceService,
)


def _db(path, *, owner_column: bool = False) -> None:
    with sqlite3.connect(path) as db:
        if owner_column:
            db.execute(
                "CREATE TABLE log_actor (report_code TEXT, fight_id INTEGER, actor_id INTEGER, actor_type TEXT, owner_id INTEGER)"
            )
        else:
            db.execute(
                "CREATE TABLE log_actor (report_code TEXT, fight_id INTEGER, actor_id INTEGER, actor_type TEXT)"
            )
        db.execute(
            """
            CREATE TABLE log_event (
                report_code TEXT,
                fight_id INTEGER,
                event_index INTEGER,
                timestamp REAL,
                event_type TEXT,
                source_id INTEGER,
                ability_game_id INTEGER,
                raw_json TEXT
            )
            """
        )
        db.commit()


def test_reports_no_linkage_when_schema_and_raw_json_have_none(tmp_path) -> None:
    path = tmp_path / "logs.db"
    _db(path)
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?)",
            ("R", 1, 1, 1000, "damage", 500, 122774, json.dumps({"ability": {"name": "Arrow"}})),
        )
        db.commit()

    report = RotationSkeletalArcherOwnerLinkageEvidenceService(path).inspect()

    assert report.event_count == 1
    assert report.source_actor_count == 1
    assert report.has_imported_linkage_evidence is False
    assert report.actor_linkage_columns == ()
    assert report.raw_linkage_paths == ()
    assert any("no explicit owner/master/parent" in item for item in report.unresolved)


def test_reports_actor_and_raw_linkage_hints_without_claiming_ownership(tmp_path) -> None:
    path = tmp_path / "logs.db"
    _db(path, owner_column=True)
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO log_event VALUES (?,?,?,?,?,?,?,?)",
            (
                "R",
                1,
                1,
                1000,
                "damage",
                500,
                122774,
                json.dumps({"source": {"ownerID": 42}, "summon": {"parent": 42}}),
            ),
        )
        db.commit()

    report = RotationSkeletalArcherOwnerLinkageEvidenceService(path).inspect()

    assert report.has_imported_linkage_evidence is True
    assert report.actor_linkage_columns == ("owner_id",)
    assert "source.ownerID" in report.raw_linkage_paths
    assert "summon" in report.raw_linkage_paths
    assert "summon.parent" in report.raw_linkage_paths
    assert report.raw_linkage_sample_count == 1
