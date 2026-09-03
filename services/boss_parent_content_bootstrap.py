from __future__ import annotations

"""Plan missing canonical parent content required by the tracked boss corpus.

Boss records already declare stable content_id values. This module uses only
those declared ids, resolves them against tracked trial/dungeon/arena source
records by exact id, and never infers content from names or paths.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any


READY = "ready"
EXISTING = "existing"
MISSING_SOURCE = "missing_source"
AMBIGUOUS_SOURCE = "ambiguous_source"
INVALID_SOURCE = "invalid_source"
BLOCKING_STATUSES = {MISSING_SOURCE, AMBIGUOUS_SOURCE, INVALID_SOURCE}
CONTENT_FOLDERS = ("trials", "dungeons", "arenas")


@dataclass(frozen=True)
class BossParentContentCandidate:
    content_id: str
    status: str
    reason: str
    source_path: Path | None = None
    name: str = ""
    content_type: str = ""
    boss_count: int = 0


@dataclass(frozen=True)
class BossParentContentAudit:
    candidates: tuple[BossParentContentCandidate, ...]

    @property
    def ready(self) -> tuple[BossParentContentCandidate, ...]:
        return tuple(row for row in self.candidates if row.status == READY)

    @property
    def existing(self) -> tuple[BossParentContentCandidate, ...]:
        return tuple(row for row in self.candidates if row.status == EXISTING)

    @property
    def blocked(self) -> tuple[BossParentContentCandidate, ...]:
        return tuple(row for row in self.candidates if row.status in BLOCKING_STATUSES)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _boss_content_counts(boss_dir: Path) -> tuple[dict[str, int], list[str]]:
    counts: dict[str, int] = {}
    invalid: list[str] = []
    for path in sorted(Path(boss_dir).glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            invalid.append(path.name)
            continue
        if not isinstance(payload, dict):
            invalid.append(path.name)
            continue
        content_id = str(payload.get("content_id") or "").strip()
        if not content_id:
            invalid.append(path.name)
            continue
        counts[content_id] = counts.get(content_id, 0) + 1
    return counts, invalid


def _content_sources(content_root: Path, content_id: str) -> list[tuple[Path, dict[str, Any]]]:
    matches: list[tuple[Path, dict[str, Any]]] = []
    for folder in CONTENT_FOLDERS:
        path = Path(content_root) / folder / f"{content_id}.json"
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            matches.append((path, {}))
            continue
        if isinstance(payload, dict):
            matches.append((path, payload))
        else:
            matches.append((path, {}))
    return matches


def audit_boss_parent_content(
    connection: sqlite3.Connection,
    *,
    boss_dir: Path,
    content_root: Path,
) -> BossParentContentAudit:
    counts, invalid_bosses = _boss_content_counts(Path(boss_dir))
    if invalid_bosses:
        return BossParentContentAudit(
            tuple(
                BossParentContentCandidate(
                    content_id=f"invalid-boss-source:{name}",
                    status=INVALID_SOURCE,
                    reason="boss source is invalid or has no content_id",
                )
                for name in invalid_bosses
            )
        )

    existing_ids: set[str] = set()
    if _table_exists(connection, "content"):
        existing_ids = {
            str(row[0])
            for row in connection.execute("SELECT id FROM content").fetchall()
        }

    rows: list[BossParentContentCandidate] = []
    for content_id in sorted(counts):
        boss_count = counts[content_id]
        if content_id in existing_ids:
            rows.append(
                BossParentContentCandidate(
                    content_id=content_id,
                    status=EXISTING,
                    reason="canonical content row already exists",
                    boss_count=boss_count,
                )
            )
            continue

        matches = _content_sources(Path(content_root), content_id)
        if not matches:
            rows.append(
                BossParentContentCandidate(
                    content_id=content_id,
                    status=MISSING_SOURCE,
                    reason="no exact tracked trial/dungeon/arena source record exists",
                    boss_count=boss_count,
                )
            )
            continue
        if len(matches) > 1:
            rows.append(
                BossParentContentCandidate(
                    content_id=content_id,
                    status=AMBIGUOUS_SOURCE,
                    reason="content id appears in more than one tracked content folder",
                    boss_count=boss_count,
                )
            )
            continue

        path, payload = matches[0]
        source_id = str(payload.get("id") or "").strip()
        name = str(payload.get("name") or "").strip()
        content_type = str(payload.get("content_type") or "").strip()
        if source_id != content_id or not name or content_type not in CONTENT_FOLDERS and content_type not in {"trial", "dungeon", "arena"}:
            rows.append(
                BossParentContentCandidate(
                    content_id=content_id,
                    status=INVALID_SOURCE,
                    reason=(
                        "tracked content source is missing required identity/type fields "
                        f"or id does not match: {path}"
                    ),
                    source_path=path,
                    name=name,
                    content_type=content_type,
                    boss_count=boss_count,
                )
            )
            continue

        rows.append(
            BossParentContentCandidate(
                content_id=content_id,
                status=READY,
                reason="exact tracked content source can be imported",
                source_path=path,
                name=name,
                content_type=content_type,
                boss_count=boss_count,
            )
        )

    return BossParentContentAudit(tuple(rows))
