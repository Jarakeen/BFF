from pathlib import Path

from discord_companion.registrations import FinchRegistrationStore
from models.roster_model import RosterMember


class FakeRoster:
    def list_team_names(self):
        return ["Performance Mode"]

    def list_members(self):
        return [
            RosterMember(
                Id=7,
                PlayerName="AAA Aces",
                Team="Performance Mode",
                DiscordName="aces",
                CanonicalPlayerId="player-aces",
            )
        ]


def test_register_get_unregister(tmp_path: Path) -> None:
    store = FinchRegistrationStore(
        path=tmp_path / "discord_registrations.json",
        roster_service=FakeRoster(),
    )

    saved = store.register(
        discord_user_id=123,
        guild_id=456,
        team_name="performance mode",
        player_ref="aces",
    )

    assert saved.player_name == "AAA Aces"
    assert saved.team_name == "Performance Mode"
    assert store.get(discord_user_id=123, guild_id=456) == saved
    assert store.unregister(discord_user_id=123, guild_id=456) is True
    assert store.get(discord_user_id=123, guild_id=456) is None
