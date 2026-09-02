from pathlib import Path

from services.settings_service import SettingsService


def test_default_broadcast_settings_use_split_layout(tmp_path: Path) -> None:
    service = SettingsService(tmp_path / "settings.json")

    settings = service.load()

    assert settings["CurrentBroadcastPath"] == str(Path("user_data/broadcast/CurrentBroadcast.json"))
    assert settings["CurrentExpeditionPath"] == str(Path("user_data/broadcast/CurrentExpedition.json"))
    assert settings["CurrentIncidentPath"] == str(Path("user_data/broadcast/CurrentIncident.json"))
    assert settings["StreamEventsPath"] == str(Path("user_data/broadcast/StreamEvents.json"))
    assert settings["StreamSessionPath"] == str(Path("user_data/broadcast/StreamSession.json"))
    assert settings["MarkerLogPath"] == str(Path("user_data/broadcast/MarkerLog.md"))
    assert settings["FieldNoteCounterPath"] == str(Path("user_data/broadcast/FieldNoteCounter.txt"))
    assert settings["CountersFolder"] == str(Path("user_data/broadcast"))
    assert settings["NarratorContentPath"] == str(
        Path("modules/broadcast/resources/natural_history_narrator.json")
    )
    assert settings["WeatherFolder"] == str(Path("data/Weather"))
