# ==================================================
# Black Feather Foundry
#
# File:
# services/archive_record.py
#
# Purpose:
# Lightweight descriptor for an archived record.
#
# Used by ArchiveService and ArchiveBrowser.
#
# ==================================================

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ArchiveRecord:
    """
    Lightweight descriptor for an archived record.

    This is not the archived Expedition itself—
    it simply describes an entry shown in the
    Archive Browser.
    """

    # Archive identifier (EX-0001, FN-0003, etc.)
    archive_no: str

    # Display name shown in the browser.
    name: str

    # Full path to the archive file.
    path: Path

    @property
    def filename(self) -> str:
        """
        Return the archive filename.
        """
        return self.path.name

    @property
    def stem(self) -> str:
        """
        Return the filename without the extension.
        """
        return self.path.stem

    @property
    def exists(self) -> bool:
        """
        Return True if the archive file exists.
        """
        return self.path.exists()

    def __str__(self) -> str:
        return self.name