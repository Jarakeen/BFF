from __future__ import annotations

"""Presentation-only location labels for Reference Data related entries."""

from dataclasses import replace
import json
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from ui.reference_data_model import ReferenceEntry


def _reviewed_dungeon_content_lookup(data_root: Path) -> dict[str, str]:
    path = data_root / "dungeon_encounter_identity.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    rows = payload.get("encounters", []) if isinstance(payload, dict) else []
    lookup: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        content_name = str(row.get("content_name") or "").strip()
        display_name = str(row.get("display_name") or "").strip()
        if display_name and content_name:
            lookup.setdefault(display_name.casefold(), content_name)
    return lookup


def _boss_content_lookup(data_root: Path) -> dict[str, str]:
    """Map visible boss/encounter names to parent content names.

    Raw boss files are useful when available. Reviewed dungeon identities provide
    a fallback for legitimate progression encounters whose raw boss import is
    missing or incomplete. This remains display metadata only.
    """

    lookup = _reviewed_dungeon_content_lookup(data_root)
    root = data_root / "eso_info" / "bosses"
    for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        name = str(payload.get("name") or "").strip()
        content_name = str(payload.get("content_name") or "").strip()
        if name and content_name:
            lookup.setdefault(name.casefold(), content_name)
    return lookup


def _qualify(value: str, lookup: dict[str, str]) -> str:
    text = str(value or "").strip()
    if not text or " — " in text:
        return text
    content_name = lookup.get(text.casefold(), "")
    if not content_name or content_name.casefold() == text.casefold():
        return text
    return f"{text} — {content_name}"


def enrich_reference_entries_with_locations(
    entries: Iterable[ReferenceEntry],
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Append dungeon/trial content names to boss names shown under Related.

    Example: ``Garvin the Tracker`` becomes ``Garvin the Tracker — Lep Seclusa``.
    This is display context only. It does not modify encounter identity or mechanics.
    """

    lookup = _boss_content_lookup(Path(data_root or get_data_dir()))
    if not lookup:
        return tuple(entries)

    enriched = []
    for entry in entries:
        related = tuple(
            dict.fromkeys(_qualify(value, lookup) for value in entry.related if str(value or "").strip())
        )
        enriched.append(replace(entry, related=related))
    return tuple(enriched)
