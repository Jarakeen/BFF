from __future__ import annotations

"""Bootstrap one canonical encounter row from existing legacy ESO records."""

from dataclasses import dataclass
import re
import sqlite3

from services.encounter_schema import ensure_encounter_schema


@dataclass(frozen=True)
class EncounterBootstrapPlan:
    encounter_id: str
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
    value = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return value


def build_encounter_bootstrap_plan(
    connection: sqlite3.Connection,
    boss_id: str,
) -> EncounterBootstrapPlan:
    row = connection.execute(
        """
        SELECT id, name, content_id, summary, location, species, reaction,
               source_url, source_title, revision_id, retrieved_at, license
        FROM bosses
        WHERE id = ?
        """,
        (boss_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Legacy boss row does not exist: {boss_id!r}")

    content_id = str(row[2] or "").strip()
    if not content_id:
        raise RuntimeError(f"Legacy boss {boss_id!r} has no content_id")

    content = connection.execute(
        "SELECT 1 FROM content WHERE id = ?",
        (content_id,),
    ).fetchone()
    if content is None:
        raise RuntimeError(
            f"Legacy boss {boss_id!r} references missing content {content_id!r}"
        )

    return EncounterBootstrapPlan(
        encounter_id=str(row[0]),
        content_id=content_id,
        name=str(row[1] or ""),
        slug=_slugify(str(row[1] or row[0])),
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
