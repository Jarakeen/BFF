# services/settings_service.py
from __future__ import annotations

import json
from pathlib import Path


class SettingsService:
    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path

    def _default_settings(self) -> dict:
        return {
            "CurrentExpeditionPath": str(Path("../Foundry/CurrentExpedition.json")),
            "CurrentIncidentPath": str(Path("../Foundry/CurrentIncident.json")),
            "FieldNoteCounterPath": str(Path("../FieldNoteCounter.txt")),
            "CountersFolder": str(Path("..")),
            "ArchiveFolder": str(Path("../Archive")),
            "WeatherFolder": str(Path("../Weather")),
            "StreamEventsPath": str(Path("../Foundry/StreamEvents.json")),
            "StreamSessionPath": str(Path("../Foundry/StreamSession.json")),
            "BossLogPath": str(Path("../Archive/BossLog.md")),
            "NarratorContentPath": str(Path("data/natural_history_narrator.json")),
            "AchievementRunDraftPath": str(Path("data/current_achievement_run.json")),
            "BrbSceneName": "BRB",
            "EndOfStreamSceneName": "Ending",
            "ObsWebSocketHost": "127.0.0.1",
            "ObsWebSocketPort": 4455,
            "ObsWebSocketPassword": "",
            "GoogleCredentialsPath": str(Path("google_service_account.json")),
            "GoogleSpreadsheetId": "",
            "GoogleSheetsPerson": "Jarakeen",
            "AchievementProgressPath": str(Path("data/achievement_progress.json")),
            "MarkerLogPath": str(Path("../Foundry/MarkerLog.md")),
            "CurrentAchievementRunPath": str(Path("../Foundry/CurrentAchievementRun.json")),
            "CurrentBroadcastPath": str(Path("../Foundry/CurrentBroadcast.json")),
            "SessionArchiveFolder": str(Path("../Archive/Sessions")),
            "BffRoot": str(Path("C:\\Users\\nourg\\OneDrive\\Desktop\\BFF"))
        }

    def _resolve_path(self, value: str) -> str:
        cleaned = str(value).strip().strip('"').strip("'")
        candidate = Path(cleaned)
        if candidate.is_absolute():
            return str(candidate)
        return str(self.settings_path.parent / candidate)

    def load(self) -> dict:
        if not self.settings_path.exists():
            return self._default_settings()

        data = json.loads(self.settings_path.read_text(encoding="utf-8"))
        return {
            "CurrentExpeditionPath": self._resolve_path(data.get("CurrentExpeditionPath", "../Foundry/CurrentExpedition.json")),
            "CurrentIncidentPath": self._resolve_path(data.get("CurrentIncidentPath", "../Foundry/CurrentIncident.json")),
            "FieldNoteCounterPath": self._resolve_path(data.get("FieldNoteCounterPath", "../FieldNoteCounter.txt")),
            "CountersFolder": self._resolve_path(data.get("CountersFolder", "..")),
            "ArchiveFolder": self._resolve_path(data.get("ArchiveFolder", "../Archive")),
            "WeatherFolder": self._resolve_path(data.get("WeatherFolder", "../Weather")),
            "StreamEventsPath": self._resolve_path(data.get("StreamEventsPath", "../Foundry/StreamEvents.json")),
            "StreamSessionPath": self._resolve_path(data.get("StreamSessionPath", "../Foundry/StreamSession.json")),
            "BossLogPath": self._resolve_path(data.get("BossLogPath", "../Archive/BossLog.md")),
            "NarratorContentPath": self._resolve_path(data.get("NarratorContentPath", "data/natural_history_narrator.json")),
            "AchievementRunDraftPath": self._resolve_path(data.get("AchievementRunDraftPath", "data/current_achievement_run.json")),
            "BrbSceneName": str(data.get("BrbSceneName", "BRB")),
            "EndOfStreamSceneName": str(data.get("EndOfStreamSceneName", "Ending")),
            "ObsWebSocketHost": str(data.get("ObsWebSocketHost", "127.0.0.1")),
            "ObsWebSocketPort": int(data.get("ObsWebSocketPort", 4455)),
            "ObsWebSocketPassword": str(data.get("ObsWebSocketPassword", "")),
            "GoogleCredentialsPath": self._resolve_path(data.get("GoogleCredentialsPath", "google_service_account.json")),
            "GoogleSpreadsheetId": str(data.get("GoogleSpreadsheetId", "")),
            "GoogleSheetsPerson": str(data.get("GoogleSheetsPerson", "Jarakeen")),
            "AchievementProgressPath": self._resolve_path(data.get("AchievementProgressPath", "data/achievement_progress.json")),
            "MarkerLogPath": self._resolve_path(data.get("MarkerLogPath", "../Foundry/MarkerLog.md")),
            "CurrentAchievementRunPath": self._resolve_path(data.get("CurrentAchievementRunPath", "../Foundry/CurrentAchievementRun.json")),
            "CurrentBroadcastPath": self._resolve_path(data.get("CurrentBroadcastPath", "../Foundry/CurrentBroadcast.json")),
            "SessionArchiveFolder": self._resolve_path(data.get("SessionArchiveFolder", "../Archive/Sessions")),
            "BffRoot": self._resolve_path(data.get("BffRoot", "C:\\Users\\nourg\\OneDrive\\Desktop\\BFF"))
        }
    
    

    def save(self, settings: dict) -> None:
        self.settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=4), encoding="utf-8")
