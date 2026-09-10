import json
from pathlib import Path

from ui.reference_common_names import enrich_reference_entries_with_common_names
from ui.reference_data_model import ReferenceEntry


def _entry() -> ReferenceEntry:
    return ReferenceEntry(
        name="Rapid Deluge — Tideborn Taleria",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("ENCOUNTER",),
        summary="Rapid Deluge mechanic.",
        details=(("Authority", "Reviewed encounter evidence"),),
    )


def test_common_name_is_displayed_and_searchable(tmp_path: Path):
    (tmp_path / "reference_common_names.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "entry_name": "Rapid Deluge — Tideborn Taleria",
                        "common_names": ["Bubbles"],
                        "source": "player_raid_terminology",
                        "notes": "Common raid callout.",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = enrich_reference_entries_with_common_names((_entry(),), tmp_path)[0]

    assert dict(result.details)["Common names"] == "Bubbles"
    assert "bubbles" in result.search_text
    assert "Rapid Deluge" in result.name
    assert any("Player Raid Terminology" in item for item in result.evidence)


def test_common_name_layer_does_not_rename_canonical_entry(tmp_path: Path):
    (tmp_path / "reference_common_names.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "entry_name": "Rapid Deluge — Tideborn Taleria",
                        "common_names": ["Bubbles", "Deluge"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = enrich_reference_entries_with_common_names((_entry(),), tmp_path)[0]

    assert result.name == "Rapid Deluge — Tideborn Taleria"
    assert dict(result.details)["Common names"] == "Bubbles, Deluge"
