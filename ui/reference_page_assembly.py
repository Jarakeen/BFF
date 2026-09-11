from __future__ import annotations

"""Final presentation assembly for the Combat Reference page.

This stage may add catalog entries and trivia/provenance context, but it remains
strictly UI-facing. It must not be imported by canonical mechanics/runtime code.
"""

from pathlib import Path
from typing import Iterable

from engine.config import get_data_dir
from ui.reference_catalog_entries import build_player_catalog_reference_entries
from ui.reference_data_model import ReferenceEntry
from ui.reference_locations import enrich_reference_entries_with_locations
from ui.reference_version_history import enrich_reference_entries_with_version_history


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
    return tuple(result)


__all__ = ["finalize_reference_entries"]
