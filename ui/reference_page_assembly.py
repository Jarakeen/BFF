from __future__ import annotations

"""Final presentation assembly for the Combat Reference page.

This stage may add catalog entries and trivia/provenance context, but it remains
strictly UI-facing. It must not be imported by canonical mechanics/runtime code.
"""

from dataclasses import replace
from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from ui.eso_text_cleanup import strip_eso_color_markup
from ui.reference_catalog_entries import build_player_catalog_reference_entries
from ui.reference_data_model import ReferenceEntry
from ui.reference_locations import enrich_reference_entries_with_locations
from ui.reference_version_history import enrich_reference_entries_with_version_history


def _strip_entry_color_markup(entry: ReferenceEntry) -> ReferenceEntry:
    """Remove ESO inline color tokens at the final Reference presentation edge."""

    return replace(
        entry,
        name=strip_eso_color_markup(entry.name),
        entry_type=strip_eso_color_markup(entry.entry_type),
        source_scope=strip_eso_color_markup(entry.source_scope),
        tags=tuple(strip_eso_color_markup(value) for value in entry.tags),
        summary=strip_eso_color_markup(entry.summary),
        details=tuple(
            (strip_eso_color_markup(label), strip_eso_color_markup(value))
            for label, value in entry.details
        ),
        related=tuple(strip_eso_color_markup(value) for value in entry.related),
        death_note=strip_eso_color_markup(entry.death_note),
        field_note=strip_eso_color_markup(entry.field_note),
        used_by=tuple(strip_eso_color_markup(value) for value in entry.used_by),
        evidence=tuple(strip_eso_color_markup(value) for value in entry.evidence),
        mitigation_note=strip_eso_color_markup(entry.mitigation_note),
    )


def finalize_reference_entries(
    entries: Iterable[ReferenceEntry],
    *,
    data_root: Path | None = None,
    database_path: Path | None = None,
) -> tuple[ReferenceEntry, ...]:
    root = Path(data_root or get_data_dir())
    database = Path(database_path or (root / "eso.db"))

    result = (
        *tuple(entries),
        *build_player_catalog_reference_entries(database),
    )
    result = enrich_reference_entries_with_locations(result, root)
    result = enrich_reference_entries_with_version_history(result, root)
    return tuple(_strip_entry_color_markup(entry) for entry in result)


__all__ = ["finalize_reference_entries"]
