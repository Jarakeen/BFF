from __future__ import annotations

"""Read-only audit of inferred boss mechanics awaiting human review."""

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InferredMechanicReviewRow:
    source_path: Path
    content_id: str
    encounter_id: str
    encounter_name: str
    mechanic_name: str
    mechanic_type: str
    damage_type: str
    description: str
    target_count: int | None
    requires_movement: bool | None
    requires_positioning: bool | None
    requires_cleanse: bool | None
    persistent_hazard: bool | None
    failure_is_fatal: bool | None
    interruptible: bool | None
    source_url: str
    source_revision: str
    issues: tuple[str, ...]


@dataclass(frozen=True)
class InferredMechanicReviewAudit:
    source_files: int
    bosses_with_inferred_mechanics: int
    rows: tuple[InferredMechanicReviewRow, ...]
    failures: tuple[str, ...]

    @property
    def issue_rows(self) -> tuple[InferredMechanicReviewRow, ...]:
        return tuple(row for row in self.rows if row.issues)

    @property
    def mechanic_types(self) -> Counter[str]:
        return Counter(row.mechanic_type or "(missing)" for row in self.rows)

    @property
    def damage_types(self) -> Counter[str]:
        return Counter(row.damage_type or "(unspecified)" for row in self.rows)


def _bool_or_none(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _review_row(path: Path, payload: dict[str, Any], raw: dict[str, Any]) -> InferredMechanicReviewRow:
    issues: list[str] = []
    name = str(raw.get("name") or "").strip()
    mechanic_type = str(raw.get("mechanic_type") or "").strip()
    description = str(raw.get("description") or "").strip()
    if not name:
        issues.append("missing_name")
    if not mechanic_type:
        issues.append("missing_mechanic_type")
    if not description:
        issues.append("missing_description")

    target_count = raw.get("target_count")
    if target_count is not None and not isinstance(target_count, int):
        issues.append("invalid_target_count")
        target_count = None

    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    return InferredMechanicReviewRow(
        source_path=path,
        content_id=str(payload.get("content_id") or "").strip(),
        encounter_id=str(payload.get("id") or "").strip(),
        encounter_name=str(payload.get("name") or "").strip(),
        mechanic_name=name,
        mechanic_type=mechanic_type,
        damage_type=str(raw.get("damage_type") or "").strip(),
        description=description,
        target_count=target_count,
        requires_movement=_bool_or_none(raw.get("requires_movement")),
        requires_positioning=_bool_or_none(raw.get("requires_positioning")),
        requires_cleanse=_bool_or_none(raw.get("requires_cleanse")),
        persistent_hazard=_bool_or_none(raw.get("persistent_hazard")),
        failure_is_fatal=_bool_or_none(raw.get("failure_is_fatal")),
        interruptible=_bool_or_none(raw.get("interruptible")),
        source_url=str(source.get("url") or "").strip(),
        source_revision=str(source.get("revision_id") or "").strip(),
        issues=tuple(issues),
    )


def audit_inferred_boss_mechanics(source_dir: Path) -> InferredMechanicReviewAudit:
    source_dir = Path(source_dir)
    paths = tuple(sorted(source_dir.glob("*.json"))) if source_dir.exists() else ()
    rows: list[InferredMechanicReviewRow] = []
    failures: list[str] = []
    bosses: set[str] = set()

    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("boss source must be a JSON object")
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"{path}: {exc}")
            continue

        mechanics = payload.get("mechanics") if isinstance(payload.get("mechanics"), list) else []
        for raw in mechanics:
            if not isinstance(raw, dict):
                continue
            if str(raw.get("interpretation_status") or "").strip().casefold() != "inferred":
                continue
            row = _review_row(path, payload, raw)
            rows.append(row)
            bosses.add(row.encounter_id)

    return InferredMechanicReviewAudit(
        source_files=len(paths),
        bosses_with_inferred_mechanics=len(bosses),
        rows=tuple(rows),
        failures=tuple(failures),
    )
