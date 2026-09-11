from __future__ import annotations

"""Presentation-only version history for Reference Data entries.

History is flavor/provenance. It must never be imported by canonical mechanics,
rotation, optimization, or min/max services. Current canonical values remain the
sole mechanics authority.
"""

from dataclasses import replace
import json
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from ui.reference_data_model import ReferenceEntry


def _normalize(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _load_rows(data_root: Path) -> tuple[dict, ...]:
    path = data_root / "reference_version_history.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    rows = payload.get("events", []) if isinstance(payload, dict) else []
    return tuple(row for row in rows if isinstance(row, dict))


def _event_line(row: dict) -> str:
    update = str(row.get("update") or "").strip()
    year = str(row.get("year") or "").strip()
    change_type = str(row.get("change_type") or "").strip().replace("_", " ").title()
    summary = str(row.get("summary") or "").strip()

    heading = " • ".join(value for value in (update, year, change_type) if value)
    if heading and summary:
        return f"{heading}: {summary}"
    return heading or summary


def enrich_reference_entries_with_version_history(
    entries: Iterable[ReferenceEntry],
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Append reviewed trivia/history to matching Reference entries.

    Matching is deliberately display-oriented: entity type + current display name.
    Historical rows are never promoted into canonical mechanics data.
    """

    root = Path(data_root or get_data_dir())
    by_identity: dict[tuple[str, str], list[dict]] = {}
    for row in _load_rows(root):
        entity_type = _normalize(row.get("entity_type"))
        name = _normalize(row.get("name"))
        if not entity_type or not name:
            continue
        by_identity.setdefault((entity_type, name), []).append(row)

    result: list[ReferenceEntry] = []
    for entry in entries:
        rows = by_identity.get((_normalize(entry.entry_type), _normalize(entry.name)), ())
        if not rows:
            result.append(entry)
            continue

        lines = tuple(line for row in rows if (line := _event_line(row)))
        if not lines:
            result.append(entry)
            continue

        sources = tuple(
            dict.fromkeys(
                str(row.get("source") or "").strip()
                for row in rows
                if str(row.get("source") or "").strip()
            )
        )
        evidence = tuple(
            dict.fromkeys(
                (
                    *entry.evidence,
                    *(f"History source: {source}" for source in sources),
                )
            )
        )
        details = tuple(
            item for item in entry.details if item[0] != "History / Legacy"
        ) + (("History / Legacy", "\n".join(lines)),)
        result.append(replace(entry, details=details, evidence=evidence))

    return tuple(result)


__all__ = ["enrich_reference_entries_with_version_history"]
