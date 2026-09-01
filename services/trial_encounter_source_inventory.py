from __future__ import annotations

"""Read-only source inventory for recovering canonical trial encounters.

This module deliberately does not import, crawl, or mutate data.  It answers a
smaller question first: which local source layers already know about each
expected encounter?
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Iterable


@dataclass(frozen=True)
class TrialEncounterSourceRow:
    expected_name: str
    raw_boss_files: tuple[str, ...]
    legacy_boss_ids: tuple[str, ...]
    canonical_encounter_ids: tuple[str, ...]
    evidence_packets: tuple[str, ...]
    has_curated_strategy: bool


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(connection, table):
        return set()
    return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")')}


def _normal(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def _scan_raw_bosses(raw_boss_dir: Path, expected_name: str) -> tuple[str, ...]:
    target = _normal(expected_name)
    matches: list[str] = []
    if not raw_boss_dir.exists():
        return ()
    for path in sorted(raw_boss_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if _normal(payload.get("name")) == target:
            matches.append(path.name)
    return tuple(matches)


def _legacy_matches(connection: sqlite3.Connection, expected_name: str) -> tuple[str, ...]:
    if not _table_exists(connection, "bosses"):
        return ()
    cols = _columns(connection, "bosses")
    if not {"id", "name"}.issubset(cols):
        return ()
    rows = connection.execute(
        "SELECT id FROM bosses WHERE lower(trim(name)) = lower(trim(?)) ORDER BY id",
        (expected_name,),
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _canonical_matches(
    connection: sqlite3.Connection,
    *,
    content_id: str,
    expected_name: str,
) -> tuple[str, ...]:
    if not _table_exists(connection, "encounter"):
        return ()
    rows = connection.execute(
        """
        SELECT id
        FROM encounter
        WHERE content_id = ? AND lower(trim(name)) = lower(trim(?))
        ORDER BY id
        """,
        (content_id, expected_name),
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _packet_matches(packet_dir: Path, content_id: str, expected_name: str) -> tuple[str, ...]:
    target = _normal(expected_name)
    matches: list[str] = []
    if not packet_dir.exists():
        return ()
    for path in sorted(packet_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("content_id") or "").strip() != content_id:
            continue
        if _normal(payload.get("encounter_name")) == target:
            matches.append(path.name)
    return tuple(matches)


def build_trial_encounter_source_inventory(
    connection: sqlite3.Connection,
    *,
    content_id: str,
    expected_names: Iterable[str],
    raw_boss_dir: Path,
    packet_dir: Path,
    curated_strategy_names: Iterable[str] = (),
) -> list[TrialEncounterSourceRow]:
    curated = {_normal(name) for name in curated_strategy_names}
    rows: list[TrialEncounterSourceRow] = []
    for expected_name in expected_names:
        rows.append(
            TrialEncounterSourceRow(
                expected_name=expected_name,
                raw_boss_files=_scan_raw_bosses(raw_boss_dir, expected_name),
                legacy_boss_ids=_legacy_matches(connection, expected_name),
                canonical_encounter_ids=_canonical_matches(
                    connection,
                    content_id=content_id,
                    expected_name=expected_name,
                ),
                evidence_packets=_packet_matches(packet_dir, content_id, expected_name),
                has_curated_strategy=_normal(expected_name) in curated,
            )
        )
    return rows
