from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from services.paths import DATA, PROJECT_ROOT


@dataclass(frozen=True)
class BroadcastPaths:
    """Resolved filesystem contract for the optional Broadcast module.

    The paths intentionally point at today's on-disk layout. Broadcast callers
    should depend on this contract instead of constructing file locations.
    That lets a later migration move mutable state into ``user_data/broadcast``
    and static resources into ``modules/broadcast/resources`` without changing
    every page, service, and OBS integration independently.
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
            footnotes=_configured_path(
                settings, "FootnotesPath", DATA / "footnotes.txt"
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
            narrator_content=_configured_path(
                settings, "NarratorContentPath", DATA / "natural_history_narrator.json"
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


def _configured_path(
    settings: Mapping[str, object],
    key: str,
    fallback: Path,
) -> Path:
    value = str(settings.get(key, "") or "").strip().strip('"').strip("'")
    return Path(value) if value else fallback
