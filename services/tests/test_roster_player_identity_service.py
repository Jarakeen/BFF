from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from models.roster_model import RosterMember
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService


def _member(name: str, *, character: str, team: str) -> RosterMember:
    return RosterMember(
        PlayerName=name,
        CharacterName=character,
        EsoClass="Warden",
        PrimaryRole="Healer",
        Team=team,
        Status="Active",
    )


def test_explicit_merge_preserves_alias_team_and_canonical_build_ownership(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    survivor_id = roster.create_member(
        _member("imyapapi", character="Current Toon", team="Swine & Punishment")
    )
    donor_id = roster.create_member(
        _member("Remains Hard", character="Old Toon", team="Performance Mode")
    )

    builds = BuildService(tmp_path / "builds.json")
    builds.save(
        BuildRoster(
            Members=[
                PlayerBuild(
                    Name="Current Toon",
                    Gamertag="imyapapi",
                    BuildName="Healer",
                    EsoClass="Warden",
                    Role="Healer",
                    Food="Ghastly Eye Bowl",
                ),
                PlayerBuild(
                    Name="Old Toon",
                    Gamertag="Remains Hard",
                    BuildName="DD",
                    EsoClass="Warden",
                    Role="Damage Dealer",
                    Food="Lava Foot Soup-And-Saltrice",
                ),
            ]
        )
    )

    service = RosterPlayerIdentityService(database, builds)
    service.add_alias(donor_id, "Ebazi", source="manual")
    result = service.merge_players(
        survivor_id=survivor_id,
        donor_id=donor_id,
        create_backups=False,
    )

    assert result.canonical_name == "imyapapi"
    assert roster.get_member(donor_id) is None
    survivor = roster.get_member(survivor_id)
    assert survivor is not None
    assert {piece.strip() for piece in survivor.Team.split(",")} == {
        "Swine & Punishment",
        "Performance Mode",
    }

    aliases = {alias.alias for alias in service.aliases_for_member(survivor_id)}
    assert aliases == {"Remains Hard", "Ebazi"}
    assert [member.PlayerName for member in service.matching_members("Remains Hard")] == [
        "imyapapi"
    ]
    assert [member.PlayerName for member in service.matching_members("Ebazi")] == [
        "imyapapi"
    ]

    saved = builds.load()
    assert len(saved.Members) == 2
    assert {member.Gamertag for member in saved.Members} == {"imyapapi"}
    catalog = builds.canonical.catalog_service.load()
    assert [player["gamertag"] for player in catalog["players"]] == ["imyapapi"]
    assert {
        character["player_id"] for character in catalog["characters"]
    } == {catalog["players"][0]["player_id"]}


def test_alias_matching_is_exact_not_fuzzy(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    member_id = roster.create_member(
        _member("imyapapi", character="Current Toon", team="Swine & Punishment")
    )
    service = RosterPlayerIdentityService(database)
    service.add_alias(member_id, "BARONZAUDRUS521")

    assert len(service.matching_members("baronzaudrus521")) == 1
    assert len(service.matching_members("@BARONZAUDRUS521")) == 1
    assert service.matching_members("BARONZAUDRUS52") == []


def test_matching_members_can_explicitly_include_archived_identity(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    roster = RosterService(database)
    member_id = roster.create_member(
        _member("Rylo", character="Archived Toon", team="Performance Mode")
    )
    service = RosterPlayerIdentityService(database)
    service.add_alias(member_id, "Old Rylo", source="former_gamertag")
    roster.archive_member(member_id)

    assert service.matching_members("Rylo") == []
    assert service.matching_members("Old Rylo") == []
    assert [row.PlayerName for row in service.matching_members(
        "Old Rylo", include_archived=True
    )] == ["Rylo"]
