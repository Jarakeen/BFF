from pathlib import Path

from models.build_model import PlayerBuild
from models.raid_plan import RaidPlan, RaidPlanMember
from services.saved_build_capability_service import SavedBuildCapabilityAudit
from tools.audit_raid_plan_acceptance import audit_raid_plan, _choose_plan


class _CapabilityService:
    def audit_build(self, build: PlayerBuild) -> SavedBuildCapabilityAudit:
        return SavedBuildCapabilityAudit(
            character_name=build.Name,
            build_name=build.BuildName,
            character_id=None,
            resolved_sources=(),
            resolved_effects=(),
            conditional_sources=(),
            unresolved=(),
            capability_unresolved=(),
            boundaries=(),
        )


def _powerful_assault_build() -> PlayerBuild:
    build = PlayerBuild(
        Name="Magrat",
        Gamertag="Jarakeen",
        BuildName="DF Healer",
        Role="Healer",
    )
    build.Armor["Chest"]["Set"] = "Powerful Assault"
    build.Armor["Hands"]["Set"] = "Powerful Assault"
    build.Necklace.Set = "Powerful Assault"
    build.Ring1.Set = "Powerful Assault"
    build.Ring2.Set = "Powerful Assault"
    return build


def _plan(name: str = "Performance Mode Rockgrove") -> RaidPlan:
    return RaidPlan(
        plan_id="performance-mode-rg",
        trial_id="rockgrove",
        name=name,
        team_name="Performance Mode",
        difficulty="Veteran Hardmode",
        members=(
            RaidPlanMember(
                seat_id="healer-1",
                gamertag="Jarakeen",
                character_name="Magrat",
                role="Healer",
                eso_class="Warden",
                selected_build_name="DF Healer",
                primary_assignment="Raid Healing / Support",
            ),
        ),
    )


def test_acceptance_audit_round_trips_and_reuses_exact_resolved_build() -> None:
    build = _powerful_assault_build()

    result = audit_raid_plan(
        plan=_plan(),
        saved_builds=(build,),
        capability_service=_CapabilityService(),
    )

    assert result.pipeline_ok is True
    assert result.persistence_roundtrip_ok is True
    assert result.resolved_build_count == 1
    assert result.effective_snapshot_count == 1
    assert result.unresolved == ()


def test_acceptance_audit_surfaces_powerful_assault_without_claiming_uptime() -> None:
    result = audit_raid_plan(
        plan=_plan(),
        saved_builds=(_powerful_assault_build(),),
        capability_service=_CapabilityService(),
    )

    powerful_assault = next(
        row for row in result.identified_effects if row[0] == "Powerful Assault"
    )
    assert powerful_assault[1] == "conditional"
    assert powerful_assault[2] == ("Magrat",)
    assert any(
        category == "conditional" and subject == "Powerful Assault"
        for category, subject, _recommendation in result.adviser_findings
    )


def test_acceptance_audit_reports_plan_blockers_without_failing_pipeline() -> None:
    plan = RaidPlan(
        plan_id="incomplete",
        trial_id="rockgrove",
        name="Incomplete",
        members=(RaidPlanMember(seat_id="healer-1", gamertag="Friend"),),
    )

    result = audit_raid_plan(
        plan=plan,
        saved_builds=(),
        capability_service=_CapabilityService(),
    )

    assert result.pipeline_ok is True
    assert result.resolved_build_count == 0
    assert result.adviser_blockers > 0
    assert result.unresolved


def test_choose_plan_requires_explicit_choice_when_multiple_exist() -> None:
    first = _plan("Performance Mode Rockgrove")
    second = RaidPlan(plan_id="other", trial_id="sunspire", name="Other Plan")

    assert _choose_plan((first, second), plan_id="performance-mode-rg") == first
    assert _choose_plan((first, second), plan_name="Performance Mode") == first


def test_acceptance_audit_script_bootstraps_repo_root_for_direct_execution() -> None:
    source = Path("tools/audit_raid_plan_acceptance.py").read_text(encoding="utf-8")

    root_pos = source.index("ROOT = Path(__file__).resolve().parents[1]")
    path_pos = source.index("sys.path.insert(0, str(ROOT))")
    engine_import_pos = source.index("from engine.config import")

    assert root_pos < path_pos < engine_import_pos
