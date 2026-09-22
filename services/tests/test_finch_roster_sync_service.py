from __future__ import annotations

from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.finch_api_client import (
    FinchGearNeedRequest,
    FinchRegistration,
    FinchRegistrationHistory,
)
from services.finch_roster_sync_service import FinchRosterSyncService
from services.roster_assignment_context_service import RosterAssignmentContextService
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService


class FakeFinchClient:
    def __init__(self, requests):
        self.requests = tuple(requests)
        self.acks: list[tuple[int, str, str]] = []

    def pending_gear_needs(self):
        return self.requests

    def registrations_private(self):
        return ()

    def acknowledge_gear_need(self, request_id, *, status, message=""):
        self.acks.append((int(request_id), str(status), str(message)))


def _request(
    request_id: int = 1,
    *,
    team: str = "Performance Mode",
    player: str = "Rylo",
    gear: str = "Coral Riptide",
):
    return FinchGearNeedRequest(
        request_id=request_id,
        discord_user_id=111,
        guild_id=222,
        team_name=team,
        player_name=player,
        gear_needed=gear,
    )


def _member(name: str, *, team: str = "Performance Mode", character: str = "Main"):
    return RosterMember(
        PlayerName=name,
        CharacterName=character,
        EsoClass="Arcanist",
        PrimaryRole="Damage Dealer",
        Team=team,
        Status="Active",
    )


def _services(tmp_path, requests):
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    identity = RosterPlayerIdentityService(database)
    assignments = RosterAssignmentContextService(database)
    client = FakeFinchClient(requests)
    sync = FinchRosterSyncService(
        client=client,
        roster=roster,
        identity=identity,
        assignments=assignments,
    )
    return database, roster, identity, assignments, client, sync


def test_sync_applies_exact_active_team_match_and_acks_after_write(tmp_path) -> None:
    _db, roster, _identity, assignments, client, sync = _services(
        tmp_path, [_request()]
    )
    member_id = roster.create_member(_member("Rylo"))

    summary = sync.sync_gear_needs()

    assert summary.fetched == 1
    assert summary.applied == 1
    assert summary.rejected == 0
    assert summary.errors == 0
    assert assignments.get_effective_assignment(
        member_id,
        team_name="Performance Mode",
        legacy_service=roster,
    )["gear_needed"] == "Coral Riptide"
    assert client.acks[0][0:2] == (1, "applied")


def test_sync_uses_explicit_alias_but_never_fuzzy_matching(tmp_path) -> None:
    _db, roster, identity, assignments, client, sync = _services(
        tmp_path,
        [
            _request(request_id=1, player="Old Rylo", gear="Pearls"),
            _request(request_id=2, player="Old Ryl", gear="Should Not Match"),
        ],
    )
    member_id = roster.create_member(_member("Rylo"))
    identity.add_alias(member_id, "Old Rylo", source="former_gamertag")

    summary = sync.sync_gear_needs()

    assert summary.applied == 1
    assert summary.rejected == 1
    assert assignments.get_effective_assignment(
        member_id,
        team_name="Performance Mode",
        legacy_service=roster,
    )["gear_needed"] == "Pearls"
    assert [ack[1] for ack in client.acks] == ["applied", "rejected"]
    assert "not known" in summary.results[1].message


def test_sync_rejects_archived_identity_instead_of_reactivating_it(tmp_path) -> None:
    _db, roster, _identity, _assignments, client, sync = _services(
        tmp_path, [_request()]
    )
    member_id = roster.create_member(_member("Rylo"))
    roster.archive_member(member_id)

    summary = sync.sync_gear_needs()

    assert summary.applied == 0
    assert summary.rejected == 1
    assert "archived Personnel" in summary.results[0].message
    assert client.acks[0][1] == "rejected"


def test_sync_rejects_player_not_on_requested_team(tmp_path) -> None:
    _db, roster, _identity, _assignments, client, sync = _services(
        tmp_path, [_request(team="Performance Mode")]
    )
    roster.create_member(_member("Rylo", team="Disappointing Feral"))
    roster.ensure_team_name("Performance Mode")

    summary = sync.sync_gear_needs()

    assert summary.rejected == 1
    assert "not assigned to team" in summary.results[0].message
    assert client.acks[0][1] == "rejected"


def test_sync_rejects_ambiguous_personnel_rows_in_same_team(tmp_path) -> None:
    _db, roster, _identity, _assignments, client, sync = _services(
        tmp_path, [_request()]
    )
    roster.create_member(_member("Rylo", character="Main"))
    roster.create_member(_member("Rylo", character="Alt"))

    summary = sync.sync_gear_needs()

    assert summary.rejected == 1
    assert "ambiguous" in summary.results[0].message
    assert client.acks[0][1] == "rejected"


def test_sync_does_not_ack_success_when_local_write_fails(tmp_path) -> None:
    _db, roster, _identity, assignments, client, sync = _services(
        tmp_path, [_request()]
    )
    roster.create_member(_member("Rylo"))

    def fail_write(*args, **kwargs):
        raise RuntimeError("disk/database write failed")

    assignments.set_field = fail_write

    summary = sync.sync_gear_needs()

    assert summary.errors == 1
    assert summary.applied == 0
    assert client.acks == []
    assert "write failed" in summary.results[0].message



class RegistrationFinchClient(FakeFinchClient):
    def __init__(self, registrations):
        super().__init__(())
        self.registrations = tuple(registrations)

    def registrations_private(self):
        return self.registrations


def test_registration_sync_binds_by_discord_id_and_preserves_private_alias_history(tmp_path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    identity = RosterPlayerIdentityService(database)
    assignments = RosterAssignmentContextService(database)
    member_id = roster.create_member(_member("Rylo"))

    first = FinchRegistration(
        discord_user_id=777,
        guild_id=888,
        team_name="Performance Mode",
        player_name="Rylo",
        discord_username="old.user",
        discord_display_name="Old Nick",
        identity_history=(
            FinchRegistrationHistory(
                kind="discord_username",
                value="old.user",
                first_seen="2026-01-01T00:00:00+00:00",
                last_seen="2026-01-01T00:00:00+00:00",
            ),
            FinchRegistrationHistory(
                kind="gamertag",
                value="Rylo",
                first_seen="2026-01-01T00:00:00+00:00",
                last_seen="2026-01-01T00:00:00+00:00",
            ),
        ),
    )
    client = RegistrationFinchClient((first,))
    sync = FinchRosterSyncService(
        client=client,
        roster=roster,
        identity=identity,
        assignments=assignments,
    )

    fetched, applied, unresolved = sync.sync_registration_identities()

    assert (fetched, applied, unresolved) == (1, 1, 0)
    assert roster.get_member(member_id).DiscordName == "Old Nick"

    second = FinchRegistration(
        discord_user_id=777,
        guild_id=888,
        team_name="Performance Mode",
        player_name="Brand New Gamertag",
        discord_username="new.user",
        discord_display_name="New Nick",
        identity_history=(
            FinchRegistrationHistory(kind="discord_username", value="old.user"),
            FinchRegistrationHistory(kind="discord_username", value="new.user"),
            FinchRegistrationHistory(kind="discord_display_name", value="Old Nick"),
            FinchRegistrationHistory(kind="discord_display_name", value="New Nick"),
            FinchRegistrationHistory(kind="gamertag", value="Rylo"),
            FinchRegistrationHistory(kind="gamertag", value="Brand New Gamertag"),
        ),
    )
    client.registrations = (second,)

    fetched, applied, unresolved = sync.sync_registration_identities()

    assert (fetched, applied, unresolved) == (1, 1, 0)
    updated = roster.get_member(member_id)
    assert updated.DiscordName == "New Nick"
    aliases = {row.alias for row in identity.aliases_for_member(member_id)}
    assert "old.user" in aliases
    assert "new.user" in aliases
    assert "Old Nick" in aliases
    assert "New Nick" in aliases
    assert "Brand New Gamertag" in aliases

    binding = database.execute(
        """
        SELECT roster_member_id
        FROM finch_discord_identity_binding
        WHERE discord_user_id = ? AND guild_id = ?
        """,
        (777, 888),
    ).fetchone()
    assert int(binding["roster_member_id"]) == member_id
