from __future__ import annotations

"""Import source-declared boss encounter structure without inferred mechanics.

This layer deliberately writes only literal/source-backed encounter structure:
health, abilities, explicit phases, dialogue, and raw source sections. It does
not classify mechanics, infer behavior, or write encounter_mechanic,
encounter_strategy, or encounter_canonical_fact rows.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any


READY = "ready"
MISSING_ENCOUNTER = "missing_encounter"
IDENTITY_CONFLICT = "identity_conflict"
INVALID_SOURCE = "invalid_source"
DUPLICATE_ABILITY = "duplicate_ability"
BLOCKING_STATUSES = {
    MISSING_ENCOUNTER,
    IDENTITY_CONFLICT,
    INVALID_SOURCE,
    DUPLICATE_ABILITY,
}


@dataclass(frozen=True)
class BossStructuralCandidate:
    source_path: Path
    encounter_id: str
    encounter_name: str
    status: str
    reason: str
    ability_count: int = 0
    phase_count: int = 0
    dialogue_count: int = 0


@dataclass(frozen=True)
class BossStructuralAudit:
    candidates: tuple[BossStructuralCandidate, ...]

    @property
    def ready(self) -> tuple[BossStructuralCandidate, ...]:
        return tuple(row for row in self.candidates if row.status == READY)

    @property
    def blocked(self) -> tuple[BossStructuralCandidate, ...]:
        return tuple(row for row in self.candidates if row.status in BLOCKING_STATUSES)

    @property
    def ability_count(self) -> int:
        return sum(row.ability_count for row in self.ready)

    @property
    def phase_count(self) -> int:
        return sum(row.phase_count for row in self.ready)

    @property
    def dialogue_count(self) -> int:
        return sum(row.dialogue_count for row in self.ready)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _load_source(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("boss source must be a JSON object")
    if not str(payload.get("id") or "").strip():
        raise ValueError("boss source has no id")
    if not str(payload.get("name") or "").strip():
        raise ValueError("boss source has no name")
    return payload


def _source_meta(payload: dict[str, Any]) -> tuple[str, str]:
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    return (
        str(source.get("url") or "").strip(),
        str(source.get("revision_id") or "").strip(),
    )


def _ability_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("abilities")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _phase_rows(payload: dict[str, Any]) -> list[Any]:
    rows = payload.get("phases")
    return rows if isinstance(rows, list) else []


def _dialogue_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("dialogue")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _classify_source(
    connection: sqlite3.Connection,
    path: Path,
    payload: dict[str, Any],
) -> BossStructuralCandidate:
    encounter_id = str(payload.get("id") or "").strip()
    encounter_name = str(payload.get("name") or "").strip()

    if not _table_exists(connection, "encounter"):
        return BossStructuralCandidate(
            path,
            encounter_id,
            encounter_name,
            MISSING_ENCOUNTER,
            "canonical encounter table does not exist",
        )

    existing = connection.execute(
        "SELECT name FROM encounter WHERE id=?",
        (encounter_id,),
    ).fetchone()
    if existing is None:
        return BossStructuralCandidate(
            path,
            encounter_id,
            encounter_name,
            MISSING_ENCOUNTER,
            "canonical encounter identity does not exist",
        )
    if str(existing[0] or "") != encounter_name:
        return BossStructuralCandidate(
            path,
            encounter_id,
            encounter_name,
            IDENTITY_CONFLICT,
            f"canonical encounter name differs: existing={existing[0]!r}",
        )

    abilities = _ability_rows(payload)
    names = [str(row.get("name") or "").strip() for row in abilities]
    nonempty = [name for name in names if name]
    if len(nonempty) != len(set(nonempty)):
        return BossStructuralCandidate(
            path,
            encounter_id,
            encounter_name,
            DUPLICATE_ABILITY,
            "source contains duplicate ability names for this encounter",
            ability_count=len(abilities),
            phase_count=len(_phase_rows(payload)),
            dialogue_count=len(_dialogue_rows(payload)),
        )

    return BossStructuralCandidate(
        path,
        encounter_id,
        encounter_name,
        READY,
        "source-backed structural rows can be imported without mechanic inference",
        ability_count=len(abilities),
        phase_count=len(_phase_rows(payload)),
        dialogue_count=len(_dialogue_rows(payload)),
    )


def audit_boss_structural_import(
    connection: sqlite3.Connection,
    source_dir: Path,
) -> BossStructuralAudit:
    candidates: list[BossStructuralCandidate] = []
    for path in sorted(Path(source_dir).glob("*.json")):
        try:
            payload = _load_source(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            candidates.append(
                BossStructuralCandidate(path, "", "", INVALID_SOURCE, str(exc))
            )
            continue
        candidates.append(_classify_source(connection, path, payload))
    return BossStructuralAudit(tuple(candidates))


def _replace_health(
    connection: sqlite3.Connection,
    encounter_id: str,
    payload: dict[str, Any],
) -> None:
    health = payload.get("health") if isinstance(payload.get("health"), dict) else {}
    connection.execute(
        """
        INSERT INTO encounter_health(encounter_id, normal, veteran, hardmode)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(encounter_id) DO UPDATE SET
            normal=excluded.normal,
            veteran=excluded.veteran,
            hardmode=excluded.hardmode
        """,
        (
            encounter_id,
            str(health.get("normal") or ""),
            str(health.get("veteran") or ""),
            str(health.get("hardmode") or ""),
        ),
    )


def _replace_abilities(
    connection: sqlite3.Connection,
    encounter_id: str,
    payload: dict[str, Any],
) -> dict[str, int]:
    source_url, revision = _source_meta(payload)
    connection.execute("DELETE FROM encounter_ability WHERE encounter_id=?", (encounter_id,))
    ids: dict[str, int] = {}
    for row in _ability_rows(payload):
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        cursor = connection.execute(
            """
            INSERT INTO encounter_ability(
                encounter_id, name, description, source_section,
                source_url, source_revision_id,
                interruptible, interrupt_note
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, '')
            """,
            (
                encounter_id,
                name,
                str(row.get("description") or ""),
                "Skills and Abilities",
                source_url,
                revision,
            ),
        )
        ids[name] = int(cursor.lastrowid)
    return ids


def _replace_phases(
    connection: sqlite3.Connection,
    encounter_id: str,
    payload: dict[str, Any],
) -> None:
    source_url, revision = _source_meta(payload)
    connection.execute("DELETE FROM encounter_phase WHERE encounter_id=?", (encounter_id,))
    for index, raw in enumerate(_phase_rows(payload), start=1):
        if isinstance(raw, dict):
            label = str(raw.get("label") or raw.get("name") or raw.get("phase") or "")
            threshold = str(raw.get("threshold") or "")
            description = str(raw.get("description") or "")
        else:
            label = f"Phase {index}"
            threshold = ""
            description = str(raw or "")
        connection.execute(
            """
            INSERT INTO encounter_phase(
                encounter_id, label, threshold, description,
                source_section, source_url, source_revision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                encounter_id,
                label,
                threshold,
                description,
                "Phases",
                source_url,
                revision,
            ),
        )


def _replace_dialogue(
    connection: sqlite3.Connection,
    encounter_id: str,
    payload: dict[str, Any],
    ability_ids: dict[str, int],
) -> None:
    source_url, revision = _source_meta(payload)
    connection.execute("DELETE FROM encounter_dialogue WHERE encounter_id=?", (encounter_id,))
    for row in _dialogue_rows(payload):
        line = str(row.get("line") or "").strip()
        if not line:
            continue
        ability = str(row.get("ability") or "").strip()
        connection.execute(
            """
            INSERT INTO encounter_dialogue(
                encounter_id, trigger, speaker, line, matched_ability_id,
                source_section, source_url, source_revision_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                encounter_id,
                str(row.get("trigger") or "Unspecified"),
                str(row.get("speaker") or ""),
                line,
                ability_ids.get(ability),
                "Dialogue",
                source_url,
                revision,
            ),
        )


def _replace_sections(
    connection: sqlite3.Connection,
    encounter_id: str,
    payload: dict[str, Any],
) -> None:
    source_url, revision = _source_meta(payload)
    sections = {
        "difficulty_notes": payload.get("difficulty_notes") or {},
        "notes": payload.get("notes") or [],
        "strategy_notes": payload.get("strategy_notes") or [],
        "related_npcs": payload.get("related_npcs") or [],
        "related_quests": payload.get("related_quests") or [],
    }
    for name, value in sections.items():
        connection.execute(
            """
            INSERT INTO encounter_section(
                encounter_id, section_name, payload_json,
                source_url, source_revision_id
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(encounter_id, section_name) DO UPDATE SET
                payload_json=excluded.payload_json,
                source_url=excluded.source_url,
                source_revision_id=excluded.source_revision_id
            """,
            (
                encounter_id,
                name,
                json.dumps(value, ensure_ascii=False, sort_keys=True),
                source_url,
                revision,
            ),
        )


def apply_boss_structural_import(
    connection: sqlite3.Connection,
    audit: BossStructuralAudit,
) -> tuple[int, int, int, int]:
    """Replace source-backed structural rows atomically for the audited corpus.

    Returns ``(bosses, abilities, phases, dialogue)``. No mechanic, strategy, or
    canonical-fact table is touched.
    """
    if audit.blocked:
        raise RuntimeError(
            f"Boss structural import has {len(audit.blocked)} blocking candidate(s); refusing batch write"
        )

    bosses = abilities = phases = dialogue = 0
    try:
        connection.execute("BEGIN")
        for candidate in audit.ready:
            payload = _load_source(candidate.source_path)
            _replace_health(connection, candidate.encounter_id, payload)
            ability_ids = _replace_abilities(connection, candidate.encounter_id, payload)
            _replace_phases(connection, candidate.encounter_id, payload)
            _replace_dialogue(connection, candidate.encounter_id, payload, ability_ids)
            _replace_sections(connection, candidate.encounter_id, payload)
            bosses += 1
            abilities += len(ability_ids)
            phases += candidate.phase_count
            dialogue += candidate.dialogue_count
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    return bosses, abilities, phases, dialogue
