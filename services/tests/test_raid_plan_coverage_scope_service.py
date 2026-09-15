from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_coverage_scope_service import RaidPlanCoverageScopeService


def _build(*, player: str, character: str, build_name: str) -> PlayerBuild:
    return PlayerBuild(Gamertag=player, Name=character, BuildName=build_name)


def test_scope_resolves_exact_selected_builds_and_preserves_unresolved_chairs() -> None:
    plan = RaidPlan(
        plan_id="rg-plan",
        trial_id="rockgrove",
        name="RG Plan",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                character_name="Magrat",
                selected_build_name="DF Healer",
                primary_assignment="Major Courage",
                secondary_assignment="Minor Courage",
            ),
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Friend",
                character_name="Damage Friend",
                selected_build_name="Missing Build",
                primary_assignment="Minor Brittle",
            ),
        ),
    )
    saved = (
        _build(player="Jarakeen", character="Magrat", build_name="DF Healer"),
        _build(player="Jarakeen", character="Magrat", build_name="Other Healer"),
    )

    scope = RaidPlanCoverageScopeService().compose(
        raid_plan=plan,
        saved_builds=saved,
        coverage_effect_names=("Major Courage", "Minor Brittle", "Minor Courage"),
    )

    assert scope.plan_id == "rg-plan"
    assert scope.named_members == 2
    assert len(scope.members) == 1
    assert scope.members[0].seat_id == "healer-1"
    assert scope.members[0].build.BuildName == "DF Healer"
    assert scope.primary_for("Major Courage") == ("Magrat",)
    assert scope.secondary_for("Minor Courage") == ("Magrat",)
    assert scope.primary_for("Minor Brittle") == ("Damage Friend",)
    assert len(scope.unresolved) == 1
    assert "Missing Build" in scope.unresolved[0]


def test_assignment_projection_requires_exact_coverage_label_match() -> None:
    plan = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                character_name="Magrat",
                selected_build_name="DF Healer",
                primary_assignment="Major Courage-ish",
                secondary_assignment="Major Courage",
            ),
        ),
    )

    scope = RaidPlanCoverageScopeService().compose(
        raid_plan=plan,
        saved_builds=(_build(player="Jarakeen", character="Magrat", build_name="DF Healer"),),
        coverage_effect_names=("Major Courage",),
    )

    assert scope.primary_for("Major Courage") == ()
    assert scope.secondary_for("Major Courage") == ("Magrat",)


def test_ambiguous_saved_build_selection_stays_unresolved() -> None:
    plan = RaidPlan(
        plan_id="plan",
        trial_id="rockgrove",
        name="Plan",
        members=(
            RaidPlanMember(
                seat_id="dd-1",
                gamertag="Friend",
                character_name="Same Character",
                selected_build_name="Same Build",
            ),
        ),
    )
    saved = (
        _build(player="Friend", character="Same Character", build_name="Same Build"),
        _build(player="Friend", character="Same Character", build_name="Same Build"),
    )

    scope = RaidPlanCoverageScopeService().compose(
        raid_plan=plan,
        saved_builds=saved,
        coverage_effect_names=("Major Courage",),
    )

    assert scope.members == ()
    assert len(scope.unresolved) == 1
    assert "ambiguous" in scope.unresolved[0].casefold()
