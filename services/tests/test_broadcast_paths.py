from pathlib import Path

from services.broadcast_paths import BroadcastPaths
from services.paths import BROADCAST_RESOURCES, BROADCAST_USER_DATA, DATA, PROJECT_ROOT


def test_broadcast_paths_honor_configured_settings() -> None:
    settings = {
        "CurrentBroadcastPath": "C:/BFF/state/CurrentBroadcast.json",
        "CurrentExpeditionPath": "C:/BFF/state/CurrentExpedition.json",
        "CurrentIncidentPath": "C:/BFF/state/CurrentIncident.json",
        "StreamEventsPath": "C:/BFF/state/StreamEvents.json",
        "StreamSessionPath": "C:/BFF/state/StreamSession.json",
        "MarkerLogPath": "C:/BFF/state/MarkerLog.md",
        "FootnotesPath": "C:/BFF/custom/footnotes.txt",
        "FieldNoteCounterPath": "C:/BFF/state/FieldNoteCounter.txt",
        "ExpeditionCounterPath": "C:/BFF/state/ExpeditionCounter.txt",
        "IncidentCounterPath": "C:/BFF/state/IncidentCounter.txt",
        "WeatherFolder": "C:/BFF/weather",
        "NarratorContentPath": "C:/BFF/custom/narrator.json",
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


def test_broadcast_paths_use_user_state_and_module_resources_as_fallback() -> None:
    paths = BroadcastPaths.from_settings({})

    assert paths.current_broadcast == BROADCAST_USER_DATA / "CurrentBroadcast.json"
    assert paths.current_expedition == BROADCAST_USER_DATA / "CurrentExpedition.json"
    assert paths.current_incident == BROADCAST_USER_DATA / "CurrentIncident.json"
    assert paths.stream_events == BROADCAST_USER_DATA / "StreamEvents.json"
    assert paths.stream_session == BROADCAST_USER_DATA / "StreamSession.json"
    assert paths.marker_log == BROADCAST_USER_DATA / "MarkerLog.md"
    assert paths.footnotes == BROADCAST_RESOURCES / "footnotes.txt"
    assert paths.field_note_counter == BROADCAST_USER_DATA / "FieldNoteCounter.txt"
    assert paths.expedition_counter == BROADCAST_USER_DATA / "ExpeditionCounter.txt"
    assert paths.incident_counter == BROADCAST_USER_DATA / "IncidentCounter.txt"
    assert paths.weather_folder == DATA / "Weather"
    assert paths.narrator_content == BROADCAST_RESOURCES / "natural_history_narrator.json"
    assert paths.counters_folder == BROADCAST_USER_DATA
    assert paths.archive_folder == PROJECT_ROOT / "Archive"
    assert paths.session_archive_folder == PROJECT_ROOT / "Archive" / "Sessions"


def test_broadcast_paths_translate_legacy_default_settings() -> None:
    paths = BroadcastPaths.from_settings(
        {
            "CurrentBroadcastPath": str(DATA / "CurrentBroadcast.json"),
            "CurrentExpeditionPath": str(DATA / "CurrentExpedition.json"),
            "CurrentIncidentPath": str(DATA / "CurrentIncident.json"),
            "StreamEventsPath": str(DATA / "StreamEvents.json"),
            "StreamSessionPath": str(DATA / "StreamSession.json"),
            "MarkerLogPath": str(DATA / "MarkerLog.md"),
            "FootnotesPath": str(DATA / "footnotes.txt"),
            "FieldNoteCounterPath": str(DATA / "FieldNoteCounter.txt"),
            "ExpeditionCounterPath": str(DATA / "ExpeditionCounter.txt"),
            "IncidentCounterPath": str(DATA / "IncidentCounter.txt"),
            "NarratorContentPath": str(DATA / "natural_history_narrator.json"),
            "CountersFolder": str(DATA),
        }
    )

    assert paths.current_broadcast == BROADCAST_USER_DATA / "CurrentBroadcast.json"
    assert paths.current_expedition == BROADCAST_USER_DATA / "CurrentExpedition.json"
    assert paths.current_incident == BROADCAST_USER_DATA / "CurrentIncident.json"
    assert paths.stream_events == BROADCAST_USER_DATA / "StreamEvents.json"
    assert paths.stream_session == BROADCAST_USER_DATA / "StreamSession.json"
    assert paths.marker_log == BROADCAST_USER_DATA / "MarkerLog.md"
    assert paths.footnotes == BROADCAST_RESOURCES / "footnotes.txt"
    assert paths.field_note_counter == BROADCAST_USER_DATA / "FieldNoteCounter.txt"
    assert paths.expedition_counter == BROADCAST_USER_DATA / "ExpeditionCounter.txt"
    assert paths.incident_counter == BROADCAST_USER_DATA / "IncidentCounter.txt"
    assert paths.narrator_content == BROADCAST_RESOURCES / "natural_history_narrator.json"
    assert paths.counters_folder == BROADCAST_USER_DATA
