from pathlib import Path

from services.broadcast_paths import BroadcastPaths
from services.paths import DATA, PROJECT_ROOT


def test_broadcast_paths_honor_configured_settings() -> None:
    settings = {
        "CurrentBroadcastPath": "C:/BFF/state/CurrentBroadcast.json",
        "StreamEventsPath": "C:/BFF/state/StreamEvents.json",
        "StreamSessionPath": "C:/BFF/state/StreamSession.json",
        "BossLogPath": "C:/BFF/archive/BossLog.md",
        "CountersFolder": "C:/BFF/counters",
        "ArchiveFolder": "C:/BFF/archive",
        "WeatherFolder": "C:/BFF/weather",
        "MarkerLogPath": "C:/BFF/state/MarkerLog.md",
        "FieldNoteCounterPath": "C:/BFF/state/FieldNoteCounter.txt",
        "SessionArchiveFolder": "C:/BFF/archive/Sessions",
    }

    paths = BroadcastPaths.from_settings(settings)

    assert paths.current_broadcast == Path(settings["CurrentBroadcastPath"])
    assert paths.stream_events == Path(settings["StreamEventsPath"])
    assert paths.stream_session == Path(settings["StreamSessionPath"])
    assert paths.boss_log == Path(settings["BossLogPath"])
    assert paths.counters_folder == Path(settings["CountersFolder"])
    assert paths.archive_folder == Path(settings["ArchiveFolder"])
    assert paths.weather_folder == Path(settings["WeatherFolder"])
    assert paths.marker_log == Path(settings["MarkerLogPath"])
    assert paths.field_note_counter == Path(settings["FieldNoteCounterPath"])
    assert paths.session_archive_folder == Path(settings["SessionArchiveFolder"])


def test_broadcast_paths_use_current_layout_as_fallback() -> None:
    paths = BroadcastPaths.from_settings({})

    assert paths.current_broadcast == DATA / "CurrentBroadcast.json"
    assert paths.stream_events == DATA / "StreamEvents.json"
    assert paths.stream_session == DATA / "StreamSession.json"
    assert paths.marker_log == DATA / "MarkerLog.md"
    assert paths.field_note_counter == DATA / "FieldNoteCounter.txt"
    assert paths.archive_folder == PROJECT_ROOT / "Archive"
    assert paths.session_archive_folder == PROJECT_ROOT / "Archive" / "Sessions"
