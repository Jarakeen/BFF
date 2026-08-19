# services/uesp/uesp_importer.py
"""
Orchestrates the UESP client, parser, and store to build the local
knowledge base. This is the layer tools/import_uesp.py talks to; it
has no knowledge of argparse or the terminal, and the UI never
imports this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from services.uesp.uesp_client import UespClient, UespClientError, UespPage
from services.uesp.uesp_store import UespStore
from services.uesp.enriched_parser import EnrichedUespParser
from services.uesp.uesp_parser import slugify

TRIAL_CATEGORY = "Online-Places-Trials"
DUNGEON_CATEGORY = "Online-Places-Group_Dungeons"
ARENA_CATEGORY = "Online:Arenas"
ARENA_TITLES = {
    "Online:Blackrose Prison",
    "Online:Dragonstar Arena",
    "Online:Infinite Archive",
    "Online:Maelstrom Arena (place)",
    "Online:Vateshran Hollows",
}

@dataclass
class ImportResult:
    title: str
    status: str  # "imported" | "skipped_up_to_date" | "error"
    detail: str = ""


class UespImporter:

    def __init__(
        self,
        client: UespClient,
        store: UespStore,
        log_path: Path,
        force: bool = False,
    ) -> None:
        self.client = client
        self.store = store
        self.log_path = log_path
        self.force = force
        self.parser = EnrichedUespParser()

        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # Single-item imports
    # --------------------------------------------------

    def import_boss(
        self,
        title: str,
        content_id: str = "",
        content_name: str = "",
    ) -> ImportResult:

        try:
            page_title = (
                title
                if ":" in title
                else f"Online:{title}"
            )

            record_id = slugify(page_title)
            page = self.client.get_page(page_title)

            if not self.force and self.store.is_up_to_date(
                "bosses",
                record_id,
                page.revision_id,
            ):
                return self._log(
                    ImportResult(title, "skipped_up_to_date")
                )

            boss = self.parser.parse_boss(
                page,
                content_id=content_id,
                content_name=content_name,
            )

            self.store.save_boss(boss)

            return self._log(
                ImportResult(title, "imported")
            )

        except UespClientError as exc:
            return self._log(
                ImportResult(title, "error", str(exc))
            )
        except Exception as exc:
            # One bad page shouldn't kill a bulk import.
            return self._log(
                ImportResult(
                    title,
                    "error",
                    f"Unexpected error: {exc}",
                )
            )


    def import_content(
        self,
        title: str,
        content_type: str = "trial",
    ) -> ImportResult:

        try:
            page = self.client.get_page(title)

            resolved_type = self.parser.detect_content_type(
                page,
                default=content_type,
            )

            folder = self.store.folder_for(resolved_type)

            content = self.parser.parse_content(
                page,
                content_type=resolved_type,
            )

            record_id = content.id

            content_up_to_date = (
                not self.force
                and self.store.is_up_to_date(
                    folder,
                    record_id,
                    page.revision_id,
                )
            )

            if resolved_type == "arena":
                boss_titles = self.parser.find_arena_boss_links(page)
            else:
                boss_titles = self.parser.find_boss_links(page)

            for boss_title in boss_titles:
                boss_result = self.import_boss(
                    boss_title,
                    content_id=content.id,
                    content_name=content.name,
                )

                if boss_result.status != "error":
                    boss_id = slugify(boss_title)

                    if boss_id not in content.boss_ids:
                        content.boss_ids.append(boss_id)
            self.store.save_content(content)

            if content_up_to_date:
                return self._log(
                    ImportResult(
                        title,
                        "skipped_up_to_date",
                        "content current; boss relationships reconciled",
                    )
                )
            self.store.save_content(content)

            return self._log(
                ImportResult(title, "imported")
            )

        except UespClientError as exc:
            return self._log(
                ImportResult(title, "error", str(exc))
            )
        except Exception as exc:
            return self._log(
                ImportResult(
                    title,
                    "error",
                    f"Unexpected error: {exc}",
                )
            )

    # --------------------------------------------------
    # Bulk imports
    # --------------------------------------------------

    def import_all_trials(self) -> list[ImportResult]:
        return self._import_category(TRIAL_CATEGORY, "trial")

    def import_all_dungeons(self) -> list[ImportResult]:
        return self._import_category(DUNGEON_CATEGORY, "dungeon")

    def import_all_arenas(self) -> list[ImportResult]:
        """
        Import the supported ESO arenas.

        UESP exposes Online:Arenas as a valid category, but its
        categorymembers API currently returns an empty page list.
        Because the supported arena roster is explicitly validated,
        fall back to ARENA_TITLES when the category query is empty.

        This keeps the importer restricted to the five intended
        gear/achievement arenas and prevents a silent zero-import.
        """
        try:
            titles = self.client.get_category_members(ARENA_CATEGORY)
        except UespClientError as exc:
            titles = []
            self._log(
                ImportResult(
                    f"Category:{ARENA_CATEGORY}",
                    "error",
                    str(exc),
                )
            )

        selected = [
            title
            for title in titles
            if title in ARENA_TITLES
        ]

        # UESP's Online:Arenas category currently returns no
        # categorymembers through the API. Use the validated roster
        # rather than silently importing nothing.
        if not selected:
            selected = sorted(ARENA_TITLES)

        return [
            self.import_content(title, "arena")
            for title in selected
        ]

    def import_all(self) -> list[ImportResult]:
        results: list[ImportResult] = []
        results.extend(self.import_all_trials())
        results.extend(self.import_all_dungeons())
        results.extend(self.import_all_arenas())
        return results

    def _import_category(self, category: str, content_type: str) -> list[ImportResult]:

        try:
            titles = self.client.get_category_members(category)
        except UespClientError as exc:
            return [self._log(ImportResult(f"Category:{category}", "error", str(exc)))]

        return [self.import_content(title, content_type) for title in titles]

    # --------------------------------------------------
    # Logging
    # --------------------------------------------------

    def _log(self, result: ImportResult) -> ImportResult:

        entry = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "title": result.title,
            "status": result.status,
            "detail": result.detail,
        }

        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

        return result
