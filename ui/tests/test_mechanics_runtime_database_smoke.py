from __future__ import annotations

from pathlib import Path

from services.encounter_boss_guide import EncounterBossGuideService
from ui.mechanics_search_support import searchable_encounter_ids


ROOT = Path(__file__).resolve().parents[2]
DATABASE = ROOT / "data" / "eso.db"


def test_runtime_database_keeps_mechanics_selector_index_populated() -> None:
    """The shipped/source runtime DB must retain the persisted boss-guide index."""

    summaries = EncounterBossGuideService(DATABASE).encounter_summaries()

    assert summaries, "Mechanics CONTENT/BOSS selectors would be empty"
    assert any(row.content_name == "Asylum Sanctorium" for row in summaries)
    assert any("Felms" in row.name for row in summaries)


def test_runtime_database_mechanics_search_finds_known_boss() -> None:
    """Guard against replacing eso.db with a copy that drops encounter search data."""

    matches = searchable_encounter_ids(DATABASE, "Felms")

    assert matches, "Mechanics search would return no results for a known boss"
