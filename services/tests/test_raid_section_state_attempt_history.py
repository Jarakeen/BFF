from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from services.raid_section_state_service import RaidSectionStateService


def test_attempt_history_persists_without_review_notes(tmp_path, monkeypatch) -> None:
    service = RaidSectionStateService(tmp_path / "raid_section_state.json")
    times = iter(
        (
            "2026-09-21T01:00:00+00:00",
            "2026-09-21T01:00:00+00:00",
            "2026-09-21T01:01:15+00:00",
            "2026-09-21T01:01:15+00:00",
        )
    )
    monkeypatch.setattr("services.raid_section_state_service._now", lambda: next(times))

    started = service.start_pull("rg-pm", encounter_id="xalvakka")
    ended = service.end_attempt("rg-pm")

    assert started["attempt"] == 1
    assert started["encounter_id"] == "xalvakka"
    assert ended["active"] is False

    history = service.attempt_history("rg-pm")
    assert len(history) == 1
    assert history[0].attempt == 1
    assert history[0].encounter_id == "xalvakka"
    assert history[0].duration_seconds == 75
    assert service.review_notes() == ()


def test_attempt_history_filters_by_encounter(tmp_path, monkeypatch) -> None:
    service = RaidSectionStateService(tmp_path / "raid_section_state.json")
    timestamps = iter(
        (
            "2026-09-21T01:00:00+00:00",
            "2026-09-21T01:00:00+00:00",
            "2026-09-21T01:00:30+00:00",
            "2026-09-21T01:00:30+00:00",
            "2026-09-21T01:02:00+00:00",
            "2026-09-21T01:02:00+00:00",
            "2026-09-21T01:02:45+00:00",
            "2026-09-21T01:02:45+00:00",
        )
    )
    monkeypatch.setattr("services.raid_section_state_service._now", lambda: next(timestamps))

    service.start_pull("rg-pm", encounter_id="oaxiltso")
    service.end_attempt("rg-pm")
    service.start_pull("rg-pm", encounter_id="xalvakka")
    service.end_attempt("rg-pm")

    xalvakka = service.attempt_history("rg-pm", encounter_id="xalvakka")
    all_attempts = service.attempt_history("rg-pm")

    assert [row.attempt for row in all_attempts] == [2, 1]
    assert len(xalvakka) == 1
    assert xalvakka[0].attempt == 2
    assert xalvakka[0].duration_seconds == 45


def test_review_note_upsert_keeps_one_note_per_attempt_and_encounter(tmp_path) -> None:
    service = RaidSectionStateService(tmp_path / "raid_section_state.json")

    first = service.save_review_note(
        plan_id="rg-pm",
        trial_id="rockgrove",
        plan_name="Performance Mode RG",
        attempt=3,
        notes="First note",
        encounter_id="xalvakka",
    )
    second = service.save_review_note(
        plan_id="rg-pm",
        trial_id="rockgrove",
        plan_name="Performance Mode RG",
        attempt=3,
        notes="Updated note",
        encounter_id="xalvakka",
    )

    notes = service.review_notes()
    assert first is not None
    assert second is not None
    assert len(notes) == 1
    assert notes[0]["notes"] == "Updated note"
    assert notes[0]["encounter_id"] == "xalvakka"


def test_attempt_ledger_keeps_trial_and_plan_identity(tmp_path) -> None:
    service = RaidSectionStateService(tmp_path / "raid_section_state.json")

    service.start_pull(
        "rg-pm",
        encounter_id="xalvakka",
        trial_id="rockgrove",
        plan_name="Performance Mode RG",
    )

    row = service.all_attempt_history()[0]
    assert row.plan_id == "rg-pm"
    assert row.trial_id == "rockgrove"
    assert row.plan_name == "Performance Mode RG"
    assert row.encounter_id == "xalvakka"
