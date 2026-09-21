from __future__ import annotations

from services.raid_review_attempt_summary_service import summarize_encounter_attempts
from services.raid_section_state_service import RaidRunAttempt


def _attempt(
    *,
    trial: str,
    encounter: str,
    attempt: int,
    duration: int | None,
) -> RaidRunAttempt:
    return RaidRunAttempt(
        plan_id="rg-pm",
        trial_id=trial,
        plan_name="Performance Mode RG",
        attempt=attempt,
        encounter_id=encounter,
        started_at=f"2026-09-21T01:0{attempt}:00+00:00",
        ended_at="" if duration is None else f"2026-09-21T01:0{attempt}:30+00:00",
        duration_seconds=duration,
    )


def test_encounter_summary_counts_all_pulls_but_times_only_completed_attempts() -> None:
    rows = summarize_encounter_attempts(
        (
            _attempt(trial="rockgrove", encounter="xalvakka", attempt=1, duration=90),
            _attempt(trial="rockgrove", encounter="xalvakka", attempt=2, duration=60),
            _attempt(trial="rockgrove", encounter="xalvakka", attempt=3, duration=None),
        )
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.pulls == 3
    assert row.timed_pulls == 2
    assert row.average_duration_seconds == 75
    assert row.best_duration_seconds == 60


def test_encounter_summary_counts_saved_notes_independently() -> None:
    rows = summarize_encounter_attempts(
        (
            _attempt(trial="rockgrove", encounter="xalvakka", attempt=1, duration=70),
            _attempt(trial="rockgrove", encounter="oaxiltso", attempt=2, duration=80),
        ),
        (
            {
                "trial_id": "rockgrove",
                "encounter_id": "xalvakka",
                "notes": "Good burn.",
            },
            {
                "trial_id": "rockgrove",
                "encounter_id": "xalvakka",
                "notes": "",
            },
        ),
    )

    by_encounter = {row.encounter_id: row for row in rows}
    assert by_encounter["xalvakka"].note_count == 1
    assert by_encounter["oaxiltso"].note_count == 0


def test_encounter_summary_keeps_trial_and_general_context_separate() -> None:
    rows = summarize_encounter_attempts(
        (
            _attempt(trial="rockgrove", encounter="", attempt=1, duration=30),
            _attempt(trial="rockgrove", encounter="xalvakka", attempt=2, duration=45),
            _attempt(trial="sunspire", encounter="xalvakka", attempt=3, duration=50),
        )
    )

    assert [(row.trial_id, row.encounter_id) for row in rows] == [
        ("rockgrove", ""),
        ("rockgrove", "xalvakka"),
        ("sunspire", "xalvakka"),
    ]
