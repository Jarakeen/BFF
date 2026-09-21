from __future__ import annotations

"""Aggregate manual Live Raid attempt history for Raid Review.

This service summarizes only explicit user-owned pull bookkeeping. It does not infer
kills, success, wipes, boss health, or combat outcomes.
"""

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Mapping

from services.raid_section_state_service import RaidRunAttempt


def _clean(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True, slots=True)
class RaidReviewEncounterSummary:
    trial_id: str
    encounter_id: str
    pulls: int
    timed_pulls: int
    average_duration_seconds: int | None
    best_duration_seconds: int | None
    note_count: int


def summarize_encounter_attempts(
    attempts: Iterable[RaidRunAttempt],
    review_notes: Iterable[Mapping[str, object]] = (),
) -> tuple[RaidReviewEncounterSummary, ...]:
    grouped: dict[tuple[str, str], list[RaidRunAttempt]] = {}
    for attempt in attempts:
        key = (_clean(attempt.trial_id), _clean(attempt.encounter_id))
        grouped.setdefault(key, []).append(attempt)

    notes_by_key: dict[tuple[str, str], int] = {}
    for note in review_notes:
        if not _clean(note.get("notes")):
            continue
        key = (_clean(note.get("trial_id")), _clean(note.get("encounter_id")))
        notes_by_key[key] = notes_by_key.get(key, 0) + 1

    rows: list[RaidReviewEncounterSummary] = []
    for (trial_id, encounter_id), group in grouped.items():
        durations = [
            int(row.duration_seconds)
            for row in group
            if row.duration_seconds is not None
        ]
        rows.append(
            RaidReviewEncounterSummary(
                trial_id=trial_id,
                encounter_id=encounter_id,
                pulls=len(group),
                timed_pulls=len(durations),
                average_duration_seconds=(
                    int(round(mean(durations))) if durations else None
                ),
                best_duration_seconds=min(durations) if durations else None,
                note_count=notes_by_key.get((trial_id, encounter_id), 0),
            )
        )

    rows.sort(
        key=lambda row: (
            row.trial_id.casefold(),
            row.encounter_id.casefold(),
        )
    )
    return tuple(rows)


__all__ = [
    "RaidReviewEncounterSummary",
    "summarize_encounter_attempts",
]
