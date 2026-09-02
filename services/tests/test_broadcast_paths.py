from pathlib import Path

from services.broadcast_paths import BroadcastPaths
from services.paths import DATA, PROJECT_ROOT


def test_broadcast_paths_honor_configured_settings() -> None:
    settings = {
        "CurrentBroadcastPath": "C:/BFF/state/CurrentBroadcast.json",
        "CurrentExpeditionPath": "C:/BFF/state/CurrentExpedition.json",
        "CurrentIncidentPath": "C:/BFF/state/CurrentIncident.json",
        "StreamEventsPath": "C:/BFF/state/StreamEvents.json",
        "StreamSessionPath": "C:/BFF/state/StreamSession.json",
        "MarkerLogPath": "C:/BFF/state/MarkerLog.md",
        "FootnotesPath": "C:/BFF/state/footnotes.txt",
        "FieldNoteCounterPath": "C:/BFF/state/FieldNoteCounter.txt",
        "ExpeditionCounterPath": "C:/BFF/state/ExpeditionCounter.txt",
        "IncidentCounterPath": "C:/BFF/state/IncidentCounter.txt",
        "WeatherFolder": "C:/BFF/weather",
        "NarratorContentPath": "C:/BFF/modules/broadcast/resources/narrator.json",
        "BossLogPath": "C:/BFF/archive/BossLog.md",
        "CountersFolder": "C:/BFF/counters",
        "ArchiveFolder": "C:/BFF/archive",
        "SessionArchiveFolder": "C:/BFF/archive/Sessions",
    }

    paths = BroadcastPaths.from_settings(settings)

    assert paths.current_broadcast == Path(settings["CurrentBroadcastPath"])
    assert paths.current_expedition == Path(settings["CurrentExpeditionPath"])
    assert paths.current_incident == Path(settings["CurrentIncidentPath"])
    assert paths.stream_events == Path(settings["StreamEventsPath"])
    assert paths.stream_session == Path(settings["StreamSessionPath"])
    assert paths.marker_log == Path(settings["MarkerLogPath"])
    assert paths.footnotes == Path(settings["FootnotesPath"])
    assert paths.field_note_counter == Path(settings["FieldNoteCounterPath"])
    assert paths.expedition_counter == Path(settings["ExpeditionCounterPath"])
    assert paths.incident_counter == Path(settings["IncidentCounterPath"])
    assert paths.weather_folder == Path(settings["WeatherFolder"])
    assert paths.narrator_content == Path(settings["NarratorContentPath"])
    assert paths.boss_log == Path(settings["BossLogPath"])
    assert paths.counters_folder == Path(settings["CountersFolder"])
    assert paths.archive_folder == Path(settings["ArchiveFolder"])
    assert paths.session_archive_folder == Path(settings["SessionArchiveFolder"])


def test_broadcast_paths_use_current_layout_as_fallback() -> None:
    paths = BroadcastPaths.from_settings({})

    assert paths.current_broadcast == DATA / "CurrentBroadcast.json"
    assert paths.current_expedition == DATA / "CurrentExpedition.json"
    assert paths.current_incident == DATA / "CurrentIncident.json"
    assert paths.stream_events == DATA / "StreamEvents.json"
    assert paths.stream_session == DATA / "StreamSession.json"
    assert paths.marker_log == DATA / "MarkerLog.md"
    assert paths.footnotes == DATA / "footnotes.txt"
    assert paths.field_note_counter == DATA / "FieldNoteCounter.txt"
    assert paths.expedition_counter == DATA / "ExpeditionCounter.txt"
    assert paths.incident_counter == DATA / "IncidentCounter.txt"
    assert paths.weather_folder == DATA / "Weather"
    assert paths.narrator_content == DATA / "natural_history_narrator.json"
    assert paths.counters_folder == DATA
    assert paths.archive_folder == PROJECT_ROOT / "Archive"
    assert paths.session_archive_folder == PROJECT_ROOT / "Archive" / "Sessions"
