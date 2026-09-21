from __future__ import annotations

from models.roster_model import RosterMember
from services.eso_database import EsoDatabase
from services.roster_assignment_context_service import RosterAssignmentContextService
from services.roster_duplicate_player_merge_service import merge_duplicate_roster_players
from services.roster_service import RosterService


def test_duplicate_gamertag_merges_teams_roles_and_assignments(tmp_path) -> None:
    database = EsoDatabase(tmp_path / "roster.db")
    roster = RosterService(database)
    context = RosterAssignmentContextService(database)

    survivor_id = roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            SecondaryRole="Damage Dealer",
            Team="Disappointing Feral, Swine & Punishment",
        )
    )
    duplicate_id = roster.create_member(
        RosterMember(
            PlayerName="@jarakeen",
            CharacterName="Magrat SW Hlz",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Team="Swine & Punishment",
        )
    )

    roster.set_member_assignment_field(duplicate_id, "notes", "legacy SW note")
    context.set_field(
        duplicate_id,
        team_name="Swine & Punishment",
        field="primary_assignment",
        value="Pilly",
    )
    context.set_field(
        duplicate_id,
        team_name="Swine & Punishment",
        encounter_id="lylanar_turlassil",
        field="notes",
        value="Twins ice/fire job",
    )

    result = merge_duplicate_roster_players(database, create_backup=False)

    assert result.groups_merged == 1
    assert result.rows_removed == 1
    assert result.survivor_ids == (survivor_id,)

    members = roster.list_members()
    assert len(members) == 1
    merged = members[0]
    assert merged.PlayerName == "Jarakeen"
    assert merged.CharacterName == "Magrat"
    assert merged.Team == "Disappointing Feral, Swine & Punishment"
    assert merged.PrimaryRole == "Healer"
    assert merged.SecondaryRole == "DD"
    assert roster.get_member_assignment(survivor_id)["notes"] == "legacy SW note"

    assert context.get_effective_assignment(
        survivor_id,
        team_name="Swine & Punishment",
        legacy_service=roster,
    )["primary_assignment"] == "Pilly"
    assert context.get_effective_assignment(
        survivor_id,
        team_name="Swine & Punishment",
        encounter_id="lylanar_turlassil",
        legacy_service=roster,
    )["notes"] == "Twins ice/fire job"


def test_duplicate_merge_is_idempotent(tmp_path) -> None:
    database = EsoDatabase(tmp_path / "roster.db")
    roster = RosterService(database)
    roster.create_member(RosterMember(PlayerName="Fu", CharacterName="Fu Arc DD", Team="Swine & Punishment"))

    result = merge_duplicate_roster_players(database, create_backup=False)

    assert result.groups_merged == 0
    assert result.rows_removed == 0
    assert len(roster.list_members()) == 1
