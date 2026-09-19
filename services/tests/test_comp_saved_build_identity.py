from models.build_model import PlayerBuild
from models.comp_plan_state import CompChairState, CompPlanState
from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_team_candidate_optimizer import CompTeamCandidatePool
from services.comp_plan_autofill_service import CompPlanAutoFillService


def _saved_candidate(
    *,
    candidate_id: str = "saved:build-1",
    source_name: str = "Display Label",
    player_id: str = "player-1",
    character_id: str = "character-1",
    build_id: str = "build-1",
) -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id=candidate_id,
        name="Trial Healer",
        source_kind="saved_build",
        source_name=source_name,
        source_url="",
        eso_class="Warden",
        role="Healer",
        gear_sets=("Set A", "Set B"),
        skills=(),
        mundus="The Ritual",
        complete_build=True,
        unresolved=(),
        score=100.0,
        score_reasons=("saved build",),
        saved_player_id=player_id,
        saved_character_id=character_id,
        saved_build_id=build_id,
    )


def test_player_build_round_trips_stable_identity_without_polluting_empty_payloads() -> None:
    empty_payload = PlayerBuild(Name="Magrat", BuildName="DF Healer").to_dict()
    assert "PlayerId" not in empty_payload
    assert "CharacterId" not in empty_payload
    assert "BuildId" not in empty_payload

    build = PlayerBuild.from_dict(
        {
            "Name": "Magrat",
            "BuildName": "DF Healer",
            "PlayerId": "player-1",
            "CharacterId": "character-1",
            "BuildId": "build-1",
        }
    )
    assert build.PlayerId == "player-1"
    assert build.CharacterId == "character-1"
    assert build.BuildId == "build-1"
    payload = build.to_dict()
    assert payload["PlayerId"] == "player-1"
    assert payload["CharacterId"] == "character-1"
    assert payload["BuildId"] == "build-1"


def test_comp_autofill_binds_saved_build_by_canonical_player_identity() -> None:
    state = CompPlanState(
        raid_plan_id=None,
        raid_plan_name="Roster",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="A Display Name That Does Not Match",
                player_id="player-1",
                character_id="character-1",
                character_name="Different Character Label",
                role="Healer",
            ),
        ),
    )
    candidate = _saved_candidate(source_name="Completely Different Display Label")

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=(CompTeamCandidatePool("healer-1", (candidate,)),),
    )

    chair = result.state.chair("healer-1")
    assert chair is not None
    assert chair.selected_build_id == "build-1"
    assert chair.selected_build_name == "Trial Healer"
    assert chair.candidate_id == "saved:build-1"


def test_comp_autofill_rejects_same_display_label_when_canonical_player_differs() -> None:
    state = CompPlanState(
        raid_plan_id=None,
        raid_plan_name="Roster",
        trial_id="Sunspire",
        chairs=(
            CompChairState(
                seat_id="healer-1",
                player_name="Shared Name",
                player_id="player-1",
                character_id="character-1",
                role="Healer",
            ),
        ),
    )
    candidate = _saved_candidate(
        source_name="Shared Name",
        player_id="player-2",
        character_id="character-2",
        build_id="build-2",
        candidate_id="saved:build-2",
    )

    result = CompPlanAutoFillService().apply(
        state=state,
        pools=(CompTeamCandidatePool("healer-1", (candidate,)),),
    )

    chair = result.state.chair("healer-1")
    assert chair is not None
    assert chair.selected_build_id is None
    assert chair.selected_build_name is None
