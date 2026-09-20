from __future__ import annotations

"""One-time secure setup for Finch's Discord bot token."""

from getpass import getpass

from discord_companion.config import load_config, write_example_config
from discord_companion.credentials import save_bot_token


def main() -> None:
    config_path = write_example_config()
    config = load_config(config_path)
    token = getpass("Paste Finch's Discord bot token (input is hidden): ").strip()
    save_bot_token(config, token)
    print("Finch's token was stored in the operating-system credential vault.")


if __name__ == "__main__":
    main()
