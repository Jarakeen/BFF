from services.raid_section_state_service import RaidSectionStateService


def test_review_note_upserts_per_plan_attempt(tmp_path):
    service = RaidSectionStateService(tmp_path / "raid_section_state.json")

    first = service.save_review_note(
        plan_id="plan-1",
        trial_id="Rockgrove",
        plan_name="Monday Prog",
        attempt=3,
        notes="First draft",
        started_at="2026-09-18T01:00:00+00:00",
    )
    second = service.save_review_note(
        plan_id="plan-1",
        trial_id="Rockgrove",
        plan_name="Monday Prog",
        attempt=3,
        notes="Updated note",
        started_at="2026-09-18T01:00:00+00:00",
        ended_at="2026-09-18T01:04:32+00:00",
    )

    assert first is not None
    assert second is not None
    rows = service.review_notes()
    assert len(rows) == 1
    assert rows[0]["notes"] == "Updated note"
    assert rows[0]["trial_id"] == "Rockgrove"
    assert rows[0]["attempt"] == 3
    assert rows[0]["started_at"] == "2026-09-18T01:00:00+00:00"
    assert rows[0]["ended_at"] == "2026-09-18T01:04:32+00:00"
    assert rows[0]["duration_seconds"] == 272
