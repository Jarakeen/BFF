from __future__ import annotations

"""Player-facing common names for Combat Reference entries.

These aliases are presentation/search vocabulary, not canonical mechanic identity.
They let raid callouts such as "bubbles" find the official mechanic entry without
renaming the underlying ESO mechanic or changing encounter/runtime authorities.
"""

from dataclasses import replace
import json
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from ui.reference_data_model import ReferenceEntry


def _load_alias_rows(data_root: Path) -> tuple[dict, ...]:
    path = Path(data_root) / "reference_common_names.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    rows = payload.get("entries", []) if isinstance(payload, dict) else []
    return tuple(row for row in rows if isinstance(row, dict))


def enrich_reference_entries_with_common_names(
    entries: Iterable[ReferenceEntry],
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Attach reviewed/player-confirmed common names to matching Reference entries."""

    root = Path(data_root or get_data_dir())
    aliases: dict[str, tuple[str, ...]] = {}
    provenance: dict[str, tuple[str, ...]] = {}

    for row in _load_alias_rows(root):
        entry_name = str(row.get("entry_name") or "").strip()
        raw_names = row.get("common_names", [])
        if not entry_name or not isinstance(raw_names, list):
            continue
        names = tuple(
            dict.fromkeys(
                str(value).strip()
                for value in raw_names
                if str(value).strip()
            )
        )
        if not names:
            continue
        identity = entry_name.casefold()
        aliases[identity] = names
        source = str(row.get("source") or "").strip().replace("_", " ").title()
        note = str(row.get("notes") or "").strip()
        evidence = []
        if source:
            evidence.append(f"Common-name source: {source}")
        if note:
            evidence.append(f"Common-name note: {note}")
        provenance[identity] = tuple(evidence)

    result = []
    for entry in entries:
        identity = entry.name.casefold()
        names = aliases.get(identity, ())
        if not names:
            result.append(entry)
            continue

        details = [item for item in entry.details if item[0] != "Common names"]
        details.append(("Common names", ", ".join(names)))
        result.append(
            replace(
                entry,
                details=tuple(details),
                evidence=tuple(dict.fromkeys((*entry.evidence, *provenance.get(identity, ())))),
            )
        )

    return tuple(result)


__all__ = ["enrich_reference_entries_with_common_names"]
