from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from services.paths import DATA, PROJECT_ROOT


BROADCAST_RESOURCES = PROJECT_ROOT / "modules" / "broadcast" / "resources"


@dataclass(frozen=True)
class BroadcastPaths:
    """Resolved filesystem contract for the optional Broadcast module.

    Broadcast callers should depend on this contract instead of constructing
    file locations. Mutable state still points at today's on-disk layout while
    tracked static resources can already live under ``modules/broadcast``.
    Legacy default resource paths are translated automatically so existing
    settings files do not need to be hand-edited during the migration.
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
            current_broadcast=_configured_path(
                settings, "CurrentBroadcastPath", DATA / "CurrentBroadcast.json"
            ),
            current_expedition=_configured_path(
                settings, "CurrentExpeditionPath", DATA / "CurrentExpedition.json"
            ),
            current_incident=_configured_path(
                settings, "CurrentIncidentPath", DATA / "CurrentIncident.json"
            ),
            stream_events=_configured_path(
                settings, "StreamEventsPath", DATA / "StreamEvents.json"
            ),
            stream_session=_configured_path(
                settings, "StreamSessionPath", DATA / "StreamSession.json"
            ),
            marker_log=_configured_path(
                settings, "MarkerLogPath", DATA / "MarkerLog.md"
            ),
            footnotes=_configured_resource_path(
                settings,
                "FootnotesPath",
                BROADCAST_RESOURCES / "footnotes.txt",
                DATA / "footnotes.txt",
            ),
            field_note_counter=_configured_path(
                settings, "FieldNoteCounterPath", DATA / "FieldNoteCounter.txt"
            ),
            expedition_counter=_configured_path(
                settings, "ExpeditionCounterPath", DATA / "ExpeditionCounter.txt"
            ),
            incident_counter=_configured_path(
                settings, "IncidentCounterPath", DATA / "IncidentCounter.txt"
            ),
            weather_folder=_configured_path(
                settings, "WeatherFolder", DATA / "Weather"
            ),
            narrator_content=_configured_resource_path(
                settings,
                "NarratorContentPath",
                BROADCAST_RESOURCES / "natural_history_narrator.json",
                DATA / "natural_history_narrator.json",
            ),
            boss_log=_configured_path(
                settings, "BossLogPath", legacy_archive / "BossLog.md"
            ),
            counters_folder=_configured_path(
                settings, "CountersFolder", DATA
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


def _configured_resource_path(
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
