import json
from pathlib import Path

from ui.reference_data_model import ReferenceEntry
from ui.reference_mitigations import enrich_reference_entries_with_mitigations


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def _entry() -> ReferenceEntry:
    return ReferenceEntry(
        name="Rapid Deluge — Tideborn Taleria",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("ENCOUNTER",),
        summary="Rapid Deluge mechanic.",
        details=(("Common names", "Bubbles"),),
    )


def test_reviewed_mitigation_is_attached_and_searchable(tmp_path: Path):
    (tmp_path / "reference_mitigations.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "entries": [
                    {
                        "entry_name": "Rapid Deluge — Tideborn Taleria",
                        "mitigation": "Get in the water and swim before it detonates. Blocking will not save you.",
                        "source": "reviewed_encounter_evidence",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    entry = enrich_reference_entries_with_mitigations((_entry(),), tmp_path)[0]

    assert entry.mitigation_note == (
        "Get in the water and swim before it detonates. Blocking will not save you."
    )
    assert "blocking will not save you" in entry.search_text
    assert any("Reviewed Encounter Evidence" in item for item in entry.evidence)


def test_missing_mitigation_does_not_invent_guidance(tmp_path: Path):
    (tmp_path / "reference_mitigations.json").write_text(
        json.dumps({"schema_version": 1, "entries": []}),
        encoding="utf-8",
    )

    entry = enrich_reference_entries_with_mitigations((_entry(),), tmp_path)[0]

    assert entry.mitigation_note == ""


def test_mitigation_field_is_appended_without_shifting_existing_positional_fields():
    entry = ReferenceEntry(
        "Example",
        "Mechanic",
        "Trial",
        ("MECHANIC",),
        "summary",
        (("Authority", "test"),),
        ("Related",),
        "death",
        "field",
        ("Consumer",),
        ("Evidence",),
    )

    assert entry.used_by == ("Consumer",)
    assert entry.evidence == ("Evidence",)
    assert entry.mitigation_note == ""


def test_checked_in_dsr_mitigations_include_reef_guardian_survival_notes():
    acid = ReferenceEntry(
        name="Acid Reflux — Reef Guardian",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("ENCOUNTER",),
        summary="Acid Reflux mechanic.",
        details=(),
    )
    heart = ReferenceEntry(
        name="Heartburn — Reef Guardian",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("ENCOUNTER",),
        summary="Heartburn mechanic.",
        details=(),
    )

    acid_result, heart_result = enrich_reference_entries_with_mitigations((acid, heart), DATA)

    assert "taunt target" in acid_result.mitigation_note.casefold()
    assert "acid pools" in acid_result.mitigation_note.casefold()
    assert "60-second timeout" in heart_result.mitigation_note.casefold()
    assert "wipes the group" in heart_result.mitigation_note.casefold()
