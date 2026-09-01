from __future__ import annotations

"""Bootstrap one canonical encounter row from existing legacy or raw UESP records."""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sqlite3

from services.encounter_schema import ensure_encounter_schema


@dataclass(frozen=True)
class EncounterBootstrapPlan:
    encounter_id: str
    legacy_boss_id: str
    bootstrap_source: str
    source_record: str
    content_id: str
    name: str
    slug: str
    summary: str
    location: str
    species: str
    reaction: str
    source_url: str
    source_page_title: str
    source_revision_id: str
    retrieved_at: str
    source_license: str


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _canonical_id(value: str) -> str:
    return _slugify(value).replace("-", "_")


def _legacy_boss_rows(connection: sqlite3.Connection) -> list[tuple]:
    return connection.execute(
        """
        SELECT id, name, content_id, summary, location, species, reaction,
               source_url, source_title, revision_id, retrieved_at, license
        FROM bosses
        """
    ).fetchall()


def _resolve_legacy_boss_row(
    connection: sqlite3.Connection,
    selector: str,
) -> tuple | None:
    selector = selector.strip()
    if not selector:
        raise RuntimeError("Legacy boss selector is required")

    rows = _legacy_boss_rows(connection)

    exact_id = [row for row in rows if str(row[0]) == selector]
    if len(exact_id) == 1:
        return exact_id[0]

    exact_name = [row for row in rows if str(row[1]).casefold() == selector.casefold()]
    if len(exact_name) == 1:
        return exact_name[0]
    if len(exact_name) > 1:
        raise RuntimeError(
            f"Legacy boss selector is ambiguous by exact name: {selector!r}"
        )

    normalized_selector = _canonical_id(selector)
    normalized = [
        row
        for row in rows
        if _canonical_id(str(row[0])) == normalized_selector
        or _canonical_id(str(row[1])) == normalized_selector
    ]
    if len(normalized) == 1:
        return normalized[0]
    if len(normalized) > 1:
        choices = ", ".join(f"{row[0]!r} ({row[1]})" for row in normalized)
        raise RuntimeError(
            f"Legacy boss selector is ambiguous after normalization: {selector!r}; "
            f"matches: {choices}"
        )

    return None


def _raw_candidates(raw_bosses_dir: Path, selector: str) -> list[tuple[Path, dict]]:
    normalized_selector = _canonical_id(selector)
    matches: list[tuple[Path, dict]] = []
    if not raw_bosses_dir.is_dir():
        return matches

    for path in sorted(raw_bosses_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue

        raw_id = str(payload.get("id") or "").strip()
        name = str(payload.get("name") or "").strip()
        if (
            raw_id == selector
            or name.casefold() == selector.casefold()
            or _canonical_id(raw_id) == normalized_selector
            or _canonical_id(name) == normalized_selector
            or _canonical_id(path.stem) == normalized_selector
        ):
            matches.append((path, payload))

    return matches


def _resolve_raw_boss(
    raw_bosses_dir: Path,
    selector: str,
) -> tuple[Path, dict] | None:
    matches = _raw_candidates(raw_bosses_dir, selector)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        choices = ", ".join(path.name for path, _ in matches)
        raise RuntimeError(
            f"Raw UESP boss selector is ambiguous: {selector!r}; matches: {choices}"
        )
    return None


def _require_content(connection: sqlite3.Connection, content_id: str) -> None:
    content = connection.execute(
        "SELECT 1 FROM content WHERE id = ?",
        (content_id,),
    ).fetchone()
    if content is None:
        raise RuntimeError(f"Content row does not exist: {content_id!r}")


def _raw_source_value(payload: dict, *keys: str) -> str:
    source = payload.get("source")
    for key in keys:
        value = payload.get(key)
        if value not in (None, ""):
            return str(value)
        if isinstance(source, dict):
            value = source.get(key)
            if value not in (None, ""):
                return str(value)
    return ""


def build_encounter_bootstrap_plan(
    connection: sqlite3.Connection,
    boss_selector: str,
    *,
    raw_bosses_dir: Path | None = None,
    content_id: str | None = None,
) -> EncounterBootstrapPlan:
    row = _resolve_legacy_boss_row(connection, boss_selector)
    if row is not None:
        legacy_boss_id = str(row[0])
        name = str(row[1] or "")
        resolved_content_id = str(row[2] or "").strip()
        if not resolved_content_id:
            raise RuntimeError(f"Legacy boss {legacy_boss_id!r} has no content_id")
        if content_id and content_id != resolved_content_id:
            raise RuntimeError(
                f"Requested content {content_id!r} conflicts with legacy boss content "
                f"{resolved_content_id!r}"
            )
        _require_content(connection, resolved_content_id)

        return EncounterBootstrapPlan(
            encounter_id=_canonical_id(name or legacy_boss_id),
            legacy_boss_id=legacy_boss_id,
            bootstrap_source="legacy_db",
            source_record=legacy_boss_id,
            content_id=resolved_content_id,
            name=name,
            slug=_slugify(name or legacy_boss_id),
            summary=str(row[3] or ""),
            location=str(row[4] or ""),
            species=str(row[5] or ""),
            reaction=str(row[6] or ""),
            source_url=str(row[7] or ""),
            source_page_title=str(row[8] or ""),
            source_revision_id=str(row[9] or ""),
            retrieved_at=str(row[10] or ""),
            source_license=str(row[11] or ""),
        )

    if raw_bosses_dir is None:
        raise RuntimeError(f"Legacy boss row does not exist for selector: {boss_selector!r}")

    raw = _resolve_raw_boss(Path(raw_bosses_dir), boss_selector)
    if raw is None:
        raise RuntimeError(
            f"Boss does not exist in legacy DB or raw UESP boss JSON for selector: "
            f"{boss_selector!r}"
        )
    if not content_id:
        raise RuntimeError(
            "Raw UESP bootstrap requires an explicit content_id; refusing to infer "
            f"content for {boss_selector!r}"
        )

    path, payload = raw
    _require_content(connection, content_id)
    raw_id = str(payload.get("id") or path.stem).strip()
    name = str(payload.get("name") or raw_id).strip()
    source_page_title = _raw_source_value(payload, "page_title", "title", "source_title")
    source_url = _raw_source_value(payload, "url", "source_url")
    source_revision_id = _raw_source_value(
        payload, "revision_id", "source_revision_id", "revision"
    )
    retrieved_at = _raw_source_value(payload, "retrieved_at")
    source_license = _raw_source_value(payload, "license", "source_license")

    return EncounterBootstrapPlan(
        encounter_id=_canonical_id(name or raw_id),
        legacy_boss_id="",
        bootstrap_source="raw_uesp_json",
        source_record=str(path),
        content_id=content_id,
        name=name,
        slug=_slugify(name or raw_id),
        summary=str(payload.get("summary") or ""),
        location=str(payload.get("location") or ""),
        species=str(payload.get("species") or ""),
        reaction=str(payload.get("reaction") or ""),
        source_url=source_url,
        source_page_title=source_page_title,
        source_revision_id=source_revision_id,
        retrieved_at=retrieved_at,
        source_license=source_license,
    )


def validate_encounter_bootstrap(
    connection: sqlite3.Connection,
    plan: EncounterBootstrapPlan,
) -> str:
    existing = connection.execute(
        """
        SELECT content_id, name, slug, source_revision_id
        FROM encounter
        WHERE id = ?
        """,
        (plan.encounter_id,),
    ).fetchone()
    if existing is None:
        return "insert"

    expected = (
        plan.content_id,
        plan.name,
        plan.slug,
        plan.source_revision_id,
    )
    actual = tuple(str(value or "") for value in existing)
    if actual != expected:
        raise RuntimeError(
            f"Canonical encounter row conflicts with bootstrap plan: {plan.encounter_id!r}"
        )
    return "existing"


def apply_encounter_bootstrap(
    connection: sqlite3.Connection,
    plan: EncounterBootstrapPlan,
) -> str:
    ensure_encounter_schema(connection)
    status = validate_encounter_bootstrap(connection, plan)
    if status == "existing":
        return status

    connection.execute(
        """
        INSERT INTO encounter(
            id, content_id, name, slug, summary, location, species, reaction,
            source_url, source_page_title, source_revision_id,
            retrieved_at, source_license
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            plan.encounter_id,
            plan.content_id,
            plan.name,
            plan.slug,
            plan.summary,
            plan.location,
            plan.species,
            plan.reaction,
            plan.source_url,
            plan.source_page_title,
            plan.source_revision_id,
            plan.retrieved_at,
            plan.source_license,
        ),
    )
    return "inserted"
