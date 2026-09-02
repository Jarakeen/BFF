from __future__ import annotations

"""Import legacy BFF Google Sheet checkmarks into profile-aware local progress."""

from dataclasses import dataclass
import unicodedata

from services.achievement_progress_service import AchievementProgressService
from services.eso_achievement_database_service import EsoAchievementDatabaseService
from services.google_sheets_service import GoogleSheetAchievementSnapshot
from services.profiled_collectible_service import ProfiledCollectibleService


@dataclass(frozen=True)
class GoogleSheetProgressImportReport:
    source_person: str
    target_profile: str
    sheet_rows: int
    checked_rows: int
    matched_achievements: int
    achievements_added: int
    collectible_rewards_marked: int
    unresolved_names: tuple[str, ...]
    ambiguous_names: tuple[str, ...]
    missing_tabs: tuple[str, ...]


class GoogleSheetProgressImporter:
    """Map checked spreadsheet rows onto canonical IDs without fuzzy guesses.

    The spreadsheet is an external progress source, never the canonical ESO
    catalog. Imports are merge-only so a missing/renamed worksheet cannot
    silently erase local completion data. Completed achievements that
    canonically grant a collectible also mark that collectible owned for the
    same profile.
    """

    def __init__(
        self,
        achievement_data: EsoAchievementDatabaseService,
        achievement_progress: AchievementProgressService,
        collectible_progress: ProfiledCollectibleService,
    ) -> None:
        self.achievement_data = achievement_data
        self.achievement_progress = achievement_progress
        self.collectible_progress = collectible_progress

    @staticmethod
    def _normalized_name(value: str) -> str:
        text = unicodedata.normalize("NFKC", str(value or ""))
        return " ".join(text.split()).casefold()

    def _canonical_name_index(self) -> dict[str, list[tuple[int, int | None]]]:
        rows = self.achievement_data.connection.execute(
            """
            SELECT a.id, a.name,
                   CASE WHEN c.id IS NOT NULL THEN a.collectible_id ELSE NULL END AS collectible_id
            FROM achievement a
            LEFT JOIN collectible c ON c.id = a.collectible_id
            WHERE a.name IS NOT NULL AND TRIM(a.name) <> ''
            ORDER BY a.id
            """
        ).fetchall()
        index: dict[str, list[tuple[int, int | None]]] = {}
        for row in rows:
            key = self._normalized_name(row["name"])
            if not key:
                continue
            collectible_id = row["collectible_id"]
            index.setdefault(key, []).append(
                (
                    int(row["id"]),
                    int(collectible_id) if collectible_id is not None else None,
                )
            )
        return index

    def import_checked(
        self,
        snapshot: GoogleSheetAchievementSnapshot,
        *,
        profile: str,
    ) -> GoogleSheetProgressImportReport:
        """Merge checked rows into one profile and return a deterministic report."""
        target_profile = self.achievement_progress.ensure_profile(profile)
        self.collectible_progress.ensure_profile(target_profile)
        canonical = self._canonical_name_index()

        matched_ids: set[int] = set()
        collectible_ids: set[int] = set()
        unresolved: set[str] = set()
        ambiguous: set[str] = set()

        for sheet_row in snapshot.checked_rows:
            key = self._normalized_name(sheet_row.name)
            matches = canonical.get(key, [])
            if not matches:
                unresolved.add(sheet_row.name)
                continue
            if len(matches) != 1:
                ambiguous.add(sheet_row.name)
                continue
            achievement_id, collectible_id = matches[0]
            matched_ids.add(achievement_id)
            if collectible_id is not None:
                collectible_ids.add(collectible_id)

        added = self.achievement_progress.merge_completed(target_profile, matched_ids)
        collectible_marked = 0
        if collectible_ids and self.collectible_progress.available:
            collectible_marked = self.collectible_progress.set_owned_batch(
                target_profile,
                {collectible_id: True for collectible_id in collectible_ids},
            )

        return GoogleSheetProgressImportReport(
            source_person=snapshot.person,
            target_profile=target_profile,
            sheet_rows=len(snapshot.rows),
            checked_rows=len(snapshot.checked_rows),
            matched_achievements=len(matched_ids),
            achievements_added=added,
            collectible_rewards_marked=collectible_marked,
            unresolved_names=tuple(sorted(unresolved, key=str.casefold)),
            ambiguous_names=tuple(sorted(ambiguous, key=str.casefold)),
            missing_tabs=tuple(snapshot.missing_tabs),
        )
