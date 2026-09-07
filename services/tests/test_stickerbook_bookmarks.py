import sqlite3
from pathlib import Path

from services.stickerbook_bookmark_service import StickerbookBookmarkService


def _database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE gear_set (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        connection.executemany(
            "INSERT INTO gear_set(id, name) VALUES (?, ?)",
            ((10, "Pillager's Profit"), (20, "Powerful Assault")),
        )
        connection.commit()


def test_bookmarks_are_profile_aware_and_toggleable(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _database(path)
    service = StickerbookBookmarkService(path)

    assert service.bookmarked_set_ids("Jarakeen") == set()
    service.set_bookmarked("Jarakeen", 10, True)

    assert service.is_bookmarked("Jarakeen", 10) is True
    assert service.bookmarked_set_ids("Jarakeen") == {10}
    assert service.bookmarked_set_ids("Other") == set()

    service.set_bookmarked("Jarakeen", 10, False)
    assert service.is_bookmarked("Jarakeen", 10) is False
    assert service.bookmarked_set_ids("Jarakeen") == set()


def test_bookmark_note_survives_toggle_without_replacement(tmp_path) -> None:
    path = tmp_path / "eso.db"
    _database(path)
    service = StickerbookBookmarkService(path)

    service.set_bookmarked("Jarakeen", 20, True, note="Try on off tank in DSR")
    service.set_bookmarked("Jarakeen", 20, False)
    service.set_bookmarked("Jarakeen", 20, True)

    assert service.note("Jarakeen", 20) == "Try on off tank in DSR"


def test_stickerbook_bookmark_ui_support_exposes_comp_shortlist_controls() -> None:
    source = Path("ui/stickerbook_bookmark_support.py").read_text(encoding="utf-8")
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(encoding="utf-8")

    assert 'filter_combo.addItem("★ Bookmarked for Comp", "bookmarked")' in source
    assert 'QPushButton("☆ Save for Trial Comp")' in source
    assert '"★ Saved for Trial Comp"' in source
    assert "StickerbookPage._filtered_rows = _filtered_rows_with_bookmarks" in source
    assert "install_stickerbook_bookmarks()" in installer
