from types import SimpleNamespace

import pytest

from minmax.coverage_requirement import CoverageRequirement
from minmax.encounter_requirements import EncounterRequirementSet
from minmax.resource_costs import ResourceType
from minmax.resource_timeline import ResourceTimelineResult
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.support_coverage import SupportCoverage
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType
from services.rotation_candidate_scorecard_service import (
    RotationCandidateScorecardService,
    RotationDemandActionRequirement,
)
from services.rotation_plan_consequence_service import RotationResourceConsequenceKind


def _plan(*actions: RotationAction, unresolved=()) -> RotationPlan:
    return RotationPlan(
        character_name="Magrat",
        build_name="DF Healer",
        duration_seconds=60.0,
        actions=tuple(actions),
        unresolved=tuple(unresolved),
    )


def _sustain(*, ending: int, costs=(), shortfall: int = 0, unresolved=()):
    timeline = ResourceTimelineResult(
        resource=ResourceType.MAGICKA,
        starting_amount=30000,
        ending_amount=ending,
        events=(),
    )
    if shortfall:
        timeline = SimpleNamespace(
            starting_amount=30000,
            ending_amount=ending,
            total_shortfall=shortfall,
            events=(),
        )
    return SimpleNamespace(
        resource=ResourceType.MAGICKA,
        run=SimpleNamespace(
            timeline=timeline,
            action_cost_events=tuple(
                SimpleNamespace(source=source, amount=amount)
                for source, amount in costs
            ),
        ),
        unresolved=tuple(unresolved),
    )


def _demand() -> RotationDemandWindow:
    return RotationDemandWindow(
        name="Phase 2 healing prep",
        start_seconds=39.0,
        end_seconds=45.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )


def _buff(name: str) -> SupportEffect:
    return SupportEffect(
        source="Healer A",
        name=name,
        category=SupportEffectCategory.BUFF,
        effect_type="support",
        target_type=SupportTargetType.GROUP,
    )


def test_exact_action_inside_named_demand_satisfies_supplied_obligation() -> None:
    baseline = _plan(
        RotationAction(40.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )
    candidate = _plan(
        RotationAction(40.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
    )

    result = RotationCandidateScorecardService().compare(
        baseline_plan=baseline,
        candidate_plan=candidate,
        baseline_sustain=_sustain(ending=20000, costs=(("Combat Prayer", 3764),)),
        candidate_sustain=_sustain(ending=21771, costs=(("Budding Seeds", 1993),)),
        demands=(_demand(),),
        demand_requirements=(
            RotationDemandActionRequirement(
                demand_name="Phase 2 healing prep",
                skill_name="Budding Seeds",
                bar="front",
            ),
        ),
    )

    assert result.demand_coverage[0].satisfied is True
    assert result.demand_coverage[0].cast_times == (40.0,)
    assert result.missing_demand_requirements == ()
    assert result.supplied_obligations_satisfied is True
    assert result.consequence.resource_kind is RotationResourceConsequenceKind.IMPROVED


def test_resource_improvement_does_not_excuse_missing_demand_obligation() -> None:
    baseline = _plan(
        RotationAction(40.0, 0, RotationActionKind.SKILL, "Combat Prayer", "front"),
    )
    candidate = _plan(
        RotationAction(46.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
    )

    result = RotationCandidateScorecardService().compare(
        baseline_plan=baseline,
        candidate_plan=candidate,
        baseline_sustain=_sustain(ending=20000, costs=(("Combat Prayer", 3764),)),
        candidate_sustain=_sustain(ending=21771, costs=(("Budding Seeds", 1993),)),
        demands=(_demand(),),
        demand_requirements=(
            RotationDemandActionRequirement(
                demand_name="Phase 2 healing prep",
                skill_name="Budding Seeds",
                bar="front",
            ),
        ),
    )

    assert result.consequence.resource_kind is RotationResourceConsequenceKind.IMPROVED
    assert len(result.missing_demand_requirements) == 1
    assert result.supplied_obligations_satisfied is False


def test_static_required_effect_gap_remains_visible_separately_from_timed_demand() -> None:
    requirements = EncounterRequirementSet(
        encounter_id="xalvakka",
        encounter_name="Xalvakka",
        requirements=(
            CoverageRequirement("Major Courage"),
            CoverageRequirement("Major Breach"),
        ),
    )
    coverage = SupportCoverage.from_effects((_buff("Major Courage"),))
    candidate = _plan(
        RotationAction(40.0, 0, RotationActionKind.SKILL, "Budding Seeds", "front"),
    )

    result = RotationCandidateScorecardService().compare(
        baseline_plan=candidate,
        candidate_plan=candidate,
        baseline_sustain=_sustain(ending=20000),
        candidate_sustain=_sustain(ending=20000),
        encounter_requirements=requirements,
        support_coverage=coverage,
    )

    assert result.missing_required_effects == ("Major Breach",)
    assert result.supplied_obligations_satisfied is False


def test_demand_requirement_must_reference_supplied_window() -> None:
    plan = _plan()

    with pytest.raises(ValueError, match="unknown demand"):
        RotationCandidateScorecardService().compare(
            baseline_plan=plan,
            candidate_plan=plan,
            baseline_sustain=_sustain(ending=20000),
            candidate_sustain=_sustain(ending=20000),
            demands=(_demand(),),
            demand_requirements=(
                RotationDemandActionRequirement(
                    demand_name="Different Window",
                    skill_name="Budding Seeds",
                ),
            ),
        )
