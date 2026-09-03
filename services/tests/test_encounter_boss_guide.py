from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from services.encounter_boss_guide import (
    EncounterBossGuideError,
    EncounterBossGuideNotFound,
    EncounterBossGuideService,
)
from services.encounter_schema import ensure_encounter_schema


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "eso.db"
    connection = sqlite3.connect(path)
    try:
        ensure_encounter_schema(connection)
        connection.execute(
            """
            INSERT INTO content (
                id, name, slug, content_type, summary, location,
                source_url, source_page_title, source_revision_id,
                retrieved_at, source_license
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "dragonstar_arena",
                "Dragonstar Arena",
                "dragonstar-arena",
                "arena",
                "",
                "Craglorn",
                "https://example.test/content",
                "Dragonstar Arena",
                "content-rev",
                "2026-09-03T00:00:00Z",
                "CC BY-SA",
            ),
        )
        connection.execute(
            """
            INSERT INTO encounter (
                id, content_id, name, slug, summary, location, species, reaction,
                source_url, source_page_title, source_revision_id,
                retrieved_at, source_license
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "hiath_the_battlemaster",
                "dragonstar_arena",
                "Hiath the Battlemaster",
                "hiath-the-battlemaster",
                "Champion of Dragonstar Arena.",
                "Round 10: The Champion's Arena",
                "Human",
                "Hostile",
                "https://example.test/hiath",
                "Hiath the Battlemaster",
                "boss-rev",
                "2026-09-03T00:00:00Z",
                "CC BY-SA",
            ),
        )
        connection.execute(
            """
            INSERT INTO encounter_health(encounter_id, normal, veteran, hardmode)
            VALUES (?, ?, ?, ?)
            """,
            ("hiath_the_battlemaster", "1,515,587", "6,114,800", None),
        )
        connection.execute(
            """
            INSERT INTO encounter_ability (
                encounter_id, name, description, source_section, source_url,
                source_revision_id, interruptible, interrupt_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "hiath_the_battlemaster",
                "Agony",
                "Hiath stuns the player.",
                "Skills and Abilities",
                "https://example.test/hiath",
                "boss-rev",
                1,
                "Can be interrupted.",
            ),
        )
        connection.execute(
            """
            INSERT INTO encounter_ability (
                encounter_id, name, description, source_section, source_url,
                source_revision_id, interruptible, interrupt_note
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "hiath_the_battlemaster",
                "Invisibility",
                "Hiath briefly becomes invisible.",
                "Skills and Abilities",
                "https://example.test/hiath",
                "boss-rev",
                None,
                "",
            ),
        )
        connection.execute(
            """
            INSERT INTO encounter_phase (
                encounter_id, label, threshold, description, source_section,
                source_url, source_revision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "hiath_the_battlemaster",
                "Execute",
                "25%",
                "Explicit source-backed phase.",
                "Phases",
                "https://example.test/hiath",
                "boss-rev",
            ),
        )
        connection.commit()
    finally:
        connection.close()
    return path


def test_boss_guide_projects_persisted_structure_without_inference(tmp_path: Path) -> None:
    service = EncounterBossGuideService(_database(tmp_path))

    guide = service.get("hiath_the_battlemaster")

    assert guide.encounter_id == "hiath_the_battlemaster"
    assert guide.content_id == "dragonstar_arena"
    assert guide.content_name == "Dragonstar Arena"
    assert guide.name == "Hiath the Battlemaster"
    assert guide.summary == "Champion of Dragonstar Arena."
    assert guide.location == "Round 10: The Champion's Arena"
    assert guide.species == "Human"
    assert guide.reaction == "Hostile"
    assert guide.health == (("normal", "1,515,587"), ("veteran", "6,114,800"))
    assert [row.name for row in guide.abilities] == ["Agony", "Invisibility"]
    assert guide.abilities[0].interruptible is True
    assert guide.abilities[0].interrupt_note == "Can be interrupted."
    assert guide.abilities[1].interruptible is None
    assert guide.abilities[1].source_revision_id == "boss-rev"
    assert len(guide.phases) == 1
    assert guide.phases[0].label == "Execute"
    assert guide.phases[0].threshold == "25%"
    assert guide.source_url == "https://example.test/hiath"
    assert guide.source_revision_id == "boss-rev"


def test_boss_guide_lists_persisted_encounters(tmp_path: Path) -> None:
    service = EncounterBossGuideService(_database(tmp_path))

    assert service.encounter_ids() == ("hiath_the_battlemaster",)


def test_boss_guide_rejects_missing_encounter(tmp_path: Path) -> None:
    service = EncounterBossGuideService(_database(tmp_path))

    with pytest.raises(EncounterBossGuideNotFound):
        service.get("not_real")


def test_boss_guide_rejects_blank_encounter_id(tmp_path: Path) -> None:
    service = EncounterBossGuideService(_database(tmp_path))

    with pytest.raises(ValueError):
        service.get("  ")


def test_boss_guide_rejects_missing_database(tmp_path: Path) -> None:
    service = EncounterBossGuideService(tmp_path / "missing.db")

    with pytest.raises(EncounterBossGuideError, match="does not exist"):
        service.encounter_ids()


def test_boss_guide_rejects_incomplete_schema(tmp_path: Path) -> None:
    database = tmp_path / "partial.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute("CREATE TABLE encounter(id TEXT PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()

    service = EncounterBossGuideService(database)
    with pytest.raises(EncounterBossGuideError, match="missing required table"):
        service.get("hiath_the_battlemaster")
