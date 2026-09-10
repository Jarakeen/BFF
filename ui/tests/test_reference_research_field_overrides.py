from ui.reference_data_model import ReferenceEntry
from ui.reference_provider_relationships import enrich_reference_entries_with_reviewed_research


def _mechanic(name: str, *, movement: str = "Not modeled", hazard: str = "Not modeled") -> ReferenceEntry:
    return ReferenceEntry(
        name=name,
        entry_type="Mechanic",
        source_scope="Trial",
        tags=("MECHANIC",),
        summary="test",
        details=(("Requires movement", movement), ("Persistent hazard", hazard)),
    )


def test_reviewed_research_replaces_matching_unresolved_field_value():
    entry = enrich_reference_entries_with_reviewed_research((_mechanic("Deadstar — Xalvakka"),))[0]
    details = dict(entry.details)

    assert details["Requires movement"].startswith("Yes.")
    assert "reviewed research" in details["Requires movement"]
    assert "Not modeled" not in entry.detail_text()
    assert "Target pattern" in entry.detail_text()


def test_reviewed_research_does_not_overwrite_existing_canonical_value():
    entry = enrich_reference_entries_with_reviewed_research(
        (_mechanic("Split — Xalvakka", movement="Yes", hazard="Yes"),)
    )[0]
    details = dict(entry.details)

    assert details["Requires movement"] == "Yes"
    assert details["Persistent hazard"] == "Yes"
    assert "Research • Movement requirement" in entry.detail_text()
    assert "Research • Persistent hazard" in entry.detail_text()
