from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from services.collection_progress_pydantic_schema import (
    validate_collection_batch,
    validate_collection_progress,
    validate_stickerbook_bookmark,
)
from services.stickerbook_bookmark_service import StickerbookBookmarkService


def test_collection_progress_rejects_invalid_identity_before_sql() -> None:
    with pytest.raises(ValueError):
        validate_collection_progress({
            "profile": "Default",
            "item_id": 0,
            "owned": True,
            "acquired_on": "",
            "notes": "",
        })


def test_collection_batch_rejects_invalid_item_before_sql() -> None:
    with pytest.raises(ValueError):
        validate_collection_batch({
            "profile": "Default",
            "owned_by_id": {1: True, -2: False},
        })


def test_stickerbook_rejects_invalid_set_before_database_mutation(tmp_path: Path) -> None:
    path = tmp_path / "foundrydock.db"
    service = StickerbookBookmarkService(path)

    with pytest.raises(ValueError):
        service.set_bookmarked("Default", 0, True)

    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM stickerbook_set_bookmark").fetchone()[0] == 0


def test_stickerbook_round_trips_valid_bookmark(tmp_path: Path) -> None:
    path = tmp_path / "foundrydock.db"
    service = StickerbookBookmarkService(path)
    service.set_bookmarked(" Raid Lead ", 42, True, note="Try on Yolnahkriin")

    assert service.is_bookmarked("Raid Lead", 42)
    assert service.note("Raid Lead", 42) == "Try on Yolnahkriin"


def test_stickerbook_schema_rejects_oversized_note() -> None:
    with pytest.raises(ValueError):
        validate_stickerbook_bookmark({
            "profile": "Default",
            "set_id": 42,
            "bookmarked": True,
            "note": "x" * 8001,
        })
