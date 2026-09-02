from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

from services.paths import BROADCAST_USER_DATA, DATA


BROADCAST_STATE_FILENAMES = (
    "CurrentBroadcast.json",
    "CurrentExpedition.json",
    "CurrentIncident.json",
    "StreamEvents.json",
    "StreamSession.json",
    "MarkerLog.md",
    "FieldNoteCounter.txt",
    "ExpeditionCounter.txt",
    "IncidentCounter.txt",
)


@dataclass(frozen=True)
class BroadcastStateMigrationResult:
    copied: tuple[str, ...]
    preserved: tuple[str, ...]
    missing: tuple[str, ...]


def migrate_legacy_broadcast_state(
    *,
    legacy_dir: Path = DATA,
    target_dir: Path = BROADCAST_USER_DATA,
) -> BroadcastStateMigrationResult:
    """Copy legacy Broadcast runtime state into ``user_data/broadcast``.

    Existing destination files always win. The migration is deliberately
    copy-only so a failed or interrupted transition never destroys the legacy
    files. Old tracked files can be retired in a later checkpoint after the
    application has proven the new location works on real user data.
    """

    legacy_dir = Path(legacy_dir)
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    preserved: list[str] = []
    missing: list[str] = []

    for filename in BROADCAST_STATE_FILENAMES:
        source = legacy_dir / filename
        destination = target_dir / filename

        if destination.exists():
            preserved.append(filename)
            continue
        if not source.exists():
            missing.append(filename)
            continue

        shutil.copy2(source, destination)
        copied.append(filename)

    return BroadcastStateMigrationResult(
        copied=tuple(copied),
        preserved=tuple(preserved),
        missing=tuple(missing),
    )
