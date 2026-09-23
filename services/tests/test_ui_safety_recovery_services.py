from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from services.ui_draft_recovery_service import UiDraftRecoveryService
from services.user_safety_snapshot_service import UserSafetySnapshotService


def test_ui_draft_recovery_round_trip_and_discard(tmp_path: Path) -> None:
    service = UiDraftRecoveryService(tmp_path / "drafts")
    path = service.save(
        "raid plan / Performance Mode",
        {"kind": "raid_plan", "plan": {"plan_id": "pm-rg", "name": "PM RG"}},
    )

    assert path.is_file()
    loaded = service.load("raid plan / Performance Mode")
    assert loaded is not None
    assert loaded["payload"]["plan"]["plan_id"] == "pm-rg"
    assert loaded["saved_at"]

    service.discard("raid plan / Performance Mode")
    assert service.load("raid plan / Performance Mode") is None


def test_ui_draft_recovery_write_is_valid_json(tmp_path: Path) -> None:
    service = UiDraftRecoveryService(tmp_path / "drafts")
    path = service.save("comp-maker", {"chairs": [{"seat_id": "tank-1"}]})

    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["payload"]["chairs"] == [{"seat_id": "tank-1"}]


def test_user_safety_snapshot_is_independent_sqlite_backup(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    backup_dir = tmp_path / "snapshots"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE state (value TEXT NOT NULL)")
        db.execute("INSERT INTO state(value) VALUES ('before')")
        db.commit()

    service = UserSafetySnapshotService(database, backup_dir, keep=3)
    snapshot = service.create("delete-team-Performance Mode")

    assert snapshot is not None and snapshot.is_file()

    with sqlite3.connect(database) as db:
        db.execute("UPDATE state SET value='after'")
        db.commit()

    with sqlite3.connect(snapshot) as db:
        assert db.execute("SELECT value FROM state").fetchone()[0] == "before"


def test_user_safety_snapshot_prunes_old_backups(tmp_path: Path) -> None:
    database = tmp_path / "foundrydock.db"
    backup_dir = tmp_path / "snapshots"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE state (value INTEGER NOT NULL)")
        db.execute("INSERT INTO state(value) VALUES (1)")
        db.commit()

    service = UserSafetySnapshotService(database, backup_dir, keep=2)
    for index in range(4):
        with sqlite3.connect(database) as db:
            db.execute("UPDATE state SET value=?", (index,))
            db.commit()
        service.create(f"snapshot-{index}")

    assert len(tuple(backup_dir.glob("*__foundrydock.db"))) == 2
