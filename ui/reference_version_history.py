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


def _detail_value(entry: ReferenceEntry, label: str) -> str:
    wanted = _normalize(label)
    for current_label, value in entry.details:
        if _normalize(current_label) == wanted:
            return str(value or "").strip()
    return ""


def _row_matches_entry(row: dict, entry: ReferenceEntry) -> bool:
    if _normalize(row.get("entity_type")) != _normalize(entry.entry_type):
        return False

    row_name = _normalize(row.get("name"))
    display_name = _normalize(entry.name)
    current_name = _normalize(_detail_value(entry, "Current name"))
    if not row_name or row_name not in {display_name, current_name}:
        return False

    context = _normalize(row.get("context"))
    if not context:
        return True
    skill_line = _normalize(_detail_value(entry, "Skill line"))
    return context == skill_line


def enrich_reference_entries_with_version_history(
    entries: Iterable[ReferenceEntry],
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Append reviewed trivia/history to matching Reference entries.

    Matching is deliberately presentation-oriented. Gear/CP rows can match by
    display name. Skills/passives can use their current ability name plus optional
    ``context`` (normally the skill line) so common names do not collide.
    Historical rows are never promoted into canonical mechanics data.
    """

    root = Path(data_root or get_data_dir())
    history_rows = _load_rows(root)

    result: list[ReferenceEntry] = []
    for entry in entries:
        rows = tuple(row for row in history_rows if _row_matches_entry(row, entry))
        if not rows:
            result.append(entry)
            continue

        lines = tuple(line for row in rows if (line := _event_line(row)))
        if not lines:
            result.append(entry)
            continue

        source_lines: list[str] = []
        for row in rows:
            source = str(row.get("source") or "").strip()
            source_url = str(row.get("source_url") or "").strip()
            if source:
                source_lines.append(f"History source: {source}")
            if source_url:
                source_lines.append(f"History source URL: {source_url}")

        evidence = tuple(
            dict.fromkeys(
                (
                    *entry.evidence,
                    *source_lines,
                )
            )
        )
        details = tuple(
            item for item in entry.details if item[0] != "History / Legacy"
        ) + (("History / Legacy", "\n".join(lines)),)
        result.append(replace(entry, details=details, evidence=evidence))

    return tuple(result)


__all__ = ["enrich_reference_entries_with_version_history"]
