from __future__ import annotations

"""Runtime configuration for the FoundryDock Discord companion.

Bot credentials are never stored in FoundryDock user data. The token is read
from the environment variable named by token_env.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path

from services.paths import USER_DATA


DEFAULT_CONFIG_PATH = USER_DATA / "discord_companion.json"


@dataclass(frozen=True, slots=True)
class DiscordCompanionConfig:
    bot_name: str = "Finch"
    token_env: str = "FOUNDRYDOCK_DISCORD_TOKEN"
    guild_id: int | None = None
    default_channel_id: int | None = None
    team_channels: dict[str, int] = field(default_factory=dict)
    team_role_mentions: dict[str, str] = field(default_factory=dict)
    reminder_minutes: tuple[int, ...] = (1440, 60, 15)

    def channel_id_for_team(self, team_name: str) -> int | None:
        wanted = str(team_name or "").strip().casefold()
        for name, channel_id in self.team_channels.items():
            if str(name).strip().casefold() == wanted:
                return int(channel_id)
        return self.default_channel_id

    def mention_for_team(self, team_name: str) -> str:
        wanted = str(team_name or "").strip().casefold()
        for name, mention in self.team_role_mentions.items():
            if str(name).strip().casefold() == wanted:
                return str(mention or "").strip()
        return ""


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    number = int(value)
    return number if number > 0 else None


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> DiscordCompanionConfig:
    path = Path(path)
    if not path.exists():
        return DiscordCompanionConfig()

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Discord companion config must contain a JSON object.")

    team_channels_raw = payload.get("team_channels", {})
    team_mentions_raw = payload.get("team_role_mentions", {})
    reminder_raw = payload.get("reminder_minutes", (1440, 60, 15))

    if not isinstance(team_channels_raw, dict):
        raise ValueError("team_channels must be an object mapping team names to channel ids.")
    if not isinstance(team_mentions_raw, dict):
        raise ValueError("team_role_mentions must be an object mapping team names to mentions.")
    if not isinstance(reminder_raw, (list, tuple)):
        raise ValueError("reminder_minutes must be a list of minute offsets.")

    reminder_minutes = tuple(
        sorted(
            {int(value) for value in reminder_raw if int(value) >= 0},
            reverse=True,
        )
    )

    return DiscordCompanionConfig(
        bot_name=str(payload.get("bot_name") or "Finch").strip() or "Finch",
        token_env=str(payload.get("token_env") or "FOUNDRYDOCK_DISCORD_TOKEN").strip(),
        guild_id=_optional_int(payload.get("guild_id")),
        default_channel_id=_optional_int(payload.get("default_channel_id")),
        team_channels={
            str(name).strip(): int(channel_id)
            for name, channel_id in team_channels_raw.items()
            if str(name).strip() and int(channel_id) > 0
        },
        team_role_mentions={
            str(name).strip(): str(mention or "").strip()
            for name, mention in team_mentions_raw.items()
            if str(name).strip() and str(mention or "").strip()
        },
        reminder_minutes=reminder_minutes,
    )


def write_example_config(path: Path = DEFAULT_CONFIG_PATH) -> Path:
    path = Path(path)
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "bot_name": "Finch",
        "token_env": "FOUNDRYDOCK_DISCORD_TOKEN",
        "guild_id": None,
        "default_channel_id": None,
        "team_channels": {},
        "team_role_mentions": {},
        "reminder_minutes": [1440, 60, 15],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "DiscordCompanionConfig",
    "load_config",
    "write_example_config",
]
