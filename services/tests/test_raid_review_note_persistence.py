from services.raid_section_state_service import RaidSectionStateService


def test_review_note_upserts_per_plan_attempt(tmp_path):
    service = RaidSectionStateService(tmp_path / "raid_section_state.json")

    first = service.save_review_note(
        plan_id="plan-1",
        trial_id="Rockgrove",
        plan_name="Monday Prog",
        attempt=3,
        notes="First draft",
    )
    second = service.save_review_note(
        plan_id="plan-1",
        trial_id="Rockgrove",
        plan_name="Monday Prog",
        attempt=3,
        notes="Updated note",
    )

    assert first is not None
    assert second is not None
    rows = service.review_notes()
    assert len(rows) == 1
    assert rows[0]["notes"] == "Updated note"
    assert rows[0]["trial_id"] == "Rockgrove"
    assert rows[0]["attempt"] == 3
