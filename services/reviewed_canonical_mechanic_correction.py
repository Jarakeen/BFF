from __future__ import annotations

"""Guarded corrections for already-reviewed canonical encounter mechanics.

The normal encounter persistence writer is intentionally create-only/idempotent
and rejects changed payloads.  This module exists for the narrower case where a
reviewed canonical fact remains valid but one explicit semantic field needs a
source-backed correction.  It never creates encounters or facts and it refuses
ambiguous or drifted targets.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class CanonicalMechanicCorrection:
    encounter_id: str
    mechanic_name: str
    expected_review_status: str
    expected_fields: tuple[tuple[str, object], ...]
    replacement_fields: tuple[tuple[str, object], ...]
    rationale: str


@dataclass(frozen=True)
class CanonicalMechanicCorrectionResult:
    encounter_id: str
    mechanic_name: str
    fact_id: int
    fact_key: str
    changed: bool
    payload_json: str


HIATH_ROLL_DODGE_OWNERSHIP = CanonicalMechanicCorrection(
    encounter_id="hiath_the_battlemaster",
    mechanic_name="Roll Dodge",
    expected_review_status="reviewed_single_source",
    expected_fields=(
        ("name", "Roll Dodge"),
        ("mechanic_type", "movement"),
        ("requires_movement", True),
        (
            "description",
            "Hiath can perform a roll dodge to avoid incoming damage.",
        ),
    ),
    replacement_fields=(("requirement_subjects", {"movement": "boss"}),),
    rationale=(
        "UESP explicitly describes Hiath as the actor performing Roll Dodge; "
        "the movement flag describes boss behavior, not a player movement demand."
    ),
)


def _target_row(
    connection: sqlite3.Connection,
    correction: CanonicalMechanicCorrection,
) -> tuple[int, str, str, str]:
    rows = connection.execute(
        """
        SELECT id, fact_key, payload_json, review_status
        FROM encounter_canonical_fact
        WHERE encounter_id = ?
          AND fact_type = 'mechanic_detail'
        ORDER BY id
        """,
        (correction.encounter_id,),
    ).fetchall()

    matches: list[tuple[int, str, str, str]] = []
    for row in rows:
        try:
            payload = json.loads(str(row[2]))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Invalid canonical mechanic payload for {correction.encounter_id}:{row[1]}"
            ) from exc
        if isinstance(payload, dict) and str(payload.get("name") or "") == correction.mechanic_name:
            matches.append((int(row[0]), str(row[1]), str(row[2]), str(row[3])))

    if len(matches) != 1:
        raise RuntimeError(
            "Canonical mechanic correction requires exactly one target: "
            f"{correction.encounter_id}:{correction.mechanic_name} | found={len(matches)}"
        )
    return matches[0]


def inspect_canonical_mechanic_correction(
    connection: sqlite3.Connection,
    correction: CanonicalMechanicCorrection,
) -> CanonicalMechanicCorrectionResult:
    fact_id, fact_key, payload_json, review_status = _target_row(connection, correction)
    if review_status != correction.expected_review_status:
        raise RuntimeError(
            "Canonical mechanic correction review status mismatch: "
            f"expected={correction.expected_review_status!r} actual={review_status!r}"
        )

    payload = json.loads(payload_json)
    if not isinstance(payload, dict):
        raise RuntimeError("Canonical mechanic correction target payload is not an object")

    for key, expected in correction.expected_fields:
        actual = payload.get(key)
        if actual != expected:
            raise RuntimeError(
                "Canonical mechanic correction precondition failed: "
                f"{correction.encounter_id}:{correction.mechanic_name}:{key} "
                f"expected={expected!r} actual={actual!r}"
            )

    replacement = dict(correction.replacement_fields)
    already_applied = all(payload.get(key) == value for key, value in replacement.items())
    if not already_applied:
        # Refuse an existing semantic value that differs from the reviewed
        # correction. Missing fields are safe because these corrections enrich
        # previously reviewed payloads rather than overwrite competing truth.
        for key, value in replacement.items():
            if key in payload and payload[key] != value:
                raise RuntimeError(
                    "Canonical mechanic correction conflicts with existing semantic value: "
                    f"{correction.encounter_id}:{correction.mechanic_name}:{key} "
                    f"existing={payload[key]!r} correction={value!r}"
                )

    corrected = dict(payload)
    corrected.update(replacement)
    corrected_json = json.dumps(corrected, ensure_ascii=False, sort_keys=True)
    return CanonicalMechanicCorrectionResult(
        encounter_id=correction.encounter_id,
        mechanic_name=correction.mechanic_name,
        fact_id=fact_id,
        fact_key=fact_key,
        changed=not already_applied,
        payload_json=corrected_json,
    )


def apply_canonical_mechanic_correction(
    connection: sqlite3.Connection,
    correction: CanonicalMechanicCorrection,
) -> CanonicalMechanicCorrectionResult:
    result = inspect_canonical_mechanic_correction(connection, correction)
    if not result.changed:
        return result

    cursor = connection.execute(
        """
        UPDATE encounter_canonical_fact
        SET payload_json = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ? AND encounter_id = ? AND fact_type = 'mechanic_detail'
        """,
        (result.payload_json, result.fact_id, correction.encounter_id),
    )
    if cursor.rowcount != 1:
        raise RuntimeError(
            "Canonical mechanic correction did not update exactly one fact: "
            f"{correction.encounter_id}:{correction.mechanic_name}"
        )

    verified = inspect_canonical_mechanic_correction(connection, correction)
    if verified.changed:
        raise RuntimeError(
            "Canonical mechanic correction post-write verification failed: "
            f"{correction.encounter_id}:{correction.mechanic_name}"
        )
    return CanonicalMechanicCorrectionResult(
        encounter_id=verified.encounter_id,
        mechanic_name=verified.mechanic_name,
        fact_id=verified.fact_id,
        fact_key=verified.fact_key,
        changed=True,
        payload_json=verified.payload_json,
    )


def inspect_canonical_mechanic_correction_file(
    database_path: Path,
    correction: CanonicalMechanicCorrection,
) -> CanonicalMechanicCorrectionResult:
    connection = sqlite3.connect(Path(database_path))
    try:
        return inspect_canonical_mechanic_correction(connection, correction)
    finally:
        connection.close()
