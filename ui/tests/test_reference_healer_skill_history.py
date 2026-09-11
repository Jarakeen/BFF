from pathlib import Path
import json

from ui.reference_data_model import ReferenceEntry
from ui.reference_version_history import enrich_reference_entries_with_version_history


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _entry(name: str, entry_type: str, skill_line: str) -> ReferenceEntry:
    current_name = name.split(" — ", 1)[0]
    return ReferenceEntry(
        name=name,
        entry_type=entry_type,
        source_scope="Skills",
        tags=(entry_type.upper(),),
        summary="Current canonical description.",
        details=(
            ("Authority", "Canonical data"),
            ("Current name", current_name),
            ("Skill line", skill_line),
        ),
    )


def test_split_history_files_are_merged(tmp_path: Path):
    (tmp_path / "reference_version_history.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "entity_type": "Skill",
                        "name": "Example Heal",
                        "context": "Healing Line",
                        "update": "U1",
                        "summary": "First event.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "reference_version_history_healer_skills.json").write_text(
        json.dumps(
            {
                "events": [
                    {
                        "entity_type": "Skill",
                        "name": "Example Heal",
                        "context": "Healing Line",
                        "update": "U2",
                        "summary": "Second event.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = enrich_reference_entries_with_version_history(
        (_entry("Example Heal — Healing Line", "Skill", "Healing Line"),),
        tmp_path,
    )[0]
    history = dict(result.details)["History / Legacy"]

    assert "U1: First event." in history
    assert "U2: Second event." in history


def test_checked_in_healer_history_covers_notable_skill_and_passive_changes():
    entries = (
        _entry("Radiating Regeneration — Restoration Staff", "Skill", "Restoration Staff"),
        _entry("Illustrious Healing — Restoration Staff", "Skill", "Restoration Staff"),
        _entry("Energy Orb — Undaunted", "Skill", "Undaunted"),
        _entry("Budding Seeds — Green Balance", "Skill", "Green Balance"),
        _entry("Maturation — Green Balance", "Passive", "Green Balance"),
    )

    result = enrich_reference_entries_with_version_history(entries, DATA)
    by_name = {entry.name: entry for entry in result}

    radiating = dict(by_name["Radiating Regeneration — Restoration Staff"].details)["History / Legacy"]
    assert "U23 • 2019 • Rename And Rework" in radiating
    assert "former Mutagen morph" in radiating
    assert "U35 • 2022 • Healing Adjustment" in radiating

    illustrious = dict(by_name["Illustrious Healing — Restoration Staff"].details)["History / Legacy"]
    assert "U23 • 2019 • Rework" in illustrious
    assert "U35 • 2022 • Rework" in illustrious
    assert "no longer provided its former extra-healing bonus" in illustrious

    orb = dict(by_name["Energy Orb — Undaunted"].details)["History / Legacy"]
    assert "U23 • 2019 • Rework" in orb
    assert "multiple allies could use the same orb" in orb
    assert "U35 • 2022 • Cadence Adjustment" in orb

    seeds = dict(by_name["Budding Seeds — Green Balance"].details)["History / Legacy"]
    assert "U27 • 2020 • Behavior Fix" in seeds
    assert "U35 • 2022 • Buff" in seeds

    maturation = dict(by_name["Maturation — Green Balance"].details)["History / Legacy"]
    assert "U20 • 2018 • Buff" in maturation
    assert "10/20 seconds" in maturation

    for entry in result:
        assert any(value.startswith("History source:") for value in entry.evidence)
        assert any(value.startswith("History source URL:") for value in entry.evidence)
