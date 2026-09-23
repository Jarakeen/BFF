from __future__ import annotations

from pathlib import Path
import sqlite3

from tools.audit_packaged_release_privacy import audit


def _package(tmp_path: Path) -> Path:
    root = tmp_path / "FoundryDock-0.1.3"
    data = root / "data"
    data.mkdir(parents=True)

    with sqlite3.connect(data / "eso.db") as db:
        db.executescript(
            """
            CREATE TABLE ability (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            INSERT INTO ability VALUES (1, 'Combat Prayer');

            CREATE TABLE roster_member (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL
            );
            """
        )
        db.commit()

    return root


def test_packaged_release_privacy_audit_accepts_clean_first_install(tmp_path: Path) -> None:
    root = _package(tmp_path)
    assert audit(root) == []


def test_packaged_release_privacy_audit_rejects_roster_rows(tmp_path: Path) -> None:
    root = _package(tmp_path)
    with sqlite3.connect(root / "data" / "eso.db") as db:
        db.execute("INSERT INTO roster_member(player_name) VALUES ('Jarakeen')")
        db.commit()

    errors = audit(root)

    assert errors == [
        "packaged user-state table is not empty: roster_member (1 row(s))"
    ]


def test_packaged_release_privacy_audit_rejects_legacy_build_state_files(tmp_path: Path) -> None:
    root = _package(tmp_path)
    (root / "data" / "characters.json").write_text("{}", encoding="utf-8")
    (root / "data" / "builds.json").write_text("{}", encoding="utf-8")

    errors = audit(root)

    assert errors == [
        f"legacy user-state file should not be packaged: {root / 'data' / 'characters.json'}",
        f"legacy user-state file should not be packaged: {root / 'data' / 'builds.json'}",
    ]
