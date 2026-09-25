from __future__ import annotations

from pathlib import Path

from models.comp_plan_state import CompChairState, CompPlanState
from models.roster_model import RosterMember
from services.build_catalog_service import BuildCatalogService
from services.build_service import BuildService
from services.canonical_build_bridge import CanonicalBuildBridge
from services.comp_build_persistence_service import CompBuildPersistenceService
from services.eso_database import EsoDatabase
from services.roster_player_identity_service import RosterPlayerIdentityService
from services.roster_service import RosterService


def _service(tmp_path: Path) -> CompBuildPersistenceService:
    return CompBuildPersistenceService(
        tmp_path,
        database_path=tmp_path / "foundrydock.db",
    )


def _seed_catalog(tmp_path: Path) -> tuple[str, str]:
    catalog = BuildCatalogService(tmp_path / "foundrydock.db")
    player_id = "player-rylo"
    character_id = "character-rylo"
    catalog.save(
        {
            "schema_version": 4,
            "players": [
                {
                    "player_id": player_id,
                    "gamertag": "Rylo",
                    "display_name": "Rylo",
                }
            ],
            "characters": [
                {
                    "character_id": character_id,
                    "player_id": player_id,
                    "name": "Rylo Character",
                    "gamertag": "Rylo",
                    "eso_class": "Arcanist",
                    "role": "DD",
                }
            ],
            "builds": [],
            "team_assignments": [],
        }
    )
    return player_id, character_id


def _state(player_id: str, character_id: str) -> CompPlanState:
    return CompPlanState(
        raid_plan_id="plan-1",
        raid_plan_name="Performance Mode",
        trial_id="Rockgrove",
        chairs=(
            CompChairState(
                seat_id="DD1",
                player_name="Rylo",
                player_id=player_id,
                character_id=character_id,
                character_name="Rylo Character",
                role="DD",
                eso_class="Arcanist",
                planned_gear_sets=("Corpseburster", "Null Arca"),
                planned_mundus="The Thief",
            ),
        ),
        dirty=True,
    )


def test_planned_comp_save_keeps_plan_state_without_creating_build(tmp_path: Path) -> None:
    player_id, character_id = _seed_catalog(tmp_path)

    result = _service(tmp_path).persist(_state(player_id, character_id))

    chair = result.state.chair("DD1")
    assert chair is not None
    assert chair.player_id == player_id
    assert chair.character_id == character_id
    assert chair.selected_build_id is None
    assert chair.build_source_kind == "planned"
    assert chair.planned_gear_sets == ("Corpseburster", "Null Arca")
    assert chair.planned_mundus == "The Thief"
    assert BuildCatalogService(tmp_path / "foundrydock.db").load()["builds"] == []


def test_resaving_planned_comp_chair_does_not_create_build(tmp_path: Path) -> None:
    player_id, character_id = _seed_catalog(tmp_path)
    service = _service(tmp_path)

    first = service.persist(_state(player_id, character_id))
    chair = first.state.chair("DD1")
    assert chair is not None
    changed = first.state.with_chair(
        chair.with_changes(planned_gear_sets=("Corpseburster", "Powerful Assault"))
    )

    second = service.persist(changed)
    revised = second.state.chair("DD1")
    assert revised is not None
    assert revised.selected_build_id is None
    assert revised.build_source_kind == "planned"
    assert revised.planned_gear_sets == ("Corpseburster", "Powerful Assault")
    assert BuildCatalogService(tmp_path / "foundrydock.db").load()["builds"] == []


def test_comp_save_promotes_personnel_identity_without_inventing_build(tmp_path: Path) -> None:
    database_path = tmp_path / "foundrydock.db"
    roster = RosterService(EsoDatabase(database_path))
    member_id = roster.create_member(
        RosterMember(
            PlayerName="Jarakeen",
            CharacterName="Magrat",
            EsoClass="Warden",
            PrimaryRole="Healer",
            Status="Active",
        )
    )
    state = CompPlanState(
        raid_plan_id="plan-sunspire",
        raid_plan_name="Performance Mode GS",
        trial_id="sunspire",
        chairs=(
            CompChairState(
                seat_id="Healer1",
                player_name="Jarakeen",
                roster_member_id=member_id,
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                planned_gear_sets=("Perfected Grand Rejuvenation", "Spell Power Cure"),
            ),
        ),
        dirty=True,
    )

    result = _service(tmp_path).persist(state)
    chair = result.state.chair("Healer1")
    assert chair is not None
    assert chair.player_id and chair.character_id
    assert chair.selected_build_id is None
    assert chair.build_source_kind == "planned"

    rebound = roster.get_member(member_id)
    assert rebound is not None
    assert rebound.CanonicalPlayerId == chair.player_id
    assert rebound.CanonicalCharacterId == chair.character_id
    assert BuildCatalogService(database_path).load()["builds"] == []


def test_comp_save_can_promote_personnel_without_character_name(tmp_path: Path) -> None:
    database_path = tmp_path / "foundrydock.db"
    roster = RosterService(EsoDatabase(database_path))
    member_id = roster.create_member(
        RosterMember(
            PlayerName="Rikbacon",
            CharacterName="",
            EsoClass="Dragonknight",
            PrimaryRole="Tank",
        )
    )
    state = CompPlanState(
        raid_plan_id="plan-sunspire",
        raid_plan_name="Performance Mode GS",
        trial_id="sunspire",
        chairs=(
            CompChairState(
                seat_id="Tank1",
                player_name="Rikbacon",
                roster_member_id=member_id,
                role="Tank",
                eso_class="Dragonknight",
                planned_gear_sets=("Turning Tide",),
            ),
        ),
        dirty=True,
    )

    result = _service(tmp_path).persist(state)
    chair = result.state.chair("Tank1")
    assert chair is not None and chair.character_id
    assert chair.selected_build_id is None
    catalog = BuildCatalogService(database_path).load()
    character = next(row for row in catalog["characters"] if row["character_id"] == chair.character_id)
    assert character["name"] == ""
    assert catalog["builds"] == []


def test_selected_saved_build_remains_reference_not_comp_copy(tmp_path: Path) -> None:
    player_id, character_id = _seed_catalog(tmp_path)
    catalog_service = BuildCatalogService(tmp_path / "foundrydock.db")
    catalog = catalog_service.load()
    build_id = "saved-build-rylo"
    catalog["builds"] = [
        {
            "build_id": build_id,
            "character_id": character_id,
            "name": "Rylo — Necromancer DD",
            "build_kind": "saved",
            "payload": {
                "BuildId": build_id,
                "CharacterId": character_id,
                "PlayerId": player_id,
                "BuildName": "Rylo — Necromancer DD",
                "Gamertag": "Rylo",
                "Name": "Rylo Character",
            },
            "legacy": {},
            "source": {},
        }
    ]
    catalog_service.save(catalog)
    base = _state(player_id, character_id)
    chair = base.chair("DD1")
    assert chair is not None
    state = base.with_chair(
        chair.with_changes(
            selected_build_id=build_id,
            selected_build_name="Rylo — Necromancer DD",
            build_source_kind="saved_build",
        )
    )

    result = _service(tmp_path).persist(state)
    revised = result.state.chair("DD1")
    assert revised is not None
    assert revised.selected_build_id == build_id
    assert revised.build_source_kind == "saved_build"
    after = BuildCatalogService(tmp_path / "foundrydock.db").load()
    assert [row["build_id"] for row in after["builds"]] == [build_id]
    assert after["builds"][0]["build_kind"] == "saved"


def test_legacy_comp_build_is_detached_not_deleted(tmp_path: Path) -> None:
    player_id, character_id = _seed_catalog(tmp_path)
    catalog_service = BuildCatalogService(tmp_path / "foundrydock.db")
    catalog = catalog_service.load()
    catalog["builds"] = [
        {
            "build_id": "legacy-comp",
            "character_id": character_id,
            "name": "Core Team • DD1",
            "build_kind": "comp",
            "payload": {},
            "legacy": {},
            "source": {"kind": "comp_maker", "plan_id": "plan-1", "seat_id": "DD1"},
        }
    ]
    catalog_service.save(catalog)
    base = _state(player_id, character_id)
    chair = base.chair("DD1")
    assert chair is not None
    state = base.with_chair(
        chair.with_changes(
            selected_build_id="legacy-comp",
            selected_build_name="Core Team • DD1",
            build_source_kind="comp_build",
        )
    )

    result = _service(tmp_path).persist(state)
    revised = result.state.chair("DD1")
    assert revised is not None
    assert revised.selected_build_id is None
    assert revised.build_source_kind == "planned"
    assert revised.planned_gear_sets == ("Corpseburster", "Null Arca")
    assert [row["build_id"] for row in catalog_service.load()["builds"]] == ["legacy-comp"]


def test_persist_reports_exact_skip_reasons_for_open_and_unplanned_chairs(tmp_path: Path) -> None:
    service = CompBuildPersistenceService(tmp_path, database_path=tmp_path / "foundrydock.db")
    state = CompPlanState(
        raid_plan_id="pm",
        raid_plan_name="Core Team",
        trial_id="sunspire",
        chairs=(
            CompChairState(
                seat_id="dd-8",
                role="DD",
                player_name="Recruit",
            ),
            CompChairState(
                seat_id="dd-7",
                role="DD",
                player_name="Known Player",
                roster_member_id=999,
            ),
        ),
    )

    result = service.persist(state)

    assert result.saved_seats == ()
    assert result.skipped_seats == ("dd-8", "dd-7")
    assert result.skipped_reasons == (
        ("dd-8", "open/recruit chair"),
        ("dd-7", "Personnel row 999 does not exist"),
    )


def test_persist_repairs_exact_personnel_alias_before_skipping_comp_build(tmp_path: Path) -> None:
    database_path = tmp_path / "foundrydock.db"
    database = EsoDatabase(database_path)
    roster = RosterService(database)
    survivor_id = roster.create_member(
        RosterMember(
            PlayerName="Pippin Feux",
            CharacterName="Pippin NB DD",
            EsoClass="Nightblade",
            PrimaryRole="DD",
            Team="Performance Mode",
        )
    )
    survivor = roster.get_member(survivor_id)
    assert survivor is not None

    identity = RosterPlayerIdentityService(database, None)
    identity.add_alias(survivor_id, "Pippin", source="manual_merge")

    service = CompBuildPersistenceService(tmp_path, database_path=database_path)
    state = CompPlanState(
        raid_plan_id="pm",
        raid_plan_name="Core Team",
        trial_id="sunspire",
        chairs=(
            CompChairState(
                seat_id="dd-5",
                role="DD",
                player_name="Pippin",
                character_name="Pippin NB DD",
                eso_class="Nightblade",
                planned_gear_sets=("Perfected Slivers of the Null Arca", "Aegis Caller"),
            ),
        ),
    )

    result = service.persist(state)

    assert result.saved_seats == ("dd-5",)
    assert result.skipped_seats == ()
    repaired = result.state.chair("dd-5")
    assert repaired is not None
    assert repaired.player_name == "Pippin Feux"
    assert repaired.roster_member_id == survivor_id
    assert repaired.selected_build_id is None
    assert repaired.build_source_kind == "planned"


def test_new_roster_player_without_canonical_ids_gets_identity_not_comp_build(tmp_path: Path) -> None:
    database_path = tmp_path / "foundrydock.db"
    roster = RosterService(EsoDatabase(database_path))
    member_id = roster.create_member(
        RosterMember(
            PlayerName="New DD",
            CharacterName="New DD Character",
            EsoClass="Nightblade",
            PrimaryRole="DD",
        )
    )
    state = CompPlanState(
        raid_plan_id="pm",
        raid_plan_name="Core Team",
        trial_id="sunspire",
        chairs=(
            CompChairState(
                seat_id="dd-5",
                player_name="New DD",
                planned_gear_sets=("Aegis Caller",),
            ),
        ),
    )

    result = _service(tmp_path).persist(state)

    assert result.saved_seats == ("dd-5",)
    assert result.skipped_seats == ()
    chair = result.state.chair("dd-5")
    assert chair is not None
    assert chair.roster_member_id == member_id
    assert chair.player_id and chair.character_id
    assert chair.selected_build_id is None
    assert chair.build_source_kind == "planned"
    assert BuildCatalogService(database_path).load()["builds"] == []


def test_unmatched_comp_player_reports_name_without_creating_duplicate_identity(tmp_path: Path) -> None:
    state = CompPlanState(
        raid_plan_id="pm",
        raid_plan_name="Core Team",
        trial_id="sunspire",
        chairs=(
            CompChairState(
                seat_id="dd-8",
                player_name="New Player",
                planned_gear_sets=("Aegis Caller",),
            ),
        ),
    )

    result = _service(tmp_path).persist(state)

    assert result.saved_seats == ()
    assert result.skipped_reasons == (
        ("dd-8", "no active Personnel record matches 'New Player'; check the saved player name"),
    )
    assert BuildCatalogService(tmp_path / "foundrydock.db").load()["players"] == []
