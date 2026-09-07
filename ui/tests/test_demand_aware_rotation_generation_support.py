from __future__ import annotations

from types import SimpleNamespace

from models.build_model import PlayerBuild
from minmax.demand_anticipatory_duration_scheduler import DemandRefreshLead
from minmax.rotation_ability_priority import (
    AbilityPriorityEntry,
    AbilityPriorityList,
    AbilityPriorityOverride,
)
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from ui.demand_aware_rotation_generation_support import (
    DemandAwareRotationGenerationRequest,
    DemandAwareRotationGenerationSupport,
)
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = ["Budding Seeds", "Combat Prayer", "", "", "", "Aggressive Horn"]
    build.BackBarSkills = ["", "", "", "", "", "", "Barrier"]
    return build


def _priorities() -> AbilityPriorityList:
    return AbilityPriorityList(
        character_name="Magrat",
        build_name="DF Healer",
        role="Healer",
        entries=(
            AbilityPriorityEntry("front", 1, "Budding Seeds", 2),
            AbilityPriorityEntry("front", 2, "Combat Prayer", 4),
        ),
        overrides=(
            AbilityPriorityOverride(
                demand_name="Burst Window",
                bar="front",
                slot=1,
                skill_name="Budding Seeds",
                priority=0,
                reason="prepare burst healing",
            ),
            AbilityPriorityOverride(
                demand_name="Burst Window",
                bar="front",
                slot=2,
                skill_name="Combat Prayer",
                priority=6,
                reason="support can yield during burst prep",
            ),
        ),
    )


def test_wrapper_passes_full_priority_list_and_demand_windows_to_refinement() -> None:
    calls = []
    projection = SimpleNamespace(label="projection")
    evidence = SimpleNamespace(label="evidence")

    class RefinementStub:
        def refine(
            self,
            plan,
            *,
            priorities=None,
            wait_decision=None,
            demands=(),
            demand_refresh_leads=(),
        ):
            calls.append(
                (
                    plan,
                    priorities,
                    wait_decision,
                    demands,
                    demand_refresh_leads,
                )
            )
            return SimpleNamespace(plan=plan, duration_projection=projection)

    class EvidenceStub:
        def from_projection(self, received):
            assert received is projection
            return evidence

    base = RotationGenerationSupport(
        duration_refinement=RefinementStub(),
        duration_evidence=EvidenceStub(),
    )
    demand = RotationDemandWindow(
        name="Burst Window",
        start_seconds=24.0,
        end_seconds=30.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
    )
    refresh_lead = DemandRefreshLead(
        demand_name="Burst Window",
        bar="front",
        skill_name="Budding Seeds",
        lead_seconds=3.0,
    )
    priorities = _priorities()

    result = DemandAwareRotationGenerationSupport(base).generate_with_evidence(
        build=_build(),
        request=DemandAwareRotationGenerationRequest(
            base_request=RotationGenerationRequest(
                duration_seconds=30.0,
                auto_required_heavy_attacks=False,
            ),
            priorities=priorities,
            demands=(demand,),
            demand_refresh_leads=(refresh_lead,),
        ),
    )

    assert result.duration_evidence is evidence
    assert len(calls) == 1
    (
        _,
        received_priorities,
        received_wait,
        received_demands,
        received_refresh_leads,
    ) = calls[0]
    assert received_priorities is priorities
    assert received_priorities.overrides == priorities.overrides
    assert received_demands == (demand,)
    assert received_refresh_leads == (refresh_lead,)
    assert received_wait is None


def test_seed_definition_uses_base_priorities_not_demand_override() -> None:
    priorities = _priorities()
    request = DemandAwareRotationGenerationRequest(
        base_request=RotationGenerationRequest(
            duration_seconds=4.0,
            weave_light_attacks=False,
            auto_required_heavy_attacks=False,
        ),
        priorities=priorities,
        demands=(
            RotationDemandWindow(
                name="Burst Window",
                start_seconds=0.0,
                end_seconds=4.0,
                kind=RotationDemandKind.HEALING,
                pattern=RotationDemandPattern.BURST,
            ),
        ),
    )

    support = DemandAwareRotationGenerationSupport()
    definition_request = support._definition_request(request)
    definition = support.base.build_definition(build=_build(), request=definition_request)

    skill_names = [step.name for step in definition.steps if step.name]
    assert skill_names[:2] == ["Budding Seeds", "Combat Prayer"]
    assert priorities.resolve(request.demands[0])[0].entry.skill_name == "Budding Seeds"
