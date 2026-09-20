from __future__ import annotations

import json
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

    (data / "characters.json").write_text(
        json.dumps(
            {
                "schema_version": 4,
                "players": [],
                "characters": [],
                "builds": [],
                "team_assignments": [],
            }
        ),
        encoding="utf-8",
    )
    (data / "builds.json").write_text('{"Members": []}', encoding="utf-8")
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


def test_packaged_release_privacy_audit_rejects_canonical_players(tmp_path: Path) -> None:
    root = _package(tmp_path)
    characters = root / "data" / "characters.json"
    payload = json.loads(characters.read_text(encoding="utf-8"))
    payload["players"] = [{"player_id": "player-1", "name": "Jarakeen"}]
    characters.write_text(json.dumps(payload), encoding="utf-8")

    errors = audit(root)

    assert errors == [
        "packaged characters.json has non-empty players: 1 row(s)"
    ]
