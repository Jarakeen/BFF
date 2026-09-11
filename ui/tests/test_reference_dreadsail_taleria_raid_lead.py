from pathlib import Path

from ui.reference_common_names import enrich_reference_entries_with_common_names
from ui.reference_encounter_evidence import load_reviewed_encounter_evidence_entries
from ui.reference_mitigations import enrich_reference_entries_with_mitigations


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _entries():
    entries = load_reviewed_encounter_evidence_entries(DATA)
    entries = enrich_reference_entries_with_common_names(entries, DATA)
    entries = enrich_reference_entries_with_mitigations(entries, DATA)
    return {entry.name: entry for entry in entries}


def test_taleria_bridge_phase_is_visible_searchable_and_actionable():
    bridge = _entries()["Bridge Phase — Tideborn Taleria"]
    text = bridge.detail_text()

    assert "50%" in text and "35%" in text and "20%" in text
    assert "60" in text
    assert "Group Wipe" in text
    assert "bridges" in bridge.search_text
    assert "portals" in bridge.search_text
    assert "channeler to 50%" in bridge.mitigation_note


def test_taleria_siren_and_behemoth_have_raid_lead_mitigation():
    entries = _entries()

    siren = entries["Summon Siren — Tideborn Taleria"]
    assert "break free" in siren.mitigation_note.casefold()
    assert "Lure of the Sea" in siren.detail_text()

    behemoth = entries["Summon Behemoth — Tideborn Taleria"]
    assert "off-tank" in behemoth.mitigation_note.casefold()
    assert "Hardmode Interval Seconds: 45" in behemoth.detail_text()


def test_taleria_tank_attacks_have_scan_friendly_mitigation():
    entries = _entries()

    coral = entries["Coral Slam — Tideborn Taleria"]
    assert "roll-dodge" in coral.mitigation_note.casefold()
    assert "Heavy Attack: Yes" in coral.detail_text()

    arcing = entries["Arcing Slash — Tideborn Taleria"]
    assert "faced away from the group" in arcing.mitigation_note.casefold()
    assert "Soaked Wound" in arcing.detail_text()
