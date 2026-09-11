import json
from pathlib import Path

from ui.reference_data_model import ReferenceEntry
from ui.reference_version_history import enrich_reference_entries_with_version_history


def _entry(name: str, entry_type: str) -> ReferenceEntry:
    return ReferenceEntry(
        name=name,
        entry_type=entry_type,
        source_scope="Gear",
        tags=(entry_type.upper(),),
        summary="Current canonical description.",
        details=(("Authority", "Canonical data"),),
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


def test_history_does_not_attach_to_unmatched_entry(tmp_path: Path):
    (tmp_path / "reference_version_history.json").write_text(
        json.dumps({"schema_version": 1, "events": []}),
        encoding="utf-8",
    )

    entry = _entry("Example Set", "Gear Set")
    result = enrich_reference_entries_with_version_history((entry,), tmp_path)[0]

    assert result == entry
