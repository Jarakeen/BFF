from __future__ import annotations

from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.finch_api_client import FinchGearNeedRequest
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
