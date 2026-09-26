from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.achievement_progress_service import AchievementProgressService


def test_database_achievement_progress_round_trips_strict_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "foundrydock.db"
    service = AchievementProgressService(path)
    service.ensure_profile("Jarakeen")
    service.set_active_profile("Jarakeen")
    service.replace_completed("Jarakeen", ("100", "200"))

    reopened = AchievementProgressService(path)
    assert reopened.active_profile == "Jarakeen"
    assert reopened.completed_ids() == {"100", "200"}


def test_invalid_achievement_id_is_rejected_before_database_mutation(tmp_path: Path) -> None:
    path = tmp_path / "foundrydock.db"
    service = AchievementProgressService(path)
    service.set_complete("100", True)

    with sqlite3.connect(path) as db:
        before = tuple(db.execute(
            "SELECT profile_name, achievement_id FROM achievement_progress ORDER BY 1, 2"
        ).fetchall())

    with pytest.raises(ValueError):
        service.set_complete("", True)

    with sqlite3.connect(path) as db:
        after = tuple(db.execute(
            "SELECT profile_name, achievement_id FROM achievement_progress ORDER BY 1, 2"
        ).fetchall())
    assert after == before
