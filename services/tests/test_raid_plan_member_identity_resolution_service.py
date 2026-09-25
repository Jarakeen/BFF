from pathlib import Path

from models.build_model import BuildRoster, PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from models.roster_model import RosterMember
from services.build_service import BuildService
from services.eso_database import EsoDatabase
from services.raid_plan_member_identity_resolution_service import (
    RaidPlanMemberIdentityResolutionService,
)
from services.raid_plan_repository import RaidPlanRepository
from services.roster_service import RosterService


def _build_state(tmp_path: Path):
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
    catalog = builds.canonical.catalog_service
    player = catalog.list_players()[0]
    character = catalog.characters_for_player(player["player_id"])[0]
    build = catalog.load()["builds"][0]
    return builds, player, character, build


def test_stable_ids_resolve_across_personnel_character_and_build(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    builds, player, character, build = _build_state(tmp_path)
    roster = RosterService(database)
    roster_member_id = roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            CanonicalPlayerId=player["player_id"],
            CanonicalCharacterId=character["character_id"],
        )
    )

    member = RaidPlanMember(
        seat_id="healer-1",
        gamertag="Display Name Only",
        roster_member_id=roster_member_id,
        player_id=player["player_id"],
        character_id=character["character_id"],
        selected_build_id=build["build_id"],
        selected_build_name="Legacy display name",
    )
    result = RaidPlanMemberIdentityResolutionService(database, builds).resolve(member)

    assert result.resolved
    assert result.roster_member_id == roster_member_id
    assert result.player_id == player["player_id"]
    assert result.character_id == character["character_id"]
    assert result.selected_build_id == build["build_id"]


def test_page_scoped_resolver_reuses_personnel_and_one_catalog_snapshot(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    builds, player, character, build = _build_state(tmp_path)
    roster = RosterService(database)
    member_id = roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            CharacterName="Magrat",
            CanonicalPlayerId=player["player_id"],
            CanonicalCharacterId=character["character_id"],
        )
    )
    snapshot = builds.canonical.catalog_service.load_strict()
    def unexpected_catalog_reload():
        raise AssertionError("identity resolution reloaded the catalog")
    builds.canonical.catalog_service.load_strict = unexpected_catalog_reload
    resolver = RaidPlanMemberIdentityResolutionService(
        database, builds, roster_service=roster, catalog_snapshot=snapshot,
    )

    assert resolver.roster is roster
    result = resolver.resolve(RaidPlanMember(
        seat_id="healer-1", gamertag="Jarakeen",
        roster_member_id=member_id, player_id=player["player_id"],
        character_id=character["character_id"], selected_build_id=build["build_id"],
    ))
    assert result.resolved
    assert result.selected_build_id == build["build_id"]


def test_personnel_schema_removes_obsolete_unique_player_index_only_once(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "personnel.db")
    RosterService(database)
    database.execute(
        "CREATE UNIQUE INDEX roster_member_canonical_player_id_unique "
        "ON roster_member(canonical_player_id) WHERE canonical_player_id <> ''"
    )
    database.commit()
    statements = []
    database.connection.set_trace_callback(statements.append)

    RosterService(database)
    RosterService(database)

    assert sum("DROP INDEX roster_member_canonical_player_id_unique" in sql for sql in statements) == 1


def test_stable_id_contradictions_fail_closed_without_name_fallback(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    builds, player, character, build = _build_state(tmp_path)
    roster = RosterService(database)
    roster_member_id = roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            CharacterName="Magrat",
            CanonicalPlayerId=player["player_id"],
            CanonicalCharacterId=character["character_id"],
        )
    )

    member = RaidPlanMember(
        seat_id="healer-1",
        gamertag="Jarakeen",
        roster_member_id=roster_member_id,
        player_id="wrong-player-id",
        character_id=character["character_id"],
        selected_build_id=build["build_id"],
    )
    result = RaidPlanMemberIdentityResolutionService(database, builds).resolve(member)

    assert not result.resolved
    assert any("disagrees with Personnel" in item for item in result.unresolved)
    assert any("does not exist" in item for item in result.unresolved)


def test_build_id_can_supply_character_player_and_bound_roster_without_name_inference(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    builds, player, character, build = _build_state(tmp_path)
    roster = RosterService(database)
    roster_member_id = roster.create_member(
        RosterMember(
            PlayerName="A Display Label That Does Not Match",
            CharacterName="Also Not Used For The Join",
            CanonicalPlayerId=player["player_id"],
            CanonicalCharacterId=character["character_id"],
        )
    )

    member = RaidPlanMember(
        seat_id="healer-1",
        gamertag="Completely Different Display Text",
        selected_build_id=build["build_id"],
    )
    result = RaidPlanMemberIdentityResolutionService(database, builds).resolve(member)

    assert result.resolved
    assert result.roster_member_id == roster_member_id
    assert result.selected_build_id == build["build_id"]
    assert result.character_id == character["character_id"]
    assert result.player_id == player["player_id"]


def test_player_only_identity_does_not_guess_one_of_multiple_roster_characters(tmp_path: Path) -> None:
    database = EsoDatabase(tmp_path / "eso.db")
    builds, player, _character, _build = _build_state(tmp_path)
    roster = RosterService(database)
    roster.create_member(
        RosterMember(PlayerName="Jarakeen", CharacterName="Magrat", CanonicalPlayerId=player["player_id"])
    )
    roster.create_member(
        RosterMember(PlayerName="Jarakeen", CharacterName="Other Toon", CanonicalPlayerId=player["player_id"])
    )

    member = RaidPlanMember(
        seat_id="healer-1",
        gamertag="Jarakeen",
        player_id=player["player_id"],
    )
    result = RaidPlanMemberIdentityResolutionService(database, builds).resolve(member)

    assert result.resolved
    assert result.player_id == player["player_id"]
    assert result.character_id is None
    assert result.roster_member_id is None


def test_raid_plan_repository_round_trips_player_id_and_loads_legacy_member(tmp_path: Path) -> None:
    path = tmp_path / "raid_plans.json"
    repository = RaidPlanRepository(path)
    plan = RaidPlan(
        plan_id="rockgrove-pm",
        trial_id="rockgrove",
        name="Performance Mode",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                player_id="player-123",
                character_id="character-123",
                selected_build_id="build-123",
            ),
        ),
    )
    repository.save(plan)

    loaded = repository.get(plan.plan_id)
    assert loaded is not None
    assert loaded.members[0].player_id == "player-123"

    path.write_text(
        '{"schema_version": 1, "plans": [{"plan_id": "legacy", "trial_id": "rockgrove", '
        '"name": "Legacy", "members": [{"seat_id": "dd-1", "gamertag": "Old Name"}], '
        '"triggered_responsibilities": []}]}',
        encoding="utf-8",
    )
    legacy = repository.get("legacy")
    assert legacy is not None
    assert legacy.members[0].player_id is None
