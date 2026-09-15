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
