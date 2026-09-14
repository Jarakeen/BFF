from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_saved_build_resolution_service import (
    RaidPlanSavedBuildResolutionService,
)


def _plan(*, build_name: str = "Tank Build") -> RaidPlan:
    return RaidPlan(
        plan_id="rg-plan",
        trial_id="rockgrove",
        name="Rockgrove",
        members=(
            RaidPlanMember(
                seat_id="off-tank",
                gamertag="TankPlayer",
                character_name="Rylonia",
                role="Tank",
                selected_build_name=build_name,
            ),
        ),
    )


def _build(*, build_name: str = "Tank Build", gamertag: str = "TankPlayer") -> PlayerBuild:
    return PlayerBuild(
        Name="Rylonia",
        Gamertag=gamertag,
        BuildName=build_name,
        Role="Tank",
    )


def test_resolves_exact_saved_build_for_raid_plan_seat() -> None:
    source = _build()
    result = RaidPlanSavedBuildResolutionService().resolve(
        raid_plan=_plan(),
        seat_id="OFF-TANK",
        saved_builds=(source,),
    )

    assert result.resolved is True
    assert result.unresolved == ()
    assert result.build is not None
    assert result.build.Name == "Rylonia"
    assert result.build.BuildName == "Tank Build"
    assert result.build is not source


def test_missing_selected_build_fails_closed() -> None:
    result = RaidPlanSavedBuildResolutionService().resolve(
        raid_plan=_plan(build_name=""),
        seat_id="off-tank",
        saved_builds=(_build(),),
    )

    assert result.resolved is False
    assert result.build is None
    assert "has no selected build" in result.unresolved[0]


def test_identity_mismatch_fails_closed() -> None:
    result = RaidPlanSavedBuildResolutionService().resolve(
        raid_plan=_plan(),
        seat_id="off-tank",
        saved_builds=(_build(gamertag="DifferentPlayer"),),
    )

    assert result.resolved is False
    assert result.build is None
    assert "No saved build matches" in result.unresolved[0]


def test_duplicate_exact_saved_build_identity_is_ambiguous() -> None:
    result = RaidPlanSavedBuildResolutionService().resolve(
        raid_plan=_plan(),
        seat_id="off-tank",
        saved_builds=(_build(), _build()),
    )

    assert result.resolved is False
    assert result.build is None
    assert "ambiguous" in result.unresolved[0]
