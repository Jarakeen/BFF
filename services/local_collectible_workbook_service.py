from __future__ import annotations

"""Read standalone collectible ownership from legacy BFF workbooks."""

from dataclasses import dataclass
from pathlib import Path

from services.google_sheets_service import ACHIEVEMENT_TABS, COLUMN_FOR_PERSON


@dataclass(frozen=True)
class LocalCollectibleRow:
    tab_name: str
    row_number: int
    name: str
    checked: bool


@dataclass(frozen=True)
class LocalCollectibleSnapshot:
    person: str
    rows: tuple[LocalCollectibleRow, ...]
    scanned_tabs: tuple[str, ...]

    @property
    def checked_rows(self) -> tuple[LocalCollectibleRow, ...]:
        return tuple(row for row in self.rows if row.checked)


class LocalCollectibleWorkbookService:
    """Extract collectible checkmarks without treating the workbook as canonical data.

    The historical BFF workbook evolved organically. Its collectible sections
    do not share one absolute column layout, but they *do* consistently mark
    ownership blocks with adjacent ``R`` / ``J`` header cells followed by the
    item-name column. Some sheets repeat those blocks many times. Detect those
    blocks directly instead of guessing A/B/C or relying on a single header row.
    """

    # These are the workbook areas that track Collectibles-page ownership. Other
    # R/J sheets (motifs, recipes, titles, antiquities, sticker book, etc.) have
    # their own canonical progress systems and must not be treated as collectible
    # ownership simply because they also use checkmarks.
    _COLLECTIBLE_SHEETS = {
        "appearance",
        "emotes",
        "fragments",
        "furnishings",
        "limited time collectibles",
        "gold coast bazaar",
        "golden pursuits",
        "tamriel tomes",
        "housing",
        "mementos",
        "mounts",
        "pets",
        "style pages",
        "upgrades and companions",
        "collectors edition",
    }

    @staticmethod
    def _is_checked(value) -> bool:
        return str(value or "").strip().casefold() in {"x", "✓", "✔", "yes", "true", "1"}

    @staticmethod
    def _load_workbook(path: Path):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError(
                "Local spreadsheet import needs openpyxl. Install it with: pip install openpyxl"
            ) from exc

        path = Path(path)
        if path.suffix.casefold() not in {".xlsx", ".xlsm"}:
            raise ValueError("Choose an .xlsx or .xlsm workbook.")
        if not path.exists():
            raise FileNotFoundError(path)
        return load_workbook(path, read_only=True, data_only=True)

    @staticmethod
    def _normalized(value) -> str:
        return " ".join(str(value or "").strip().casefold().split())

    @classmethod
    def _header_blocks(cls, sheet) -> list[tuple[int, int, int, int]]:
        """Return (row, rylo_col, jarakeen_col, name_col), all zero-based cols."""
        blocks: list[tuple[int, int, int, int]] = []
        for row_number, values in enumerate(sheet.iter_rows(values_only=True), start=1):
            normalized = [cls._normalized(value) for value in values]
            for index in range(max(0, len(normalized) - 1)):
                if normalized[index] == "r" and normalized[index + 1] == "j":
                    blocks.append((row_number, index, index + 1, index + 2))
                    break
        return blocks

    def read_person(self, path: Path, person: str) -> LocalCollectibleSnapshot:
        person = str(person or "").strip()
        if person not in COLUMN_FOR_PERSON:
            raise ValueError(f"Unknown profile source: {person}")

        workbook = self._load_workbook(path)
        try:
            rows: list[LocalCollectibleRow] = []
            scanned_tabs: list[str] = []
            achievement_tabs = {name.casefold() for name in ACHIEVEMENT_TABS}
            reserved = {"achievements", "progress", "meta"}

            for tab_name in workbook.sheetnames:
                key = self._normalized(tab_name)
                if key in achievement_tabs or key in reserved or key not in self._COLLECTIBLE_SHEETS:
                    continue

                sheet = workbook[tab_name]
                blocks = self._header_blocks(sheet)
                if not blocks:
                    # A collectible-labelled sheet without R/J ownership blocks
                    # is informational only for this importer.
                    continue

                scanned_tabs.append(tab_name)
                all_values = list(sheet.iter_rows(values_only=True))
                for block_index, (header_row, rylo_col, jarakeen_col, name_col) in enumerate(blocks):
                    next_header_row = blocks[block_index + 1][0] if block_index + 1 < len(blocks) else len(all_values) + 1
                    mark_col = rylo_col if person == "Rylo" else jarakeen_col

                    for row_number in range(header_row + 1, next_header_row):
                        values = all_values[row_number - 1]
                        if len(values) <= max(mark_col, name_col):
                            continue
                        if not self._is_checked(values[mark_col]):
                            continue
                        name = str(values[name_col] or "").strip()
                        if not name:
                            continue
                        rows.append(
                            LocalCollectibleRow(
                                tab_name=tab_name,
                                row_number=row_number,
                                name=name,
                                checked=True,
                            )
                        )

            return LocalCollectibleSnapshot(
                person=person,
                rows=tuple(rows),
                scanned_tabs=tuple(scanned_tabs),
            )
        finally:
            workbook.close()
