from pathlib import Path

from ui.reference_data_model import ReferenceEntry
from ui.reference_version_history import enrich_reference_entries_with_version_history


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _cp(name: str) -> ReferenceEntry:
    return ReferenceEntry(
        name=name,
        entry_type="Champion Point",
        source_scope="Champion Points",
        tags=("CHAMPION POINT",),
        summary="Current canonical Champion Point description.",
        details=(("Authority", "Canonical Champion Point data"),),
    )


def test_checked_in_champion_point_history_tranche_is_attached():
    names = (
        "Backstabber",
        "Biting Aura",
        "Deadly Aim",
        "Master-at-Arms",
        "Thaumaturge",
        "Occult Overload",
        "Wrathful Strikes",
        "Rejuvenator",
        "Exploiter",
        "Force of Nature",
    )

    result = enrich_reference_entries_with_version_history(tuple(_cp(name) for name in names), DATA)
    by_name = {entry.name: entry for entry in result}

    assert "U34 • 2022 • Nerf" in dict(by_name["Backstabber"].details)["History / Legacy"]
    assert "down from 3%" in dict(by_name["Backstabber"].details)["History / Legacy"]

    for name in ("Biting Aura", "Deadly Aim", "Master-at-Arms", "Thaumaturge"):
        history = dict(by_name[name].details)["History / Legacy"]
        assert "U34 • 2022 • Rework" in history
        assert "2 stages at 25 points" in history
        assert "5 stages at 10 points" in history

    occult = dict(by_name["Occult Overload"].details)["History / Legacy"]
    assert "U34 • 2022 • Rework" in occult
    assert "2560 Oblivion Damage" in occult

    wrathful = dict(by_name["Wrathful Strikes"].details)["History / Legacy"]
    rejuvenator = dict(by_name["Rejuvenator"].details)["History / Legacy"]
    assert "U34 • 2022 • Buff" in wrathful
    assert "up from 33" in wrathful
    assert "U34 • 2022 • Buff" in rejuvenator
    assert "up from 33" in rejuvenator

    exploiter = dict(by_name["Exploiter"].details)["History / Legacy"]
    assert "U34 • 2022 • Returned" in exploiter
    assert "Off Balance" in exploiter

    force = dict(by_name["Force of Nature"].details)["History / Legacy"]
    assert "U34 • 2022 • Introduced" in force
    assert "900 Offensive Penetration" in force

    for entry in result:
        assert any("PC/Mac Patch Notes v8.0.5" in item for item in entry.evidence)
        assert any("7612709" in item for item in entry.evidence)


def test_champion_point_history_remains_reference_only_metadata():
    entry = enrich_reference_entries_with_version_history((_cp("Force of Nature"),), DATA)[0]

    assert entry.entry_type == "Champion Point"
    assert entry.summary == "Current canonical Champion Point description."
    assert dict(entry.details)["Authority"] == "Canonical Champion Point data"
    assert "History / Legacy" in dict(entry.details)
