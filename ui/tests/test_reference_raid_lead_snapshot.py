from ui.reference_data_model import ReferenceEntry
from ui.reference_data_page import _raid_lead_snapshot_html, _raid_lead_snapshot_rows


def _rapid_deluge() -> ReferenceEntry:
    return ReferenceEntry(
        name="Rapid Deluge — Tideborn Taleria",
        entry_type="Mechanic Evidence",
        source_scope="Trial",
        tags=("ENCOUNTER",),
        summary="Reviewed evidence for Rapid Deluge.",
        details=(
            ("Encounter", "Tideborn Taleria"),
            (
                "Evidence • Rapid Deluge Veteran Behavior",
                "Target Count: 5; Detonation Seconds Approx: 6; Radius Meters: 19; Swimming Mitigates Blast: Yes",
            ),
        ),
        mitigation_note="Get in the water and swim before it detonates. Blocking will not save you.",
    )


def test_raid_lead_snapshot_prioritizes_mechanic_behavior_over_provenance():
    rows = dict(_raid_lead_snapshot_rows(_rapid_deluge()))

    assert "Target Count: 5" in rows["What it does"]
    assert "Detonation Seconds Approx: 6" in rows["Duration / timing"]
    assert "Radius Meters: 19" in rows["Size / radius"]
    assert "Target Count: 5" in rows["Targets / kill risk"]
    assert rows["Comes from"] == "Tideborn Taleria"
    assert rows["How to mitigate"].startswith("Get in the water")


def test_raid_lead_snapshot_html_uses_scan_friendly_labels():
    rendered = _raid_lead_snapshot_html(_rapid_deluge())

    assert "<b>RAID LEAD SNAPSHOT</b>" in rendered
    assert "<b>What it does:</b>" in rendered
    assert "<b>Duration / timing:</b>" in rendered
    assert "<b>Size / radius:</b>" in rendered
    assert "<b>Targets / kill risk:</b>" in rendered
    assert "<b>Comes from:</b> Tideborn Taleria" in rendered
    assert "<b>How to mitigate:</b>" in rendered


def test_non_mechanic_reference_entries_do_not_get_raid_lead_snapshot():
    effect = ReferenceEntry(
        name="Major Courage",
        entry_type="Named Effect",
        source_scope="Global Combat",
        tags=("BUFF",),
        summary="Named effect.",
        details=(("Standard effect", "Adds Weapon and Spell Damage"),),
    )

    assert _raid_lead_snapshot_rows(effect) == ()
    assert _raid_lead_snapshot_html(effect) == ""
