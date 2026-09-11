from __future__ import annotations

"""Short player-facing mitigation notes for Combat Reference entries.

These notes explain how to survive or handle a mechanic in practice. They are a
presentation layer over reviewed evidence and do not replace canonical encounter
mechanics, gameplay-policy authority, or detailed Field Notes.
"""

from dataclasses import replace
import json
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from ui.reference_data_model import ReferenceEntry


def _load_rows(data_root: Path) -> tuple[dict, ...]:
    root = Path(data_root)
    rows: list[dict] = []
    for path in sorted(root.glob("reference_mitigations*.json"), key=lambda item: item.name.casefold()):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        entries = payload.get("entries", []) if isinstance(payload, dict) else []
        rows.extend(row for row in entries if isinstance(row, dict))
    return tuple(rows)


def enrich_reference_entries_with_mitigations(
    entries: Iterable[ReferenceEntry],
    data_root: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    """Attach short reviewed mitigation guidance to matching entries.

    The Combat Reference page calls this as its final default-data stage. In that
    specific default-data path, the presentation-only catalog/history assembly is
    applied after mitigations. Explicit ``data_root`` callers (including focused
    tests and tools) receive mitigation enrichment only.
    """

    using_default_data = data_root is None
    root = Path(data_root or get_data_dir())
    mitigations: dict[str, str] = {}
    provenance: dict[str, tuple[str, ...]] = {}

    for row in _load_rows(root):
        entry_name = str(row.get("entry_name") or "").strip()
        mitigation = str(row.get("mitigation") or "").strip()
        if not entry_name or not mitigation:
            continue
        identity = entry_name.casefold()
        mitigations[identity] = mitigation

        source = str(row.get("source") or "").strip().replace("_", " ").title()
        note = str(row.get("notes") or "").strip()
        evidence = []
        if source:
            evidence.append(f"Mitigation source: {source}")
        if note:
            evidence.append(f"Mitigation note: {note}")
        provenance[identity] = tuple(evidence)

    result = []
    for entry in entries:
        identity = entry.name.casefold()
        mitigation = mitigations.get(identity, "")
        if not mitigation:
            result.append(entry)
            continue
        result.append(
            replace(
                entry,
                mitigation_note=mitigation,
                evidence=tuple(dict.fromkeys((*entry.evidence, *provenance.get(identity, ())))),
            )
        )

    enriched = tuple(result)
    if not using_default_data:
        return enriched

    # Keep catalog/history trivia at the UI boundary. Import lazily so focused
    # mitigation helpers remain independent of the larger Reference-page catalog.
    from ui.reference_page_assembly import finalize_reference_entries

    return finalize_reference_entries(enriched, data_root=root)


__all__ = ["enrich_reference_entries_with_mitigations"]
