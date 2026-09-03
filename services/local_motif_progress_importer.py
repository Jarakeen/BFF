from __future__ import annotations

"""Merge legacy motif completion into profile-aware canonical motif progress."""

from dataclasses import dataclass
import unicodedata

from services.learned_motif_service import LearnedMotifService
from services.local_motif_workbook_service import LocalMotifSnapshot


@dataclass(frozen=True)
class LocalMotifImportPreview:
    source_person: str
    target_profile: str
    sheet_rows: int
    checked_rows: int
    matched_motifs: int
    learnable_items: int
    unresolved_names: tuple[str, ...]
    ambiguous_names: tuple[str, ...]
    source_tabs: tuple[str, ...]


@dataclass(frozen=True)
class LocalMotifImportReport:
    source_person: str
    target_profile: str
    checked_rows: int
    matched_motifs: int
    learnable_items_marked: int
    unresolved_names: tuple[str, ...]
    ambiguous_names: tuple[str, ...]


class LocalMotifProgressImporter:
    """Resolve completed motif rows by motif number plus canonical style name.

    A checked legacy motif row represents a completed style. The canonical motif
    catalog stores the learnable full-style book and/or individual chapters, so
    every learnable item belonging to that uniquely resolved motif is marked
    learned for the same profile. Imports are merge-only and never clear data.
    """

    def __init__(self, service: LearnedMotifService) -> None:
        self.service = service

    @staticmethod
    def _normalized(value: str) -> str:
        text = unicodedata.normalize("NFKC", str(value or ""))
        return " ".join(text.split()).casefold()

    def _canonical_index(self) -> dict[int, dict[str, set[int]]]:
        if not self.service.available:
            return {}
        rows = self.service.connection.execute(
            """
            SELECT item_id, motif_number, style_name
            FROM learnable_motif
            WHERE style_name IS NOT NULL AND TRIM(style_name) <> ''
            ORDER BY motif_number, item_id
            """
        ).fetchall()
        index: dict[int, dict[str, set[int]]] = {}
        for row in rows:
            number = int(row["motif_number"])
            key = self._normalized(row["style_name"])
            if not key:
                continue
            index.setdefault(number, {}).setdefault(key, set()).add(int(row["item_id"]))
        return index

    def _analyze(self, snapshot: LocalMotifSnapshot):
        canonical = self._canonical_index()
        matched_motifs: set[tuple[int, str]] = set()
        item_ids: set[int] = set()
        unresolved: set[str] = set()
        ambiguous: set[str] = set()

        for row in snapshot.checked_rows:
            key = self._normalized(row.style_name)
            styles = canonical.get(int(row.motif_number), {})
            matches = styles.get(key)
            label = f"{row.motif_number}: {row.style_name}"
            if not matches:
                unresolved.add(label)
                continue

            # A motif number should map to one normalized style identity. If the
            # source name is somehow represented by multiple distinct canonical
            # style keys, refuse to guess instead of crossing styles.
            matching_keys = [style_key for style_key in styles if style_key == key]
            if len(matching_keys) != 1:
                ambiguous.add(label)
                continue

            matched_motifs.add((int(row.motif_number), key))
            item_ids.update(matches)

        return matched_motifs, item_ids, unresolved, ambiguous

    def preview_checked(self, snapshot: LocalMotifSnapshot, *, profile: str) -> LocalMotifImportPreview:
        matched, item_ids, unresolved, ambiguous = self._analyze(snapshot)
        return LocalMotifImportPreview(
            source_person=snapshot.person,
            target_profile=str(profile or "").strip(),
            sheet_rows=len(snapshot.rows),
            checked_rows=len(snapshot.checked_rows),
            matched_motifs=len(matched),
            learnable_items=len(item_ids),
            unresolved_names=tuple(sorted(unresolved, key=str.casefold)),
            ambiguous_names=tuple(sorted(ambiguous, key=str.casefold)),
            source_tabs=tuple(snapshot.source_tabs),
        )

    def import_checked(self, snapshot: LocalMotifSnapshot, *, profile: str) -> LocalMotifImportReport:
        target_profile = self.service.set_active_profile(profile)
        matched, item_ids, unresolved, ambiguous = self._analyze(snapshot)
        marked = 0
        if item_ids:
            marked = self.service.set_learned_batch({item_id: True for item_id in item_ids})
        return LocalMotifImportReport(
            source_person=snapshot.person,
            target_profile=target_profile,
            checked_rows=len(snapshot.checked_rows),
            matched_motifs=len(matched),
            learnable_items_marked=marked,
            unresolved_names=tuple(sorted(unresolved, key=str.casefold)),
            ambiguous_names=tuple(sorted(ambiguous, key=str.casefold)),
        )
