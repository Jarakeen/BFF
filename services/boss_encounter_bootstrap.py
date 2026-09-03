from __future__ import annotations

"""Plan and apply canonical encounter identities for the tracked boss corpus.

This layer is deliberately identity-only. It trusts only source-declared boss ids
and content ids, refuses fuzzy content inference, and delegates row insertion to
the existing encounter bootstrap writer. Boss mechanics remain review evidence
and are not promoted here.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from services.encounter_bootstrap import EncounterBootstrapPlan, apply_encounter_bootstrap


READY = "ready"
EXISTING = "existing"
MISSING_CONTENT = "missing_content"
CONFLICT = "conflict"
INVALID_SOURCE = "invalid_source"
DUPLICATE_ID = "duplicate_id"
BLOCKING_STATUSES = {MISSING_CONTENT, CONFLICT, INVALID_SOURCE, DUPLICATE_ID}


@dataclass(frozen=True)
class BossEncounterBootstrapCandidate:
    source_path: Path
    encounter_id: str
    encounter_name: str
    content_id: str
    status: str
    reason: str
    plan: EncounterBootstrapPlan | None = None


@dataclass(frozen=True)
class BossEncounterBootstrapAudit:
    candidates: tuple[BossEncounterBootstrapCandidate, ...]

    @property
    def ready(self) -> tuple[BossEncounterBootstrapCandidate, ...]:
        return tuple(row for row in self.candidates if row.status == READY)

    @property
    def existing(self) -> tuple[BossEncounterBootstrapCandidate, ...]:
        return tuple(row for row in self.candidates if row.status == EXISTING)

    @property
    def blocked(self) -> tuple[BossEncounterBootstrapCandidate, ...]:
        return tuple(row for row in self.candidates if row.status in BLOCKING_STATUSES)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _source_value(payload: dict[str, Any], key: str) -> str:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    value = source.get(key)
    return str(value).strip() if value not in (None, "") else ""


def _plan_from_payload(path: Path, payload: dict[str, Any]) -> EncounterBootstrapPlan:
    encounter_id = str(payload.get("id") or "").strip()
    name = str(payload.get("name") or "").strip()
    content_id = str(payload.get("content_id") or "").strip()
    if not encounter_id:
        raise ValueError("source boss has no id")
    if not name:
        raise ValueError("source boss has no name")
    if not content_id:
        raise ValueError("source boss has no content_id")

    return EncounterBootstrapPlan(
        encounter_id=encounter_id,
        legacy_boss_id="",
        bootstrap_source="raw_uesp_json",
        source_record=str(path),
        content_id=content_id,
        name=name,
        slug=_slug(name),
        summary=str(payload.get("summary") or ""),
        location=str(payload.get("location") or ""),
        species=str(payload.get("species") or ""),
        reaction=str(payload.get("reaction") or ""),
        source_url=_source_value(payload, "url"),
        source_page_title=_source_value(payload, "page_title"),
        source_revision_id=_source_value(payload, "revision_id"),
        retrieved_at=_source_value(payload, "retrieved_at"),
        source_license=_source_value(payload, "license"),
    )


def _classify_plan(
    connection: sqlite3.Connection,
    path: Path,
    plan: EncounterBootstrapPlan,
) -> BossEncounterBootstrapCandidate:
    if not _table_exists(connection, "content"):
        return BossEncounterBootstrapCandidate(
            path, plan.encounter_id, plan.name, plan.content_id,
            MISSING_CONTENT, "canonical content table does not exist", plan,
        )

    content = connection.execute(
        "SELECT 1 FROM content WHERE id=?",
        (plan.content_id,),
    ).fetchone()
    if content is None:
        return BossEncounterBootstrapCandidate(
            path, plan.encounter_id, plan.name, plan.content_id,
            MISSING_CONTENT, "source-declared content_id has no canonical content row", plan,
        )

    # A real local database may predate the encounter schema. Dry-run audit must
    # remain read-only, so absence of the encounter table simply means there are
    # no existing canonical encounter identities yet. The apply path delegates to
    # apply_encounter_bootstrap(), which creates/extends the schema before insert.
    if not _table_exists(connection, "encounter"):
        return BossEncounterBootstrapCandidate(
            path, plan.encounter_id, plan.name, plan.content_id,
            READY, "encounter table is not present yet; identity can be inserted on apply", plan,
        )

    existing = connection.execute(
        "SELECT content_id, name, slug, source_revision_id FROM encounter WHERE id=?",
        (plan.encounter_id,),
    ).fetchone()
    if existing is None:
        return BossEncounterBootstrapCandidate(
            path, plan.encounter_id, plan.name, plan.content_id,
            READY, "canonical encounter identity can be inserted", plan,
        )

    actual = tuple(str(value or "") for value in existing)
    expected = (plan.content_id, plan.name, plan.slug, plan.source_revision_id)
    if actual == expected:
        return BossEncounterBootstrapCandidate(
            path, plan.encounter_id, plan.name, plan.content_id,
            EXISTING, "canonical encounter identity already matches source", plan,
        )

    return BossEncounterBootstrapCandidate(
        path, plan.encounter_id, plan.name, plan.content_id,
        CONFLICT,
        f"existing encounter row differs: existing={actual!r} expected={expected!r}",
        plan,
    )


def audit_boss_encounter_bootstrap(
    connection: sqlite3.Connection,
    source_dir: Path,
) -> BossEncounterBootstrapAudit:
    source_dir = Path(source_dir)
    candidates: list[BossEncounterBootstrapCandidate] = []
    seen: dict[str, BossEncounterBootstrapCandidate] = {}

    for path in sorted(source_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("source boss must be a JSON object")
            plan = _plan_from_payload(path, payload)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            candidates.append(
                BossEncounterBootstrapCandidate(
                    path, "", "", "", INVALID_SOURCE, str(exc), None
                )
            )
            continue

        row = _classify_plan(connection, path, plan)
        prior = seen.get(plan.encounter_id)
        if prior is not None:
            duplicate_reason = (
                f"encounter_id {plan.encounter_id!r} appears in both "
                f"{prior.source_path.name!r} and {path.name!r}"
            )
            candidates.append(
                BossEncounterBootstrapCandidate(
                    path, plan.encounter_id, plan.name, plan.content_id,
                    DUPLICATE_ID, duplicate_reason, plan,
                )
            )
            continue
        seen[plan.encounter_id] = row
        candidates.append(row)

    return BossEncounterBootstrapAudit(tuple(candidates))


def apply_boss_encounter_bootstrap(
    connection: sqlite3.Connection,
    audit: BossEncounterBootstrapAudit,
) -> tuple[int, int]:
    """Insert all ready encounter identities atomically.

    Refuses the entire batch when any identity/content/source blocker exists.
    Returns ``(inserted, existing)``. Mechanics/evidence are untouched.
    """
    if audit.blocked:
        raise RuntimeError(
            f"Boss encounter bootstrap has {len(audit.blocked)} blocking candidate(s); refusing batch write"
        )

    inserted = 0
    existing = 0
    try:
        connection.execute("BEGIN")
        for candidate in audit.candidates:
            if candidate.plan is None:
                continue
            status = apply_encounter_bootstrap(connection, candidate.plan)
            if status == "inserted":
                inserted += 1
            else:
                existing += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return inserted, existing
