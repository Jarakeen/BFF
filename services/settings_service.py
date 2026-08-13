# services/settings_service.py
from __future__ import annotations

import json
from pathlib import Path

try:
    import keyring
except ImportError:
    keyring = None

# ESO Logs Client Secret is kept out of settings.json (which
# often gets zipped into support bundles / synced folders)
# and stored in the OS credential vault instead, via keyring.
# If keyring isn't available on a given machine, save() falls
# back to storing it in settings.json rather than losing it
# silently -- see _save_secret()/_load_secret() below.
_KEYRING_SERVICE = "BlackFeatherFoundry"
_KEYRING_ESO_LOGS_SECRET = "EsoLogsClientSecret"


class SettingsService:
    def __init__(self, settings_path: Path) -> None:
        self.settings_path = settings_path

    def _default_settings(self) -> dict:
        return {
            "EsoLogsClientId": "",
            "EsoLogsClientSecret": "",
            "BuildsExportFolder": "",
            "CurrentExpeditionPath": str(Path("../data/CurrentExpedition.json")),
            "CurrentIncidentPath": str(Path("../data/CurrentIncident.json")),
            "FieldNoteCounterPath": str(Path("../FieldNoteCounter.txt")),
            "CountersFolder": str(Path("..")),
            "ArchiveFolder": str(Path("../Archive")),
            "WeatherFolder": str(Path("../Weather")),
            "StreamEventsPath": str(Path("..data/StreamEvents.json")),
            "StreamSessionPath": str(Path("..data/StreamSession.json")),
            "BossLogPath": str(Path("../Archive/BossLog.md")),
            "NarratorContentPath": str(Path("..natural_history_narrator.json")),
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
            "CurrentAchievementRunPath": str(Path("../data/CurrentAchievementRun.json")),
            "CurrentBroadcastPath": str(Path("..data/CurrentBroadcast.json")),
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

        data = json.loads(
    self.settings_path.read_text(
        encoding="utf-8"
    )
)

        return {
                "EsoLogsClientId": str(
                    data.get(
                        "EsoLogsClientId",
                        ""
                    )
                ),

                "EsoLogsClientSecret": self._load_secret(data),

                "BuildsExportFolder": str(
                    data.get(
                        "BuildsExportFolder",
                        ""
                    )
                ),

                "CurrentExpeditionPath": self._resolve_path(
                    data.get(
                        "CurrentExpeditionPath",
                        "../data/CurrentExpedition.json"
                    )
                ),

                "CurrentIncidentPath": self._resolve_path(
                    data.get(
                        "CurrentIncidentPath",
                        "../data/CurrentIncident.json"
                    )
                ),

                "FieldNoteCounterPath": self._resolve_path(
                    data.get(
                        "FieldNoteCounterPath",
                        "...data/FieldNoteCounter.txt"
                    )
                ),

                "CountersFolder": self._resolve_path(
                    data.get(
                        "CountersFolder",
                        ".."
                    )
                ),

                "ArchiveFolder": self._resolve_path(
                    data.get(
                        "ArchiveFolder",
                        "../Archive"
                    )
                ),

                "WeatherFolder": self._resolve_path(
                    data.get(
                        "WeatherFolder",
                        "../data/Weather"
                    )
                ),

                "StreamEventsPath": self._resolve_path(
                    data.get(
                        "StreamEventsPath",
                        "../data/StreamEvents.json"
                    )
                ),

                "StreamSessionPath": self._resolve_path(
                    data.get(
                        "StreamSessionPath",
                        "../data/StreamSession.json"
                    )
                ),

                "BossLogPath": self._resolve_path(
                    data.get(
                        "BossLogPath",
                        "../Archive/BossLog.md"
                    )
                ),

                "NarratorContentPath": self._resolve_path(
                    data.get(
                        "NarratorContentPath",
                        "data/natural_history_narrator.json"
                    )
                ),

                "AchievementRunDraftPath": self._resolve_path(
                    data.get(
                        "AchievementRunDraftPath",
                        "data/current_achievement_run.json"
                    )
                ),

                "BrbSceneName": str(
                    data.get(
                        "BrbSceneName",
                        "BRB"
                    )
                ),

                "EndOfStreamSceneName": str(
                    data.get(
                        "EndOfStreamSceneName",
                        "Ending"
                    )
                ),

                "ObsWebSocketHost": str(
                    data.get(
                        "ObsWebSocketHost",
                        "127.0.0.1"
                    )
                ),

                "ObsWebSocketPort": int(
                    data.get(
                        "ObsWebSocketPort",
                        4455
                    )
                ),

                "ObsWebSocketPassword": str(
                    data.get(
                        "ObsWebSocketPassword",
                        ""
                    )
                ),

                "GoogleCredentialsPath": self._resolve_path(
                    data.get(
                        "GoogleCredentialsPath",
                        "google_service_account.json"
                    )
                ),

                "GoogleSpreadsheetId": str(
                    data.get(
                        "GoogleSpreadsheetId",
                        ""
                    )
                ),

                "GoogleSheetsPerson": str(
                    data.get(
                        "GoogleSheetsPerson",
                        "Jarakeen"
                    )
                ),

                "AchievementProgressPath": self._resolve_path(
                    data.get(
                        "AchievementProgressPath",
                        "data/achievement_progress.json"
                    )
                ),

                "MarkerLogPath": self._resolve_path(
                    data.get(
                        "MarkerLogPath",
                        "../data/MarkerLog.md"
                    )
                ),

                "CurrentAchievementRunPath": self._resolve_path(
                    data.get(
                        "CurrentAchievementRunPath",
                        "/data/CurrentAchievementRun.json"
                    )
                ),

                "CurrentBroadcastPath": self._resolve_path(
                    data.get(
                        "CurrentBroadcastPath",
                        "data/CurrentBroadcast.json"
                    )
                ),

                "SessionArchiveFolder": self._resolve_path(
                    data.get(
                        "SessionArchiveFolder",
                        "../Archive/Sessions"
                    )
                ),

                "BffRoot": self._resolve_path(
                    data.get(
                        "BffRoot",
                        "C:\\Users\\nourg\\OneDrive\\Desktop\\BFF"
                    )
                ),
            }
        
        
        

    def save(self, settings: dict) -> None:

        settings = dict(settings)

        secret = settings.pop("EsoLogsClientSecret", "")

        stored_in_keyring = self._save_secret(secret)

        # Only if keyring truly isn't available do we fall
        # back to writing the secret into settings.json --
        # better a plaintext secret on disk than a silently
        # discarded one.
        if not stored_in_keyring:
            settings["EsoLogsClientSecret"] = secret

        self.settings_path.write_text(json.dumps(settings, ensure_ascii=False, indent=4), encoding="utf-8")

    # --------------------------------------------------
    # ESO Logs Client Secret (keyring-backed)
    # --------------------------------------------------

    def _save_secret(self, secret: str) -> bool:
        """Returns True if the secret was handed off to keyring."""

        if keyring is None:
            return False

        try:

            if secret:
                keyring.set_password(
                    _KEYRING_SERVICE,
                    _KEYRING_ESO_LOGS_SECRET,
                    secret,
                )
            else:
                keyring.delete_password(
                    _KEYRING_SERVICE,
                    _KEYRING_ESO_LOGS_SECRET,
                )

            return True

        except Exception:
            return False

    def _load_secret(self, raw_settings: dict) -> str:

        if keyring is not None:

            try:

                stored = keyring.get_password(
                    _KEYRING_SERVICE,
                    _KEYRING_ESO_LOGS_SECRET,
                )

                if stored:
                    return stored

            except Exception:
                pass

        # keyring unavailable/empty -- fall back to whatever
        # was last written to settings.json directly (only
        # happens on a machine with no OS credential vault).
        return str(raw_settings.get("EsoLogsClientSecret", ""))
