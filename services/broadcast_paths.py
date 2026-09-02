from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from services.paths import (
    BROADCAST_RESOURCES,
    BROADCAST_USER_DATA,
    DATA,
    PROJECT_ROOT,
)


@dataclass(frozen=True)
class BroadcastPaths:
    """Resolved filesystem contract for the optional Broadcast module.

    Mutable Broadcast state belongs under ``user_data/broadcast``. Existing
    settings that still point at the old ``data`` defaults are translated to
    the new location after the startup migrator has copied their contents.
    Custom user-selected paths remain untouched.
    """

    current_broadcast: Path
    current_expedition: Path
    current_incident: Path
    stream_events: Path
    stream_session: Path
    marker_log: Path
    footnotes: Path
    field_note_counter: Path
    expedition_counter: Path
    incident_counter: Path
    weather_folder: Path
    narrator_content: Path
    boss_log: Path
    counters_folder: Path
    archive_folder: Path
    session_archive_folder: Path

    @classmethod
    def from_settings(cls, settings: Mapping[str, object]) -> "BroadcastPaths":
        legacy_archive = PROJECT_ROOT / "Archive"
        return cls(
            current_broadcast=_configured_migrated_path(
                settings,
                "CurrentBroadcastPath",
                BROADCAST_USER_DATA / "CurrentBroadcast.json",
                DATA / "CurrentBroadcast.json",
            ),
            current_expedition=_configured_migrated_path(
                settings,
                "CurrentExpeditionPath",
                BROADCAST_USER_DATA / "CurrentExpedition.json",
                DATA / "CurrentExpedition.json",
            ),
            current_incident=_configured_migrated_path(
                settings,
                "CurrentIncidentPath",
                BROADCAST_USER_DATA / "CurrentIncident.json",
                DATA / "CurrentIncident.json",
            ),
            stream_events=_configured_migrated_path(
                settings,
                "StreamEventsPath",
                BROADCAST_USER_DATA / "StreamEvents.json",
                DATA / "StreamEvents.json",
            ),
            stream_session=_configured_migrated_path(
                settings,
                "StreamSessionPath",
                BROADCAST_USER_DATA / "StreamSession.json",
                DATA / "StreamSession.json",
            ),
            marker_log=_configured_migrated_path(
                settings,
                "MarkerLogPath",
                BROADCAST_USER_DATA / "MarkerLog.md",
                DATA / "MarkerLog.md",
            ),
            footnotes=_configured_migrated_path(
                settings,
                "FootnotesPath",
                BROADCAST_RESOURCES / "footnotes.txt",
                DATA / "footnotes.txt",
            ),
            field_note_counter=_configured_migrated_path(
                settings,
                "FieldNoteCounterPath",
                BROADCAST_USER_DATA / "FieldNoteCounter.txt",
                DATA / "FieldNoteCounter.txt",
            ),
            expedition_counter=_configured_migrated_path(
                settings,
                "ExpeditionCounterPath",
                BROADCAST_USER_DATA / "ExpeditionCounter.txt",
                DATA / "ExpeditionCounter.txt",
            ),
            incident_counter=_configured_migrated_path(
                settings,
                "IncidentCounterPath",
                BROADCAST_USER_DATA / "IncidentCounter.txt",
                DATA / "IncidentCounter.txt",
            ),
            weather_folder=_configured_path(
                settings, "WeatherFolder", DATA / "Weather"
            ),
            narrator_content=_configured_migrated_path(
                settings,
                "NarratorContentPath",
                BROADCAST_RESOURCES / "natural_history_narrator.json",
                DATA / "natural_history_narrator.json",
            ),
            boss_log=_configured_path(
                settings, "BossLogPath", legacy_archive / "BossLog.md"
            ),
            counters_folder=_configured_migrated_path(
                settings,
                "CountersFolder",
                BROADCAST_USER_DATA,
                DATA,
            ),
            archive_folder=_configured_path(
                settings, "ArchiveFolder", legacy_archive
            ),
            session_archive_folder=_configured_path(
                settings, "SessionArchiveFolder", legacy_archive / "Sessions"
            ),
        )


def _clean_path_value(value: object) -> str:
    return str(value or "").strip().strip('"').strip("'")


def _configured_path(
    settings: Mapping[str, object],
    key: str,
    fallback: Path,
) -> Path:
    value = _clean_path_value(settings.get(key, ""))
    return Path(value) if value else fallback


def _configured_migrated_path(
    settings: Mapping[str, object],
    key: str,
    fallback: Path,
    legacy_default: Path,
) -> Path:
    value = _clean_path_value(settings.get(key, ""))
    if not value:
        return fallback

    configured = Path(value)
    try:
        if configured.resolve(strict=False) == legacy_default.resolve(strict=False):
            return fallback
    except OSError:
        pass

    return configured
