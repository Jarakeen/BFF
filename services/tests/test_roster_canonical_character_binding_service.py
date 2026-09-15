from pathlib import Path

import pytest

from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_canonical_character_binding_service import (
    RosterCanonicalCharacterBindingService,
)
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
                ),
                PlayerBuild(
                    Name="Mustrum",
                    Gamertag="Jarakeen",
                    BuildName="Tank",
                    EsoClass="Dragonknight",
                    Role="Tank",
                ),
                PlayerBuild(
                    Name="Rylonia",
                    Gamertag="Rylo",
                    BuildName="Corpsebuster DD",
                    EsoClass="Necromancer",
                    Role="Damage Dealer",
                ),
            ]
        )
    )
    return builds


def _member(player: str, character: str) -> RosterMember:
    return RosterMember(PlayerName=player, CharacterName=character, Status="Active")


def _character_by_name(builds: BuildService, name: str) -> dict:
    catalog = builds.canonical.catalog_service.load()
    return next(row for row in catalog["characters"] if row["name"] == name)


def test_character_binding_derives_canonical_player_owner(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    member_id = roster.create_member(_member("Jarakeen", "Magrat"))
    builds = _builds(tmp_path)
    character = _character_by_name(builds, "Magrat")

    service = RosterCanonicalCharacterBindingService(database, builds)
    result = service.bind(
        roster_member_id=member_id,
        canonical_character_id=character["character_id"],
    )

    member = roster.get_member(member_id)
    assert result.canonical_character_id == character["character_id"]
    assert result.canonical_player_id == character["player_id"]
    assert member.CanonicalCharacterId == character["character_id"]
    assert member.CanonicalPlayerId == character["player_id"]
    assert service.binding_for_member(member_id) == result


def test_same_player_can_bind_multiple_distinct_characters(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    first = roster.create_member(_member("Jarakeen", "Magrat"))
    second = roster.create_member(_member("Jarakeen", "Mustrum"))
    builds = _builds(tmp_path)
    magrat = _character_by_name(builds, "Magrat")
    mustrum = _character_by_name(builds, "Mustrum")
    service = RosterCanonicalCharacterBindingService(database, builds)

    service.bind(roster_member_id=first, canonical_character_id=magrat["character_id"])
    service.bind(roster_member_id=second, canonical_character_id=mustrum["character_id"])

    first_member = roster.get_member(first)
    second_member = roster.get_member(second)
    assert first_member.CanonicalPlayerId == second_member.CanonicalPlayerId
    assert first_member.CanonicalCharacterId != second_member.CanonicalCharacterId


def test_character_binding_fails_closed_on_duplicate_or_player_mismatch(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    first = roster.create_member(_member("Jarakeen", "Magrat"))
    second = roster.create_member(_member("Jarakeen", "Other"))
    builds = _builds(tmp_path)
    magrat = _character_by_name(builds, "Magrat")
    rylonia = _character_by_name(builds, "Rylonia")
    characters = RosterCanonicalCharacterBindingService(database, builds)
    players = RosterCanonicalPlayerBindingService(database, builds)

    characters.bind(roster_member_id=first, canonical_character_id=magrat["character_id"])
    with pytest.raises(ValueError, match="already bound"):
        characters.bind(roster_member_id=second, canonical_character_id=magrat["character_id"])

    players.bind(roster_member_id=second, canonical_player_id=rylonia["player_id"])
    with pytest.raises(ValueError, match="conflicts"):
        characters.bind(roster_member_id=second, canonical_character_id=magrat["character_id"])


def test_player_binding_cannot_break_existing_character_owner(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    member_id = roster.create_member(_member("Jarakeen", "Magrat"))
    builds = _builds(tmp_path)
    magrat = _character_by_name(builds, "Magrat")
    rylonia = _character_by_name(builds, "Rylonia")
    characters = RosterCanonicalCharacterBindingService(database, builds)
    players = RosterCanonicalPlayerBindingService(database, builds)

    characters.bind(roster_member_id=member_id, canonical_character_id=magrat["character_id"])

    with pytest.raises(ValueError, match="conflicts"):
        players.bind(roster_member_id=member_id, canonical_player_id=rylonia["player_id"])
    with pytest.raises(ValueError, match="clear the canonical character"):
        players.clear(roster_member_id=member_id)

    characters.clear(roster_member_id=member_id)
    players.clear(roster_member_id=member_id)
    assert roster.get_member(member_id).CanonicalCharacterId == ""
    assert roster.get_member(member_id).CanonicalPlayerId == ""
