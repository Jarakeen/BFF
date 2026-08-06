# services/archive_service.py
from __future__ import annotations

from pathlib import Path
from services.archive_record import ArchiveRecord

# Counter filenames kept human-readable and backwards compatible with the
# existing FieldNoteCounter.txt (which the OBS Lua script also reads
# directly, so its name/format must not change).
COUNTER_FILENAMES = {
    "IR": "IncidentCounter.txt",
    "FN": "FieldNoteCounter.txt",
    "EX": "ExpeditionCounter.txt",
    "AR": "AchievementRunCounter.txt",
}

FORM_LABELS = {
    "IR": "Incident Report",
    "FN": "Field Note",
    "EX": "Expedition Archive",
    "AR": "Achievement Run",
}


class ArchiveService:
    """Assigns sequential IDs (IR-0001, FN-0002, ...) and writes archive markdown.

    counters_folder is where per-type counter .txt files live (plain integers,
    same format as the original FieldNoteCounter.txt so the Lua script can
    keep reading it unmodified). archive_folder is where the .md files land.
    """

    def __init__(self, counters_folder: Path, archive_folder: Path) -> None:
        self.counters_folder = counters_folder
        self.archive_folder = archive_folder

    def _counter_path(self, prefix: str) -> Path:
        filename = COUNTER_FILENAMES.get(prefix)
        if filename is None:
            raise ValueError(f"Unknown archive prefix: {prefix}")
        return self.counters_folder / filename

    def peek_number(self, prefix: str) -> int:
        """Return the current counter value without incrementing it."""
        counter_path = self._counter_path(prefix)
        if not counter_path.exists():
            return 0
        raw = counter_path.read_text(encoding="utf-8").strip().strip('"').strip("'")
        return int(raw) if raw else 0

    def next_number(self, prefix: str) -> int:
        """Increment and persist the counter for this prefix, return the new value."""
        counter_path = self._counter_path(prefix)
        counter_path.parent.mkdir(parents=True, exist_ok=True)
        current = self.peek_number(prefix)
        new_value = current + 1
        counter_path.write_text(str(new_value), encoding="utf-8")
        return new_value

    @staticmethod
    def format_id(prefix: str, number: int) -> str:
        return f"{prefix}-{number:04d}"

    def write_markdown(self, prefix: str, number: int, lines: list[str]) -> Path:
        """Write an archive markdown file named e.g. IR_0042.md and return its path."""
        self.archive_folder.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}_{number:04d}.md"
        path = self.archive_folder / filename
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def file_form(self, prefix: str, lines_builder) -> tuple[str, Path]:
        """Assign the next number for prefix, build markdown via lines_builder(report_id, number),
        write it to the archive folder, and return (report_id, archive_path)."""
        number = self.next_number(prefix)
        report_id = self.format_id(prefix, number)
        lines = lines_builder(report_id, number)
        path = self.write_markdown(prefix, number, lines)
        return report_id, path

    def load_record(self, archive_no: str) -> str:
        """
        Load an archived markdown file.
        """

        filename = archive_no.replace("-", "_") + ".md"

        path = self.archive_folder / filename

        if not path.exists():
            return ""

        return path.read_text(
            encoding="utf-8"
        )

# --------------------------------------------------
# Archive Browser
# --------------------------------------------------

def list_records(self) -> list[ArchiveRecord]:
    """
    Return all archived records.
    """

    records: list[ArchiveRecord] = []

    if not self.archive_folder.exists():
        return records

    for path in sorted(
        self.archive_folder.glob("*.md"),
        reverse=True,
    ):

        archive_no = path.stem.replace("_", "-")

        records.append(
            ArchiveRecord(
                archive_no=archive_no,
                name=archive_no,
                path=path,
            )
        )

    return records


def load_record(self, archive_no: str) -> str:
    """
    Load an archived markdown file.
    """

    filename = archive_no.replace("-", "_") + ".md"

    path = self.archive_folder / filename

    if not path.exists():
        return ""

    return path.read_text(
        encoding="utf-8"
    )