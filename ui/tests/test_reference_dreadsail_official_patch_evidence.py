from pathlib import Path

from ui.reference_encounter_evidence import load_reviewed_encounter_evidence_entries


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _entry(name: str):
    entries = load_reviewed_encounter_evidence_entries(DATA)
    return next(entry for entry in entries if entry.name == name)


def test_rapid_deluge_uses_official_u34_non_blockable_evidence():
    entry = _entry("Rapid Deluge — Tideborn Taleria")
    text = entry.detail_text()

    assert "Rapid Deluge Blockable: No" in text
    assert any("PTS Patch Notes v8.0.2" in item for item in entry.evidence)


def test_rapid_deluge_keeps_hardmode_target_count_disagreement_visible():
    entry = _entry("Rapid Deluge — Tideborn Taleria")
    text = entry.detail_text()

    assert "Hardmode Target Count Current Guide: 8" in text
    assert "Unresolved Conflict Uesp 6 Vs Current Guide 8" in text
    assert "Target Count By Difficulty" in text


def test_nematocyst_cloud_uses_official_u34_non_cleanseable_evidence():
    entry = _entry("Nematocyst Cloud — Tideborn Taleria")

    assert "Nematocyst Cloud Cleanseable: No" in entry.detail_text()
    assert any("PTS Patch Notes v8.0.2" in item for item in entry.evidence)


def test_cave_in_uses_official_u34_dodgeable_evidence():
    entry = _entry("Cave In — Tideborn Taleria")

    assert "Cave In Dodgeable: Yes" in entry.detail_text()
    assert any("PTS Patch Notes v8.0.2" in item for item in entry.evidence)
