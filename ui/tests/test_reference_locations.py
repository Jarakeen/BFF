import json
from pathlib import Path

from ui.reference_data_model import ReferenceEntry
from ui.reference_locations import enrich_reference_entries_with_locations


def _entry(*related: str) -> ReferenceEntry:
    return ReferenceEntry(
        name="Example",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("REFERENCE",),
        summary="Example",
        details=(),
        related=tuple(related),
    )


def test_related_boss_name_gets_content_context(tmp_path: Path):
    boss_root = tmp_path / "eso_info" / "bosses"
    boss_root.mkdir(parents=True)
    (boss_root / "garvin_the_tracker.json").write_text(
        json.dumps(
            {
                "id": "garvin_the_tracker",
                "name": "Garvin the Tracker",
                "content_id": "lep_seclusa",
                "content_name": "Lep Seclusa",
                "location": "Lep Seclusa — Inlet Grotto",
            }
        ),
        encoding="utf-8",
    )

    result = enrich_reference_entries_with_locations(
        (_entry("Garvin the Tracker"),),
        tmp_path,
    )[0]

    assert result.related == ("Garvin the Tracker — Lep Seclusa",)


def test_reviewed_identity_fills_location_when_raw_boss_file_is_missing(tmp_path: Path):
    (tmp_path / "dungeon_encounter_identity.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "encounters": [
                    {
                        "content_id": "frostvault",
                        "content_name": "Frostvault",
                        "release_year": 2019,
                        "release_update": 21,
                        "release_pack": "Wrathstone",
                        "encounter_id": "icestalker",
                        "display_name": "Icestalker",
                        "member_ids": ["icestalker"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = enrich_reference_entries_with_locations(
        (_entry("Icestalker"),),
        tmp_path,
    )[0]

    assert result.related == ("Icestalker — Frostvault",)


def test_already_qualified_related_name_is_left_alone(tmp_path: Path):
    result = enrich_reference_entries_with_locations(
        (_entry("Garvin the Tracker — Lep Seclusa"),),
        tmp_path,
    )[0]

    assert result.related == ("Garvin the Tracker — Lep Seclusa",)
