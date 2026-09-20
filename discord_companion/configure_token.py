from __future__ import annotations

"""One-time secure setup for Finch's Discord bot token."""

import json
from getpass import getpass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from discord_companion.config import load_config, write_example_config
from discord_companion.credentials import save_bot_token


def _normalize_token(raw: str) -> str:
    token = str(raw or "").strip().strip('"').strip("'")
    if token.lower().startswith("bot "):
        token = token[4:].strip()
    return token


def _validate_bot_token(token: str) -> tuple[bool, str]:
    request = Request(
        "https://discord.com/api/v10/users/@me",
        headers={
            "Authorization": f"Bot {token}",
            "User-Agent": "FoundryDock-Finch/1.0",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code == 401:
            return False, (
                "Discord rejected that token (401 Unauthorized). "
                "Use the Bot Token from Developer Portal > Bot, not the "
                "Application ID, Public Key, Client Secret, or install URL."
            )
        return False, f"Discord token check failed with HTTP {exc.code}."
    except URLError as exc:
        return False, f"Could not reach Discord to validate the token: {exc.reason}"
    except Exception as exc:
        return False, f"Could not validate the Discord token: {exc}"

    username = str(payload.get("username") or "Finch")
    bot_id = str(payload.get("id") or "")
    return True, f"Discord accepted the token for {username} (id={bot_id})."


def main() -> None:
    config_path = write_example_config()
    config = load_config(config_path)
    token = _normalize_token(
        getpass("Paste Finch's Discord bot token (input is hidden): ")
    )
    if not token:
        raise SystemExit("No token entered. Nothing was stored.")

    valid, message = _validate_bot_token(token)
    print(message)
    if not valid:
        raise SystemExit(1)

    save_bot_token(config, token)
    print("Finch's token was stored in the operating-system credential vault.")


if __name__ == "__main__":
    main()
