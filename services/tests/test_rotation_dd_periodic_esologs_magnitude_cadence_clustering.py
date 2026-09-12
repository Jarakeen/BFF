from __future__ import annotations

import sqlite3

from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionService,
)


def _row(timestamp: float, event_index: int, amount: float) -> sqlite3.Row:
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE event(timestamp REAL, event_index INTEGER, amount REAL)")
    db.execute("INSERT INTO event VALUES (?, ?, ?)", (timestamp, event_index, amount))
    row = db.execute("SELECT * FROM event").fetchone()
    db.close()
    assert row is not None
    return row


def test_twenty_ms_mixed_amount_rows_are_one_ambiguous_occurrence_at_one_second_cadence() -> None:
    rows = [
        _row(1000.0, 1, 3661.0),
        _row(1020.0, 2, 3005.0),
        _row(2000.0, 3, 3200.0),
    ]

    sequences, ambiguous = (
        RotationDDPeriodicEsoLogsMagnitudeStateTransitionService._unambiguous_occurrence_sequences(
            rows,
            reviewed_interval_seconds=1.0,
        )
    )

    assert ambiguous == 1
    assert sequences == ((rows[2],),)


def test_rows_near_one_second_apart_remain_distinct_occurrences() -> None:
    rows = [
        _row(1000.0, 1, 3000.0),
        _row(1985.0, 2, 3100.0),
        _row(3010.0, 3, 3200.0),
    ]

    sequences, ambiguous = (
        RotationDDPeriodicEsoLogsMagnitudeStateTransitionService._unambiguous_occurrence_sequences(
            rows,
            reviewed_interval_seconds=1.0,
        )
    )

    assert ambiguous == 0
    assert sequences == ((rows[0], rows[1], rows[2]),)


def test_missing_reviewed_cadence_keeps_narrow_fallback_window() -> None:
    rows = [
        _row(1000.0, 1, 3000.0),
        _row(1020.0, 2, 3100.0),
    ]

    sequences, ambiguous = (
        RotationDDPeriodicEsoLogsMagnitudeStateTransitionService._unambiguous_occurrence_sequences(
            rows,
            reviewed_interval_seconds=None,
        )
    )

    assert ambiguous == 0
    assert sequences == ((rows[0], rows[1]),)
