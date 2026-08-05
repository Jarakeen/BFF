# services/google_sheets_service.py
from __future__ import annotations

from pathlib import Path

# The ~50 tabs in the BFF achievement tracker that share the same layout:
# column A = "R" (Rylo's checkmark), column B = "J" (Jarakeen's checkmark),
# column C = achievement name, column F = points, column G = description.
# Section-header rows (e.g. "Rockgrove", "Defeating Bosses") only have
# column C filled - no points/description - which is how we tell them apart
# from real achievement rows.
ACHIEVEMENT_TABS = [
    "Character Achievements", "Achievements for PVP", "Crafting Achievements",
    "Dark Anchors Achievements", "Exploration Achievements", "Dungeons Achievements",
    "Veteran Dungeons Achievements", "Housing Achievements", "Quest Achievements",
    "Holiday Events", "Prologues Achievements", "Infinite Archive Achievements",
    "Ascending Tide Achievements", "Blackwood Achievements", "Clockwork City Achievements",
    "Dark Brotherhood Achievements", "The Deadlands", "Dragon Bones Achievements",
    "Dragonhold Achievements", "Elsweyr Achievements", "Fallen Banners",
    "Feast of Shadows", "Firesong Achievements", "Flames of Ambition Achievements",
    "Gold Road Achievements", "Greymoor", "Harrowstorm Achievements",
    "High Isle Achievements", "Horns of the Reach Achievements", "Imperial City Achievements",
    "Lost Depths Achievements", "Markarth Achievements", "Morrowind Achievements",
    "Murkmire", "Necrom", "Night Market", "Orsinium Achievements",
    "Scalebreaker Achievements", "Scions of Ithelia Achievements", "Scribes of Fate Achievements",
    "Seasons of the Worm Cult", "Season Zero", "Season One",
    "Shadows of the Hist Achievement", "Stonethorn Achievements", "Summerset Achievements",
    "Thieves Guild Achievements", "Waking Flame Achievements", "Wolfhunter Achievements",
    "Wrathstone Achievements",
]

COLUMN_FOR_PERSON = {"Rylo": 1, "Jarakeen": 2}  # 1-indexed: column A / column B

NAME_COL = 3
POINTS_COL = 6


class GoogleSheetsNotConfigured(Exception):
    """Raised when credentials or spreadsheet ID haven't been set up yet."""


class GoogleSheetsService:
    """Reads/writes the BFF achievement tracker spreadsheet.

    Requires the `gspread` and `google-auth` packages (pip install gspread
    google-auth) and a Google Cloud Service Account JSON key that has been
    shared as an Editor on the target spreadsheet.
    """

    def __init__(self, credentials_path: Path, spreadsheet_id: str) -> None:
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self._client = None
        self._spreadsheet = None
        self._index: dict[str, tuple[str, int]] = {}  # achievement name -> (tab_name, row_number)

    def _ensure_connected(self):
        if self._spreadsheet is not None:
            return
        if not self.credentials_path or not Path(self.credentials_path).exists():
            raise GoogleSheetsNotConfigured(
                f"Service account credentials file not found: {self.credentials_path}"
            )
        if not self.spreadsheet_id:
            raise GoogleSheetsNotConfigured("No spreadsheet ID configured.")

        import gspread  # imported lazily so the app still runs without it installed

        self._client = gspread.service_account(filename=str(self.credentials_path))
        self._spreadsheet = self._client.open_by_key(self.spreadsheet_id)

    def build_index(self, progress_callback=None) -> int:
        """Scan every achievement tab and index each achievement row by name.
        Returns the number of achievements indexed. Call this once per
        session (or whenever you want to refresh it) before looking anything
        up - it's ~50 bulk reads, one per tab, not one call per row."""
        self._ensure_connected()
        self._index.clear()

        for i, tab_name in enumerate(ACHIEVEMENT_TABS):
            if progress_callback:
                progress_callback(i + 1, len(ACHIEVEMENT_TABS), tab_name)
            try:
                worksheet = self._spreadsheet.worksheet(tab_name)
            except Exception:
                continue  # tab renamed/missing - skip rather than fail the whole index
            values = worksheet.get_all_values()
            for row_num, row in enumerate(values, start=1):
                name = row[NAME_COL - 1].strip() if len(row) >= NAME_COL else ""
                points = row[POINTS_COL - 1].strip() if len(row) >= POINTS_COL else ""
                if name and points:
                    # Real achievement row (section headers have a name but no points)
                    self._index[name] = (tab_name, row_num)

        return len(self._index)

    def lookup(self, achievement_name: str) -> tuple[str, int] | None:
        return self._index.get(achievement_name)

    def get_status(self, achievement_name: str, person: str) -> bool | None:
        """Returns True/False if the achievement is found and marked/unmarked,
        or None if the achievement isn't in the index (not found in the sheet)."""
        location = self.lookup(achievement_name)
        if location is None:
            return None
        tab_name, row_num = location
        self._ensure_connected()
        worksheet = self._spreadsheet.worksheet(tab_name)
        col = COLUMN_FOR_PERSON[person]
        value = worksheet.cell(row_num, col).value or ""
        return value.strip().lower() == "x"

    def set_status(self, achievement_name: str, person: str, checked: bool) -> bool:
        """Writes/clears the checkmark for one person on one achievement.
        Returns True if written, False if the achievement wasn't found in
        the sheet (nothing to write to)."""
        location = self.lookup(achievement_name)
        if location is None:
            return False
        tab_name, row_num = location
        self._ensure_connected()
        worksheet = self._spreadsheet.worksheet(tab_name)
        col = COLUMN_FOR_PERSON[person]
        worksheet.update_cell(row_num, col, "X" if checked else "")
        return True
