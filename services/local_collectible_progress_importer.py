from __future__ import annotations

"""Exact-match standalone collectible ownership from legacy workbooks."""

from dataclasses import dataclass
import unicodedata

from services.local_collectible_workbook_service import LocalCollectibleSnapshot
from services.profiled_collectible_service import ProfiledCollectibleService


@dataclass(frozen=True)
class CollectibleProgressImportPreview:
    source_person: str
    target_profile: str
    sheet_rows: int
    checked_rows: int
    matched_collectibles: int
    unresolved_names: tuple[str, ...]
    ambiguous_names: tuple[str, ...]
    scanned_tabs: tuple[str, ...]


@dataclass(frozen=True)
class CollectibleProgressImportReport:
    source_person: str
    target_profile: str
    sheet_rows: int
    checked_rows: int
    matched_collectibles: int
    collectibles_marked_owned: int
    unresolved_names: tuple[str, ...]
    ambiguous_names: tuple[str, ...]
    scanned_tabs: tuple[str, ...]


class LocalCollectibleProgressImporter:
    """Merge checked collectible rows into one named profile without fuzzy guesses."""

    def __init__(self, collectible_progress: ProfiledCollectibleService) -> None:
        self.collectible_progress = collectible_progress

    @staticmethod
    def _normalized_name(value: str) -> str:
        text = unicodedata.normalize("NFKC", str(value or ""))
        return " ".join(text.split()).casefold()

    def _canonical_name_index(self) -> dict[str, list[int]]:
        rows = self.collectible_progress.connection.execute(
            """
            SELECT id, name
            FROM collectible
            WHERE name IS NOT NULL AND TRIM(name) <> ''
            ORDER BY id
            """
        ).fetchall()
        index: dict[str, list[int]] = {}
        for row in rows:
            key = self._normalized_name(row["name"])
            if key:
                index.setdefault(key, []).append(int(row["id"]))
        return index

    def _analyze(self, snapshot: LocalCollectibleSnapshot):
        canonical = self._canonical_name_index()
        matched_ids: set[int] = set()
        unresolved: set[str] = set()
        ambiguous: set[str] = set()

        for row in snapshot.checked_rows:
            matches = canonical.get(self._normalized_name(row.name), [])
            if not matches:
                unresolved.add(row.name)
                continue
            if len(matches) != 1:
                ambiguous.add(row.name)
                continue
            matched_ids.add(matches[0])
        return matched_ids, unresolved, ambiguous

    def preview_checked(self, snapshot: LocalCollectibleSnapshot, *, profile: str) -> CollectibleProgressImportPreview:
        matched_ids, unresolved, ambiguous = self._analyze(snapshot)
        return CollectibleProgressImportPreview(
            source_person=snapshot.person,
            target_profile=str(profile or "").strip(),
            sheet_rows=len(snapshot.rows),
            checked_rows=len(snapshot.checked_rows),
            matched_collectibles=len(matched_ids),
            unresolved_names=tuple(sorted(unresolved, key=str.casefold)),
            ambiguous_names=tuple(sorted(ambiguous, key=str.casefold)),
            scanned_tabs=tuple(snapshot.scanned_tabs),
        )

    def import_checked(self, snapshot: LocalCollectibleSnapshot, *, profile: str) -> CollectibleProgressImportReport:
        target_profile = self.collectible_progress.ensure_profile(profile)
        matched_ids, unresolved, ambiguous = self._analyze(snapshot)
        marked = 0
        if matched_ids:
            marked = self.collectible_progress.set_owned_batch(
                target_profile,
                {collectible_id: True for collectible_id in matched_ids},
            )
        return CollectibleProgressImportReport(
            source_person=snapshot.person,
            target_profile=target_profile,
            sheet_rows=len(snapshot.rows),
            checked_rows=len(snapshot.checked_rows),
            matched_collectibles=len(matched_ids),
            collectibles_marked_owned=marked,
            unresolved_names=tuple(sorted(unresolved, key=str.casefold)),
            ambiguous_names=tuple(sorted(ambiguous, key=str.casefold)),
            scanned_tabs=tuple(snapshot.scanned_tabs),
        )
