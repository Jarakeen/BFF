from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import zipfile

import pytest

from services.encounter_research_archive import import_research_archive


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE content(id TEXT PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute(
            """
            CREATE TABLE encounter(
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                content_id TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO content(id, name) VALUES (?, ?)",
            ("rockgrove", "Rockgrove"),
        )
        connection.executemany(
            "INSERT INTO encounter(id, name, content_id) VALUES (?, ?, ?)",
            (
                ("oaxiltso", "Oaxiltso", "rockgrove"),
                ("xalvakka", "Xalvakka", "rockgrove"),
                ("wamasu", "Wamasu", "rockgrove"),
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return path


def _zip(tmp_path: Path) -> tuple[Path, dict[str, bytes]]:
    path = tmp_path / "strats.zip"
    members = {
        "strats/Oaxiltso.txt": (
            "Oaxiltso\n"
            "At 90% health, Oaxiltso summons an add every 30 seconds.\n"
            "The group should interrupt the channel.\n"
            "Move away from the wamasu add before it explodes.\n"
        ).encode(),
        "strats/guide.htm": (
            "<html lang='fr-FR'><head><title>Guide Rochebosque</title>"
            "<link rel='canonical' href='https://example.test/fr-guide'></head>"
            "<body><h2>Xalvakka</h2><p>À 50% de santé, la phase finale commence.</p>"
            "</body></html>"
        ).encode(),
        "strats/diagram.png": b"not-a-real-png",
    }
    with zipfile.ZipFile(path, "w") as zipped:
        for name, data in members.items():
            zipped.writestr(name, data)
    return path, members


def _manifest(tmp_path: Path, members: dict[str, bytes]) -> Path:
    payload = {
        "schema_version": 1,
        "sources": [
            {
                "archive_member": "Oaxiltso.txt",
                "sha256": sha256(members["strats/Oaxiltso.txt"]).hexdigest(),
                "source_name": "Saved Oaxiltso guide",
                "language": "en",
                "content_hint": "Rockgrove",
                "encounter_hint": "Oaxiltso",
            },
            {
                "archive_member": "guide.htm",
                "sha256": sha256(members["strats/guide.htm"]).hexdigest(),
                "source_name": "French guide",
                "language": "fr",
                "content_hint": "Rockgrove",
            },
            {
                "archive_member": "diagram.png",
                "sha256": sha256(members["strats/diagram.png"]).hexdigest(),
                "source_name": "Strategy visual",
                "content_hint": "Rockgrove",
                "encounter_hint": "Xalvakka",
            },
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_research_archive_stages_multilingual_encounter_candidates(tmp_path: Path) -> None:
    archive, members = _zip(tmp_path)
    bundle = import_research_archive(
        archive,
        _database(tmp_path),
        manifest_path=_manifest(tmp_path, members),
    )

    assert len(bundle.sources) == 3
    assert bundle.visual_sources == 1
    assert {row.language for row in bundle.sources} == {"en", "fr", "non_text"}

    oaxiltso = [row for row in bundle.candidates if row.encounter_id == "oaxiltso"]
    assert any(row.trigger_type == "boss_health" and row.trigger_value == "90%" for row in oaxiltso)
    assert any(row.trigger_type == "repeat_interval" and row.trigger_value == "30 seconds" for row in oaxiltso)
    assert any(row.event_type == "interrupt" for row in oaxiltso)
    assert any("wamasu add" in row.evidence_text for row in oaxiltso)
    assert not [row for row in bundle.candidates if row.encounter_id == "wamasu"]

    xalvakka = [row for row in bundle.candidates if row.encounter_id == "xalvakka"]
    assert xalvakka
    assert all(row.source_language == "fr" for row in xalvakka)
    assert any("50%" in row.evidence_text for row in xalvakka)
    assert any(
        row.trigger_type == "boss_health" and row.trigger_value == "50%"
        for row in xalvakka
    )

    french_source = next(row for row in bundle.sources if row.language == "fr")
    assert french_source.source_url == "https://example.test/fr-guide"
    assert french_source.title == "Guide Rochebosque"


def test_research_archive_refuses_manifest_hash_drift(tmp_path: Path) -> None:
    archive, members = _zip(tmp_path)
    manifest = _manifest(tmp_path, members)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["sources"][0]["sha256"] = "0" * 64
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RuntimeError, match="hash mismatch"):
        import_research_archive(archive, _database(tmp_path), manifest_path=manifest)


def test_research_archive_does_not_create_canonical_tables_or_rows(tmp_path: Path) -> None:
    archive, members = _zip(tmp_path)
    database = _database(tmp_path)

    import_research_archive(
        archive,
        database,
        manifest_path=_manifest(tmp_path, members),
    )

    connection = sqlite3.connect(database)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        connection.close()

    assert "encounter_canonical_fact" not in tables
    assert tables == {"content", "encounter"}
