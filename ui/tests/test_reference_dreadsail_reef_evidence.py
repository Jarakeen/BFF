from pathlib import Path

from ui.reference_encounter_evidence import load_reviewed_encounter_evidence_entries


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data"


def _entries_by_name():
    return {
        entry.name: entry
        for entry in load_reviewed_encounter_evidence_entries(DATA_ROOT)
    }


def test_twins_dome_reference_joins_shared_dome_rules():
    entries = _entries_by_name()
    ember = entries["Destructive Ember — Lylanar and Turlassil"]
    hailstone = entries["Piercing Hailstone — Lylanar and Turlassil"]

    for entry in (ember, hailstone):
        text = entry.detail_text()
        assert "Opposite Element Dome Required" in text
        assert "Fire Enemies Require: Ice Dome" in text
        assert "Ice Enemies Require: Fire Dome" in text
        assert "Opposing Dome Contact Overload" in text
        assert "Domes Dissipate: Yes" in text


def test_reef_guardian_reference_joins_acid_reflux_behavior_and_timing():
    entries = _entries_by_name()
    acid = entries["Acid Reflux — Reef Guardian"]
    text = acid.detail_text()

    assert "Acid Reflux Core Behavior" in text
    assert "Target: Taunt Target" in text
    assert "Leaves Acid Pools: Yes" in text
    assert "Applies Stacking Acid Vulnerability: Yes" in text
    assert "Acid Pool Count: 5" in text


def test_taleria_reference_joins_rapid_deluge_response_and_veteran_timing():
    entries = _entries_by_name()
    deluge = entries["Rapid Deluge — Tideborn Taleria"]
    text = deluge.detail_text()

    assert "Rapid Deluge Veteran Behavior" in text
    assert "Target Count: 5" in text
    assert "Detonation Seconds Approx: 6" in text
    assert "Swimming Mitigates Blast: Yes" in text
    assert "Rapid Deluge Swimming Checked" in text


def test_taleria_maelstrom_reference_exposes_heal_check_and_tick_cadence():
    entries = _entries_by_name()
    maelstrom = entries["Maelstrom — Tideborn Taleria"]
    text = maelstrom.detail_text()

    assert "Maelstrom Veteran Behavior" in text
    assert "Duration Seconds: 6" in text
    assert "Tick Interval Seconds: 0.3" in text
    assert "Damage Ramps: Yes" in text
    assert "Heal Check: Yes" in text
