from types import SimpleNamespace

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from services.raid_plan_optimizer_adviser_service import RaidPlanOptimizerAdviserService


class _CapabilityService:
    def __init__(self, gaps=()) -> None:
        self.gaps = tuple(gaps)

    def audit_build(self, _build):
        return SimpleNamespace(
            resolved_effects=(),
            conditional_sources=(),
            boundaries=(),
            capability_resolution_gaps=self.gaps,
            capability_unresolved=self.gaps,
        )


def _build(*, name="Magrat", gamertag="Jarakeen", build_name="DF Healer") -> PlayerBuild:
    return PlayerBuild(Name=name, Gamertag=gamertag, BuildName=build_name, Role="Healer")


def _plan(build_name="DF Healer") -> RaidPlan:
    return RaidPlan(
        plan_id="performance-mode-rg",
        trial_id="rockgrove",
        name="Performance Mode - Rockgrove",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                character_name="Magrat",
                role="Healer",
                selected_build_name=build_name,
            ),
        ),
    )


def test_adviser_reports_open_chairs_and_unresolved_builds_without_mutation() -> None:
    service = RaidPlanOptimizerAdviserService(_CapabilityService())
    plan = _plan("Missing Build")

    review = service.review(raid_plan=plan, saved_builds=(_build(),))

    assert review.blocker_count >= 2
    assert any(item.subject == "11 open chair(s)" for item in review.findings)
    assert any(item.subject == "Unresolved selected build" for item in review.findings)
    assert plan.member("healer-1").selected_build_name == "Missing Build"


def test_adviser_keeps_canonical_evidence_debt_separate_from_team_change() -> None:
    service = RaidPlanOptimizerAdviserService(
        _CapabilityService(("Ability Foo does not resolve to a canonical effect",))
    )

    review = service.review(raid_plan=_plan(), saved_builds=(_build(),), total_chairs=1)

    gaps = [item for item in review.findings if item.category == "data_gap"]
    assert gaps
    assert any("Foundry" in item.recommendation for item in gaps)


def test_equipped_powerful_assault_is_advised_as_conditional_not_missing() -> None:
    build = _build()
    build.Armor["Chest"]["Set"] = "Powerful Assault"
    build.Armor["Hands"]["Set"] = "Powerful Assault"
    build.Armor["Waist"]["Set"] = "Powerful Assault"
    build.Necklace.Set = "Powerful Assault"
    build.Ring1.Set = "Powerful Assault"

    review = RaidPlanOptimizerAdviserService(_CapabilityService()).review(
        raid_plan=_plan(),
        saved_builds=(build,),
        total_chairs=1,
    )

    pa = [item for item in review.findings if item.subject == "Powerful Assault"]
    assert pa
    assert all(item.category == "conditional" for item in pa)
    assert all("uptime" in item.recommendation.casefold() or "trigger" in item.recommendation.casefold() for item in pa)


def test_adviser_is_deterministically_priority_sorted() -> None:
    review = RaidPlanOptimizerAdviserService(_CapabilityService()).review(
        raid_plan=_plan(),
        saved_builds=(),
    )

    priorities = [item.priority for item in review.findings]
    rank = {"high": 0, "medium": 1, "low": 2}
    assert [rank[value] for value in priorities] == sorted(rank[value] for value in priorities)


def test_adviser_exposes_honest_workbench_evidence_contract() -> None:
    review = RaidPlanOptimizerAdviserService(_CapabilityService()).review(
        raid_plan=_plan(),
        saved_builds=(_build(),),
        total_chairs=1,
    )

    assert review.required_effect_count > 0
    assert (
        review.covered_effect_count
        + review.conditional_effect_count
        + review.planned_unproven_effect_count
        + review.ownership_attention_effect_count
        + review.missing_effect_count
        + review.unverified_effect_count
        == review.required_effect_count
    )
    assert "verified" in review.coverage_summary
    assert all(item.current_state for item in review.findings)
    assert all(item.proposed_state for item in review.findings)
    assert all(item.confidence in {"high", "medium", "low", "unknown"} for item in review.findings)


def test_adviser_does_not_fabricate_numeric_performance_gains() -> None:
    review = RaidPlanOptimizerAdviserService(_CapabilityService()).review(
        raid_plan=_plan(),
        saved_builds=(_build(),),
        total_chairs=1,
    )

    rendered = "\n".join(
        value
        for item in review.findings
        for value in (
            item.recommendation,
            item.evidence,
            item.current_state,
            item.proposed_state,
        )
    )
    assert "% group DPS" not in rendered
    assert "projected DPS" not in rendered


def test_assigned_but_unproven_provider_is_not_reported_as_unassigned_missing() -> None:
    plan = RaidPlan(
        plan_id="assigned-plan",
        trial_id="rockgrove",
        name="Assigned Plan",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                character_name="Magrat",
                role="Healer",
                selected_build_name="DF Healer",
                primary_assignment="Major Courage",
                assignment_source="WW",
            ),
        ),
    )

    review = RaidPlanOptimizerAdviserService(_CapabilityService()).review(
        raid_plan=plan,
        saved_builds=(_build(),),
        total_chairs=1,
    )

    major_courage = [
        item for item in review.findings if item.subject == "Major Courage"
    ]
    assert major_courage
    assert any(item.current_state == "Assigned provider; source unproven" for item in major_courage)
    assert all(item.category != "coverage_gap" for item in major_courage)
    assert review.planned_unproven_effect_count >= 1


def test_planned_support_gear_is_reviewed_as_conditional_provider_evidence() -> None:
    plan = RaidPlan(
        plan_id="planned-gear",
        trial_id="rockgrove",
        name="Planned Gear",
        members=(
            RaidPlanMember(
                seat_id="tank-1",
                gamertag="Tank",
                character_name="Tank",
                role="Tank",
                selected_build_name="Tank Plan",
                planned_gear_sets=("Powerful Assault",),
            ),
        ),
    )
    build = PlayerBuild(
        Name="Tank",
        Gamertag="Tank",
        BuildName="Tank Plan",
        Role="Tank",
    )

    review = RaidPlanOptimizerAdviserService(_CapabilityService()).review(
        raid_plan=plan,
        saved_builds=(build,),
        total_chairs=1,
    )

    powerful_assault = [
        item for item in review.findings if item.subject == "Powerful Assault"
    ]
    assert powerful_assault
    assert all(item.category == "conditional" for item in powerful_assault)
    assert any(
        item.current_state == "Provider exists; ownership unassigned"
        for item in powerful_assault
    )
