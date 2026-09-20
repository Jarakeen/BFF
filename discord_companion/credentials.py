from __future__ import annotations

"""Credential storage for Finch.

The Discord bot token is treated like a password. Prefer the operating-system
credential vault through keyring. An environment variable remains a supported
non-persistent override for development and automation.
"""

import os

import keyring

from discord_companion.config import DiscordCompanionConfig


_SERVICE_NAME = "FoundryDock.Finch"


def credential_username(config: DiscordCompanionConfig) -> str:
    guild = str(config.guild_id or "default")
    return f"discord-bot-token:{guild}"


def load_bot_token(config: DiscordCompanionConfig) -> str:
    environment = os.environ.get(config.token_env, "").strip()
    if environment:
        return environment
    token = keyring.get_password(_SERVICE_NAME, credential_username(config))
    return str(token or "").strip()


def save_bot_token(config: DiscordCompanionConfig, token: str) -> None:
    token = str(token or "").strip()
    if not token:
        raise ValueError("Discord bot token cannot be blank.")
    keyring.set_password(_SERVICE_NAME, credential_username(config), token)


def delete_bot_token(config: DiscordCompanionConfig) -> None:
    try:
        keyring.delete_password(_SERVICE_NAME, credential_username(config))
    except keyring.errors.PasswordDeleteError:
        pass


__all__ = [
    "credential_username",
    "delete_bot_token",
    "load_bot_token",
    "save_bot_token",
]
