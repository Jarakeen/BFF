from pathlib import Path

import pytest

from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_canonical_player_binding_service import (
    RosterCanonicalPlayerBindingService,
)
from services.roster_service import RosterService


def _builds(tmp_path: Path) -> BuildService:
    builds = BuildService(tmp_path / "builds.json")
    builds.save(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Magrat",
                    Gamertag="Jarakeen",
                    BuildName="DF Healer",
                    EsoClass="Warden",
                    Role="Healer",
                )
            ]
        )
    )
    return builds


def _member(name: str, character: str) -> RosterMember:
    return RosterMember(
        PlayerName=name,
        CharacterName=character,
        EsoClass="Warden",
        PrimaryRole="Healer",
    )


def test_explicit_binding_uses_stable_catalog_player_id(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    member_id = roster.create_member(_member("Jarakeen", "Magrat"))
    builds = _builds(tmp_path)
    player = builds.canonical.catalog_service.list_players()[0]

    service = RosterCanonicalPlayerBindingService(database, builds)
    result = service.bind(
        roster_member_id=member_id,
        canonical_player_id=player["player_id"],
    )

    assert result.roster_member_id == member_id
    assert result.canonical_player_id == player["player_id"]
    assert result.gamertag == "Jarakeen"
    assert roster.get_member(member_id).CanonicalPlayerId == player["player_id"]
    assert service.binding_for_member(member_id) == result


def test_binding_fails_closed_on_unknown_player_but_allows_multiple_character_rows(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    first = roster.create_member(_member("Jarakeen", "Magrat"))
    second = roster.create_member(_member("Jarakeen", "Second Character"))
    builds = _builds(tmp_path)
    player_id = builds.canonical.catalog_service.list_players()[0]["player_id"]
    service = RosterCanonicalPlayerBindingService(database, builds)

    with pytest.raises(ValueError, match="does not exist"):
        service.bind(roster_member_id=first, canonical_player_id="missing-player")

    service.bind(roster_member_id=first, canonical_player_id=player_id)
    service.bind(roster_member_id=second, canonical_player_id=player_id)

    assert roster.get_member(first).CanonicalPlayerId == player_id
    assert roster.get_member(second).CanonicalPlayerId == player_id


def test_binding_can_be_cleared_without_deleting_identity(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    member_id = roster.create_member(_member("Jarakeen", "Magrat"))
    builds = _builds(tmp_path)
    player_id = builds.canonical.catalog_service.list_players()[0]["player_id"]
    service = RosterCanonicalPlayerBindingService(database, builds)

    service.bind(roster_member_id=member_id, canonical_player_id=player_id)
    service.clear(roster_member_id=member_id)

    assert service.binding_for_member(member_id) is None
    assert roster.get_member(member_id).CanonicalPlayerId == ""
    assert builds.canonical.catalog_service.get_player(player_id) is not None


def test_roster_schema_upgrade_adds_canonical_identity_links_without_guessing(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    database.execute(
        """
        CREATE TABLE roster_member (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            character_name TEXT,
            eso_class TEXT,
            primary_role TEXT,
            secondary_role TEXT,
            status TEXT NOT NULL DEFAULT 'Active'
        )
        """
    )
    database.execute(
        """
        INSERT INTO roster_member (
            player_name, character_name, eso_class, primary_role, secondary_role, status
        ) VALUES ('Jarakeen', 'Magrat', 'Warden', 'Healer', '', 'Active')
        """
    )
    database.commit()

    roster = RosterService(database)
    member = roster.list_members()[0]

    assert member.PlayerName == "Jarakeen"
    assert member.CanonicalPlayerId == ""
    assert member.CanonicalCharacterId == ""
