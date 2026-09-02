from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from services.paths import DATA, PROJECT_ROOT


@dataclass(frozen=True)
class BroadcastPaths:
    """Resolved filesystem contract for the optional Broadcast module.

    This deliberately points at the application's current on-disk locations.
    Callers should depend on this object rather than constructing Broadcast
    paths themselves. A later migration can therefore move mutable state into
    ``user_data/broadcast`` without rewriting every page and service.
    """

    current_broadcast: Path
    stream_events: Path
    stream_session: Path
    boss_log: Path
    counters_folder: Path
    archive_folder: Path
    weather_folder: Path
    marker_log: Path
    field_note_counter: Path
    session_archive_folder: Path

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "BroadcastPaths":
        legacy_archive = PROJECT_ROOT / "Archive"
        return cls(
            current_broadcast=_configured_path(
                settings, "CurrentBroadcastPath", DATA / "CurrentBroadcast.json"
            ),
            stream_events=_configured_path(
                settings, "StreamEventsPath", DATA / "StreamEvents.json"
            ),
            stream_session=_configured_path(
                settings, "StreamSessionPath", DATA / "StreamSession.json"
            ),
            boss_log=_configured_path(
                settings, "BossLogPath", legacy_archive / "BossLog.md"
            ),
            counters_folder=_configured_path(
                settings, "CountersFolder", PROJECT_ROOT
            ),
            archive_folder=_configured_path(
                settings, "ArchiveFolder", legacy_archive
            ),
            weather_folder=_configured_path(
                settings, "WeatherFolder", PROJECT_ROOT / "Weather"
            ),
            marker_log=_configured_path(
                settings, "MarkerLogPath", DATA / "MarkerLog.md"
            ),
            field_note_counter=_configured_path(
                settings, "FieldNoteCounterPath", DATA / "FieldNoteCounter.txt"
            ),
            session_archive_folder=_configured_path(
                settings, "SessionArchiveFolder", legacy_archive / "Sessions"
            ),
        )


def _configured_path(
    settings: Mapping[str, object],
    key: str,
    fallback: Path,
) -> Path:
    value = str(settings.get(key, "") or "").strip().strip('"').strip("'")
    return Path(value) if value else fallback
