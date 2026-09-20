from __future__ import annotations

from pathlib import Path

from models.comp_plan_state import CompChairState, CompPlanState
from services.build_catalog_service import BuildCatalogService
from services.comp_build_persistence_service import CompBuildPersistenceService


def _seed_catalog(tmp_path: Path) -> tuple[str, str]:
    catalog = BuildCatalogService(tmp_path / "characters.json")
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


def test_comp_save_creates_real_canonical_build_and_assigns_id(tmp_path: Path) -> None:
    player_id, character_id = _seed_catalog(tmp_path)

    result = CompBuildPersistenceService(tmp_path).persist(
        _state(player_id, character_id)
    )

    chair = result.state.chair("DD1")
    assert chair is not None
    assert chair.selected_build_id
    assert chair.build_source_kind == "comp_build"

    catalog = BuildCatalogService(tmp_path / "characters.json").load()
    row = next(
        build
        for build in catalog["builds"]
        if build["build_id"] == chair.selected_build_id
    )
    assert row["character_id"] == character_id
    assert row["build_kind"] == "comp"
    assert row["legacy"]["PlannedGearSets"] == ["Corpseburster", "Null Arca"]
    assert row["legacy"]["Mundus"] == "The Thief"
    assert row["source"]["kind"] == "comp_maker"


def test_resaving_comp_chair_updates_same_build_id(tmp_path: Path) -> None:
    player_id, character_id = _seed_catalog(tmp_path)
    service = CompBuildPersistenceService(tmp_path)

    first = service.persist(_state(player_id, character_id))
    first_chair = first.state.chair("DD1")
    assert first_chair is not None and first_chair.selected_build_id

    changed = first.state.with_chair(
        first_chair.with_changes(
            planned_gear_sets=("Corpseburster", "Powerful Assault")
        )
    )
    second = service.persist(changed)
    second_chair = second.state.chair("DD1")
    assert second_chair is not None
    assert second_chair.selected_build_id == first_chair.selected_build_id

    catalog = BuildCatalogService(tmp_path / "characters.json").load()
    comp_rows = [
        row
        for row in catalog["builds"]
        if row.get("build_kind") == "comp"
        and row.get("character_id") == character_id
    ]
    assert len(comp_rows) == 1
    assert comp_rows[0]["legacy"]["PlannedGearSets"] == [
        "Corpseburster",
        "Powerful Assault",
    ]


def test_recruit_chair_does_not_create_build(tmp_path: Path) -> None:
    _seed_catalog(tmp_path)
    state = CompPlanState(
        raid_plan_id="plan-1",
        raid_plan_name="Performance Mode",
        trial_id="Rockgrove",
        chairs=(
            CompChairState(
                seat_id="DD1",
                player_name="Recruitment Needed",
                role="DD",
                planned_gear_sets=("Corpseburster", "Null Arca"),
            ),
        ),
        dirty=True,
    )

    result = CompBuildPersistenceService(tmp_path).persist(state)

    assert result.saved_seats == ()
    assert result.skipped_seats == ("DD1",)
    assert BuildCatalogService(tmp_path / "characters.json").load()["builds"] == []
