from types import SimpleNamespace

from minmax.resource_costs import BaseActionCost, ResourceType
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from models.build_model import PlayerBuild
from services.rotation_ultimate_service import RotationUltimateService


class _CostRepository:
    def resolve_name(self, name):
        return SimpleNamespace(
            name=name,
            base_cost=BaseActionCost(
                amount=250.0,
                resources=(ResourceType.ULTIMATE,),
                ability_id=1,
                rank=4,
                morph=1,
                base_mechanic=8,
            ),
            unresolved=(),
        )


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer")
    build.FrontBarSkills = ["Skill", "", "", "", "", "Aggressive Horn"]
    return build


def _plan() -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=10.0,
        actions=tuple(
            RotationAction(float(second), 0, RotationActionKind.SKILL, "Skill", "front")
            for second in range(11)
        ),
    )


def test_generation_projection_retains_spend_and_generation_evidence_when_affordable() -> None:
    event = UltimateGenerationEvent(5.0, 150.0, "verified gain")
    result = RotationUltimateService(
        ability_cost_repository=_CostRepository(),
    ).apply_generation(
        build=_build(),
        plan=_plan(),
        ultimate_bar="front",
        starting_ultimate=100.0,
        generation_events=(event,),
    )

    assert len(result.spend_rules) == 1
    assert result.spend_rules[0].skill_name == "Aggressive Horn"
    assert result.spend_rules[0].cost == 250.0
    assert result.generation_events == (event,)


def test_generation_projection_retains_spend_evidence_even_when_never_affordable() -> None:
    event = UltimateGenerationEvent(5.0, 50.0, "verified gain")
    result = RotationUltimateService(
        ability_cost_repository=_CostRepository(),
    ).apply_generation(
        build=_build(),
        plan=_plan(),
        ultimate_bar="front",
        starting_ultimate=100.0,
        generation_events=(event,),
    )

    assert result.rules == ()
    assert len(result.spend_rules) == 1
    assert result.spend_rules[0].cost == 250.0
    assert result.generation_events == (event,)
    assert any("never became affordable" in item for item in result.unresolved)
