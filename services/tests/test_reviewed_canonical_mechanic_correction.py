from __future__ import annotations

import json
import sqlite3

import pytest

from services.encounter_schema import ensure_encounter_schema
from services.reviewed_canonical_mechanic_correction import (
    HIATH_ROLL_DODGE_OWNERSHIP,
    apply_canonical_mechanic_correction,
    inspect_canonical_mechanic_correction,
)


def _database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    ensure_encounter_schema(connection)
    connection.execute(
        "INSERT INTO content(id, name, slug, content_type) VALUES (?, ?, ?, ?)",
        ("dragonstar_arena", "Dragonstar Arena", "dragonstar_arena", "arena"),
    )
    connection.execute(
        "INSERT INTO encounter(id, content_id, name, slug) VALUES (?, ?, ?, ?)",
        (
            "hiath_the_battlemaster",
            "dragonstar_arena",
            "Hiath the Battlemaster",
            "hiath_the_battlemaster",
        ),
    )
    return connection


def _roll_dodge_payload(**updates) -> dict:
    payload = {
        "name": "Roll Dodge",
        "mechanic_type": "movement",
        "damage_type": None,
        "description": "Hiath can perform a roll dodge to avoid incoming damage.",
        "target_count": None,
        "requires_movement": True,
        "requires_positioning": None,
        "requires_cleanse": None,
        "persistent_hazard": None,
        "failure_is_fatal": None,
        "interruptible": None,
    }
    payload.update(updates)
    return payload


def _insert_fact(
    connection: sqlite3.Connection,
    *,
    payload: dict | None = None,
    review_status: str = "reviewed_single_source",
    fact_key: str = "roll_dodge",
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO encounter_canonical_fact(
            encounter_id, canonical_kind, fact_type, fact_key,
            payload_json, review_status
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            "hiath_the_battlemaster",
            "mechanic_detail",
            "mechanic_detail",
            fact_key,
            json.dumps(payload or _roll_dodge_payload(), ensure_ascii=False, sort_keys=True),
            review_status,
        ),
    )
    return int(cursor.lastrowid)


def test_hiath_roll_dodge_correction_adds_explicit_boss_ownership() -> None:
    connection = _database()
    try:
        fact_id = _insert_fact(connection)
        before = inspect_canonical_mechanic_correction(
            connection, HIATH_ROLL_DODGE_OWNERSHIP
        )
        assert before.changed is True

        result = apply_canonical_mechanic_correction(
            connection, HIATH_ROLL_DODGE_OWNERSHIP
        )
        payload = json.loads(
            connection.execute(
                "SELECT payload_json FROM encounter_canonical_fact WHERE id=?",
                (fact_id,),
            ).fetchone()[0]
        )

        assert result.changed is True
        assert payload["requires_movement"] is True
        assert payload["requirement_subjects"] == {"movement": "boss"}
    finally:
        connection.close()


def test_hiath_roll_dodge_correction_is_idempotent() -> None:
    connection = _database()
    try:
        _insert_fact(connection)
        first = apply_canonical_mechanic_correction(
            connection, HIATH_ROLL_DODGE_OWNERSHIP
        )
        second = apply_canonical_mechanic_correction(
            connection, HIATH_ROLL_DODGE_OWNERSHIP
        )

        assert first.changed is True
        assert second.changed is False
        assert connection.execute(
            "SELECT COUNT(*) FROM encounter_canonical_fact"
        ).fetchone()[0] == 1
    finally:
        connection.close()


def test_hiath_roll_dodge_correction_refuses_drifted_source_semantics() -> None:
    connection = _database()
    try:
        _insert_fact(
            connection,
            payload=_roll_dodge_payload(description="Different reviewed description."),
        )

        with pytest.raises(RuntimeError, match="precondition failed"):
            inspect_canonical_mechanic_correction(
                connection, HIATH_ROLL_DODGE_OWNERSHIP
            )
    finally:
        connection.close()


def test_hiath_roll_dodge_correction_refuses_wrong_review_status() -> None:
    connection = _database()
    try:
        _insert_fact(connection, review_status="corroborated")

        with pytest.raises(RuntimeError, match="review status mismatch"):
            inspect_canonical_mechanic_correction(
                connection, HIATH_ROLL_DODGE_OWNERSHIP
            )
    finally:
        connection.close()


def test_hiath_roll_dodge_correction_refuses_competing_subject_truth() -> None:
    connection = _database()
    try:
        _insert_fact(
            connection,
            payload=_roll_dodge_payload(
                requirement_subjects={"movement": "player"}
            ),
        )

        with pytest.raises(RuntimeError, match="conflicts with existing semantic value"):
            inspect_canonical_mechanic_correction(
                connection, HIATH_ROLL_DODGE_OWNERSHIP
            )
    finally:
        connection.close()


def test_hiath_roll_dodge_correction_leaves_other_fact_and_evidence_untouched() -> None:
    connection = _database()
    try:
        fact_id = _insert_fact(connection)
        other_id = _insert_fact(
            connection,
            fact_key="agony",
            payload={
                "name": "Agony",
                "mechanic_type": "interrupt",
                "description": "Reviewed interrupt.",
                "interruptible": True,
            },
        )
        connection.execute(
            """
            INSERT INTO encounter_fact_evidence(
                canonical_fact_id, source_type, source_name, source_locator,
                source_revision, confidence, source_value_json, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fact_id,
                "uesp",
                "UESP",
                "https://en.uesp.net/wiki/Online:Hiath_the_Battlemaster",
                "123",
                "medium",
                json.dumps(_roll_dodge_payload(), sort_keys=True),
                "Original reviewed evidence.",
            ),
        )
        other_before = connection.execute(
            "SELECT payload_json, updated_at FROM encounter_canonical_fact WHERE id=?",
            (other_id,),
        ).fetchone()
        evidence_before = connection.execute(
            "SELECT source_value_json, notes FROM encounter_fact_evidence WHERE canonical_fact_id=?",
            (fact_id,),
        ).fetchone()

        apply_canonical_mechanic_correction(
            connection, HIATH_ROLL_DODGE_OWNERSHIP
        )

        other_after = connection.execute(
            "SELECT payload_json, updated_at FROM encounter_canonical_fact WHERE id=?",
            (other_id,),
        ).fetchone()
        evidence_after = connection.execute(
            "SELECT source_value_json, notes FROM encounter_fact_evidence WHERE canonical_fact_id=?",
            (fact_id,),
        ).fetchone()
        assert other_after == other_before
        assert evidence_after == evidence_before
    finally:
        connection.close()
