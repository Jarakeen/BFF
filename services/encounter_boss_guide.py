from __future__ import annotations

"""Read-only boss-guide projection over persisted encounter structure.

The combat/evaluation ``EncounterDefinition`` intentionally stays small. This
module serves UI and reference-data consumers that need persisted identity,
health, named abilities, and explicit phases without teaching those consumers to
query SQLite directly or invent missing encounter semantics.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3


class EncounterBossGuideError(RuntimeError):
    """Persisted boss-guide data is missing, malformed, or ambiguous."""


class EncounterBossGuideNotFound(LookupError):
    """The requested canonical encounter does not exist in persistence."""


@dataclass(frozen=True)
class BossGuideEncounterSummary:
    encounter_id: str
    content_id: str
    content_name: str
    name: str
    location: str


@dataclass(frozen=True)
class BossGuideAbility:
    ability_id: int
    name: str
    description: str
    interruptible: bool | None
    interrupt_note: str
    source_section: str
    source_url: str
    source_revision_id: str


@dataclass(frozen=True)
class BossGuidePhase:
    phase_id: int
    label: str
    threshold: str
    description: str
    source_section: str
    source_url: str
    source_revision_id: str


@dataclass(frozen=True)
class EncounterBossGuide:
    encounter_id: str
    content_id: str
    content_name: str
    name: str
    summary: str
    location: str
    species: str
    reaction: str
    health_record_present: bool
    health: tuple[tuple[str, str], ...]
    abilities: tuple[BossGuideAbility, ...]
    phases: tuple[BossGuidePhase, ...]
    source_url: str
    source_page_title: str
    source_revision_id: str
    retrieved_at: str
    source_license: str


_REQUIRED_TABLES = {
    "content",
    "encounter",
    "encounter_health",
    "encounter_ability",
    "encounter_phase",
}


def _table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    return bool(int(value))


class EncounterBossGuideService:
    """Project persisted structural encounter truth for guide/reference consumers."""

    def __init__(self, database: Path) -> None:
        self.database = Path(database)

    def _connect(self) -> sqlite3.Connection:
        if not self.database.exists():
            raise EncounterBossGuideError(
                f"Encounter database does not exist: {self.database}"
            )
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        missing = sorted(_REQUIRED_TABLES - _table_names(connection))
        if missing:
            connection.close()
            raise EncounterBossGuideError(
                "Encounter database is missing required table(s): " + ", ".join(missing)
            )
        return connection

    def encounter_summaries(self) -> tuple[BossGuideEncounterSummary, ...]:
        """Return the light-weight persisted index used by boss/content selectors."""
        connection = self._connect()
        try:
            return tuple(
                BossGuideEncounterSummary(
                    encounter_id=str(row["id"]),
                    content_id=str(row["content_id"]),
                    content_name=str(row["content_name"] or ""),
                    name=str(row["name"] or ""),
                    location=str(row["location"] or ""),
                )
                for row in connection.execute(
                    """
                    SELECT e.id, e.content_id, c.name AS content_name, e.name, e.location
                    FROM encounter AS e
                    JOIN content AS c ON c.id = e.content_id
                    ORDER BY c.name COLLATE NOCASE, e.name COLLATE NOCASE, e.id
                    """
                ).fetchall()
            )
        finally:
            connection.close()

    def encounter_ids(self) -> tuple[str, ...]:
        return tuple(row.encounter_id for row in self.encounter_summaries())

    def get(self, encounter_id: str) -> EncounterBossGuide:
        encounter_id = str(encounter_id or "").strip()
        if not encounter_id:
            raise ValueError("encounter_id must be a non-empty canonical id")

        connection = self._connect()
        try:
            encounter = connection.execute(
                """
                SELECT
                    e.id, e.content_id, c.name AS content_name, e.name, e.summary,
                    e.location, e.species, e.reaction, e.source_url,
                    e.source_page_title, e.source_revision_id, e.retrieved_at,
                    e.source_license
                FROM encounter AS e
                JOIN content AS c ON c.id = e.content_id
                WHERE e.id = ?
                """,
                (encounter_id,),
            ).fetchone()
            if encounter is None:
                raise EncounterBossGuideNotFound(
                    f"No persisted canonical encounter for id {encounter_id!r}"
                )

            health_row = connection.execute(
                """
                SELECT normal, veteran, hardmode
                FROM encounter_health
                WHERE encounter_id = ?
                """,
                (encounter_id,),
            ).fetchone()
            health_record_present = health_row is not None
            health = ()
            if health_row is not None:
                health = tuple(
                    (difficulty, str(health_row[difficulty] or ""))
                    for difficulty in ("normal", "veteran", "hardmode")
                    if health_row[difficulty]
                )

            abilities = tuple(
                BossGuideAbility(
                    ability_id=int(row["id"]),
                    name=str(row["name"] or ""),
                    description=str(row["description"] or ""),
                    interruptible=_optional_bool(row["interruptible"]),
                    interrupt_note=str(row["interrupt_note"] or ""),
                    source_section=str(row["source_section"] or ""),
                    source_url=str(row["source_url"] or ""),
                    source_revision_id=str(row["source_revision_id"] or ""),
                )
                for row in connection.execute(
                    """
                    SELECT id, name, description, interruptible, interrupt_note,
                           source_section, source_url, source_revision_id
                    FROM encounter_ability
                    WHERE encounter_id = ?
                    ORDER BY id
                    """,
                    (encounter_id,),
                ).fetchall()
            )

            phases = tuple(
                BossGuidePhase(
                    phase_id=int(row["id"]),
                    label=str(row["label"] or ""),
                    threshold=str(row["threshold"] or ""),
                    description=str(row["description"] or ""),
                    source_section=str(row["source_section"] or ""),
                    source_url=str(row["source_url"] or ""),
                    source_revision_id=str(row["source_revision_id"] or ""),
                )
                for row in connection.execute(
                    """
                    SELECT id, label, threshold, description, source_section,
                           source_url, source_revision_id
                    FROM encounter_phase
                    WHERE encounter_id = ?
                    ORDER BY id
                    """,
                    (encounter_id,),
                ).fetchall()
            )

            return EncounterBossGuide(
                encounter_id=str(encounter["id"]),
                content_id=str(encounter["content_id"]),
                content_name=str(encounter["content_name"] or ""),
                name=str(encounter["name"] or ""),
                summary=str(encounter["summary"] or ""),
                location=str(encounter["location"] or ""),
                species=str(encounter["species"] or ""),
                reaction=str(encounter["reaction"] or ""),
                health_record_present=health_record_present,
                health=health,
                abilities=abilities,
                phases=phases,
                source_url=str(encounter["source_url"] or ""),
                source_page_title=str(encounter["source_page_title"] or ""),
                source_revision_id=str(encounter["source_revision_id"] or ""),
                retrieved_at=str(encounter["retrieved_at"] or ""),
                source_license=str(encounter["source_license"] or ""),
            )
        finally:
            connection.close()
