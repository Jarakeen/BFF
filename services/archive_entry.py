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
    Represents a single archived record.

    This is a lightweight object used to populate the
    Archive Browser. It is not the full Expedition.
    """

    # Archive ID (EX-0001, FN-0005, IR-0012, etc.)
    archive_no: str

    # Display name shown in the browser.
    name: str

    # Path to the archive markdown file.
    path: Path

    @property
    def filename(self) -> str:
        """
        Return the archive filename.
        """

        return self.path.name

    @property
    def exists(self) -> bool:
        """
        Return True if the archive file exists.
        """

        return self.path.exists()

    def __str__(self) -> str:
        return self.name