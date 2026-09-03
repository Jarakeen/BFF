from __future__ import annotations

"""Explicit review decisions for single-source inferred boss mechanics.

UESP-derived mechanic classifications are useful evidence, but they are still
interpretations of source text. This module records an auditable decision per
mechanic without weakening the existing corroboration-based promotion policy.
Only accepted decisions may be converted into reviewed single-source plans.
"""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from services.boss_inferred_mechanic_review import audit_inferred_boss_mechanics

PENDING = "pending"
ACCEPTED = "accepted"
REJECTED = "rejected"
VALID_STATUSES = {PENDING, ACCEPTED, REJECTED}


@dataclass(frozen=True)
class InferredMechanicDecision:
    encounter_id: str
    mechanic_name: str
    status: str
    rationale: str = ""

    @property
    def key(self) -> tuple[str, str]:
        return (self.encounter_id, self.mechanic_name)


@dataclass(frozen=True)
class InferredMechanicDecisionAudit:
    decisions: tuple[InferredMechanicDecision, ...]
    expected_count: int
    missing: tuple[tuple[str, str], ...]
    extra: tuple[tuple[str, str], ...]
    duplicate_keys: tuple[tuple[str, str], ...]
    invalid_statuses: tuple[tuple[str, str, str], ...]
    accepted_without_rationale: tuple[tuple[str, str], ...]
    rejected_without_rationale: tuple[tuple[str, str], ...]

    @property
    def blocked(self) -> bool:
        return bool(
            self.missing
            or self.extra
            or self.duplicate_keys
            or self.invalid_statuses
            or self.accepted_without_rationale
            or self.rejected_without_rationale
        )


def build_pending_decision_manifest(source_dir: Path) -> dict[str, Any]:
    audit = audit_inferred_boss_mechanics(source_dir)
    decisions = [
        {
            "encounter_id": row.encounter_id,
            "mechanic_name": row.mechanic_name,
            "status": PENDING,
            "rationale": "",
        }
        for row in audit.rows
    ]
    return {
        "schema_version": 1,
        "purpose": "Explicit review decisions for single-source inferred boss mechanics",
        "decisions": decisions,
    }


def write_pending_decision_manifest(source_dir: Path, output_path: Path) -> Path:
    payload = build_pending_decision_manifest(source_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if output_path.exists() and output_path.read_text(encoding="utf-8") == text:
        return output_path
    output_path.write_text(text, encoding="utf-8")
    return output_path


def load_decisions(path: Path) -> tuple[InferredMechanicDecision, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("review manifest must be a JSON object")
    rows = payload.get("decisions")
    if not isinstance(rows, list):
        raise ValueError("review manifest has no decisions array")

    decisions: list[InferredMechanicDecision] = []
    for index, raw in enumerate(rows, start=1):
        if not isinstance(raw, dict):
            raise ValueError(f"review decision #{index} must be an object")
        encounter_id = str(raw.get("encounter_id") or "").strip()
        mechanic_name = str(raw.get("mechanic_name") or "").strip()
        status = str(raw.get("status") or "").strip().casefold()
        rationale = str(raw.get("rationale") or "").strip()
        if not encounter_id or not mechanic_name:
            raise ValueError(f"review decision #{index} is missing encounter_id/mechanic_name")
        decisions.append(
            InferredMechanicDecision(
                encounter_id=encounter_id,
                mechanic_name=mechanic_name,
                status=status,
                rationale=rationale,
            )
        )
    return tuple(decisions)


def audit_decisions(
    source_dir: Path,
    decisions: Iterable[InferredMechanicDecision],
) -> InferredMechanicDecisionAudit:
    source_audit = audit_inferred_boss_mechanics(source_dir)
    expected = {(row.encounter_id, row.mechanic_name) for row in source_audit.rows}
    decision_rows = tuple(decisions)

    counts: dict[tuple[str, str], int] = {}
    for row in decision_rows:
        counts[row.key] = counts.get(row.key, 0) + 1
    duplicate_keys = tuple(sorted(key for key, count in counts.items() if count > 1))

    actual = set(counts)
    missing = tuple(sorted(expected - actual))
    extra = tuple(sorted(actual - expected))
    invalid_statuses = tuple(
        sorted(
            (row.encounter_id, row.mechanic_name, row.status)
            for row in decision_rows
            if row.status not in VALID_STATUSES
        )
    )
    accepted_without_rationale = tuple(
        sorted(row.key for row in decision_rows if row.status == ACCEPTED and not row.rationale)
    )
    rejected_without_rationale = tuple(
        sorted(row.key for row in decision_rows if row.status == REJECTED and not row.rationale)
    )

    return InferredMechanicDecisionAudit(
        decisions=decision_rows,
        expected_count=len(expected),
        missing=missing,
        extra=extra,
        duplicate_keys=duplicate_keys,
        invalid_statuses=invalid_statuses,
        accepted_without_rationale=accepted_without_rationale,
        rejected_without_rationale=rejected_without_rationale,
    )
