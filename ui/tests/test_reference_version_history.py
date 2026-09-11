import json
from pathlib import Path

from ui.reference_data_model import ReferenceEntry
from ui.reference_version_history import enrich_reference_entries_with_version_history


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _entry(
    name: str,
    entry_type: str,
    *,
    current_name: str = "",
    skill_line: str = "",
) -> ReferenceEntry:
    details = [("Authority", "Canonical data")]
    if current_name:
        details.append(("Current name", current_name))
    if skill_line:
        details.append(("Skill line", skill_line))
    return ReferenceEntry(
        name=name,
        entry_type=entry_type,
        source_scope="Gear",
        tags=(entry_type.upper(),),
        summary="Current canonical description.",
        details=tuple(details),
    )


def test_reviewed_history_is_appended_as_trivia_only(tmp_path: Path):
    (tmp_path / "reference_version_history.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "events": [
                    {
                        "entity_type": "Gear Set",
                        "name": "Example Set",
                        "update": "U34",
                        "year": 2022,
                        "change_type": "released",
                        "summary": "Released with a 5-piece bonus of 1000 Weapon and Spell Damage.",
                        "source": "Reviewed patch note",
                        "source_url": "https://example.invalid/u34",
                    },
                    {
                        "entity_type": "Gear Set",
                        "name": "Example Set",
                        "update": "U36",
                        "year": 2022,
                        "change_type": "nerf",
                        "summary": "5-piece bonus reduced to 800 Weapon and Spell Damage.",
                        "source": "Reviewed patch note",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = enrich_reference_entries_with_version_history(
        (_entry("Example Set", "Gear Set"),),
        tmp_path,
    )[0]

    history = dict(result.details)["History / Legacy"]
    assert "U34 • 2022 • Released" in history
    assert "U36 • 2022 • Nerf" in history
    assert "1000 Weapon and Spell Damage" in history
    assert any("Reviewed patch note" in value for value in result.evidence)
    assert any("https://example.invalid/u34" in value for value in result.evidence)


def test_skill_history_can_match_current_name_plus_skill_line(tmp_path: Path):
    (tmp_path / "reference_version_history.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "events": [
                    {
                        "entity_type": "Skill",
                        "name": "Combat Prayer",
                        "context": "Restoration Staff",
                        "update": "U23",
                        "year": 2019,
                        "change_type": "balance",
                        "summary": "Reviewed historical change.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = enrich_reference_entries_with_version_history(
        (
            _entry(
                "Combat Prayer — Restoration Staff",
                "Skill",
                current_name="Combat Prayer",
                skill_line="Restoration Staff",
            ),
        ),
        tmp_path,
    )[0]

    assert "U23 • 2019 • Balance" in dict(result.details)["History / Legacy"]


def test_skill_history_context_prevents_same_name_collision(tmp_path: Path):
    (tmp_path / "reference_version_history.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "events": [
                    {
                        "entity_type": "Skill",
                        "name": "Shared Name",
                        "context": "Line A",
                        "update": "U40",
                        "summary": "Only Line A changed.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    entry = _entry(
        "Shared Name — Line B",
        "Skill",
        current_name="Shared Name",
        skill_line="Line B",
    )
    result = enrich_reference_entries_with_version_history((entry,), tmp_path)[0]

    assert "History / Legacy" not in dict(result.details)


def test_history_does_not_attach_to_unmatched_entry(tmp_path: Path):
    (tmp_path / "reference_version_history.json").write_text(
        json.dumps({"schema_version": 1, "events": []}),
        encoding="utf-8",
    )

    entry = _entry("Example Set", "Gear Set")
    result = enrich_reference_entries_with_version_history((entry,), tmp_path)[0]

    assert result == entry


def test_checked_in_history_seeds_gear_skill_passive_and_cp_examples():
    entries = (
        _entry("Serpent's Disdain", "Gear Set"),
        _entry("Pillager's Profit", "Gear Set"),
        _entry("Roaring Opportunist", "Gear Set"),
        _entry("Saxhleel Champion", "Gear Set"),
        _entry("Pearlescent Ward", "Gear Set"),
        _entry("Spell Power Cure", "Gear Set"),
        _entry("Powerful Assault", "Gear Set"),
        _entry(
            "Combat Prayer — Restoration Staff",
            "Skill",
            current_name="Combat Prayer",
            skill_line="Restoration Staff",
        ),
        _entry(
            "Essence Drain — Restoration Staff",
            "Passive",
            current_name="Essence Drain",
            skill_line="Restoration Staff",
        ),
        _entry("Fighting Finesse", "Champion Point"),
    )

    result = enrich_reference_entries_with_version_history(entries, DATA)
    by_name = {entry.name: entry for entry in result}

    assert "U34 • 2022 • Released" in dict(by_name["Serpent's Disdain"].details)["History / Legacy"]

    pillager = dict(by_name["Pillager's Profit"].details)["History / Legacy"]
    assert "U34 • 2022 • Released" in pillager
    assert "U39 • 2023 • Bug Fix" in pillager
    assert "U46 • 2025 • Nerf" in pillager

    roaring = dict(by_name["Roaring Opportunist"].details)["History / Legacy"]
    assert "U26 • 2020 • Released" in roaring
    assert "U27 • 2020 • Rework" in roaring
    assert "U47 • 2025 • Stat Line" in roaring
    assert "12 to 6" in roaring

    assert "U30 • 2021 • Released" in dict(by_name["Saxhleel Champion"].details)["History / Legacy"]
    assert "U34 • 2022 • Released" in dict(by_name["Pearlescent Ward"].details)["History / Legacy"]

    spell_power_cure = dict(by_name["Spell Power Cure"].details)["History / Legacy"]
    assert "U7 • 2015 • Launch-Era Balance" in spell_power_cure
    assert "U27 • 2020 • Rework" in spell_power_cure
    assert "6-person target cap" in spell_power_cure

    powerful_assault = dict(by_name["Powerful Assault"].details)["History / Legacy"]
    assert "U7 • 2015 • Launch-Era Buff" in powerful_assault
    assert "U27 • 2020 • Rework" in powerful_assault
    assert "307 Weapon and Spell Damage" in powerful_assault

    assert "U23 • 2019 • Balance" in dict(by_name["Combat Prayer — Restoration Staff"].details)["History / Legacy"]
    assert "U31 • 2021 • Buff" in dict(by_name["Essence Drain — Restoration Staff"].details)["History / Legacy"]
    assert "U34 • 2022 • Rework" in dict(by_name["Fighting Finesse"].details)["History / Legacy"]
