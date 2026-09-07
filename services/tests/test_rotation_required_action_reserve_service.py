from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from models.build_model import PlayerBuild
from services.rotation_candidate_scorecard_service import RotationDemandActionRequirement
from services.rotation_required_action_reserve_service import RotationRequiredActionReserveService


class _StubSustainService:
    def __init__(self, *, events=(), unresolved=()):
        self.events = tuple(events)
        self.unresolved = tuple(unresolved)
        self.plan = None

    def evaluate(self, *, build, plan, resource):
        self.plan = plan
        return SimpleNamespace(
            run=SimpleNamespace(action_cost_events=self.events),
            unresolved=self.unresolved,
        )


def _build() -> PlayerBuild:
    build = PlayerBuild()
    build.Name = "Magrat"
    build.BuildName = "DF Healer"
    return build


def _event(source: str, amount: int):
    return SimpleNamespace(source=source, amount=amount)


def test_single_required_cast_derives_exact_canonical_cost_floor() -> None:
    sustain = _StubSustainService(events=(_event("Budding Seeds", 1993),))
    service = RotationRequiredActionReserveService(sustain)

    result = service.derive(
        build=_build(),
        demand_name="Phase 2 healing prep",
        requirements=(
            RotationDemandActionRequirement(
                demand_name="Phase 2 healing prep",
                skill_name="Budding Seeds",
                bar="front",
            ),
        ),
    )

    assert result.minimum_amount == 1993
    assert result.action_costs == (("Budding Seeds", 1, 1993),)
    assert result.blocking_unresolved == ()
    assert result.context_notes == ()
    assert result.unresolved == ()
    assert result.as_requirement().minimum_amount == 1993
    assert sustain.plan.duration_seconds > 0
    assert sustain.plan.actions[0].time_seconds == 0.0
    assert sustain.plan.actions[0].name == "Budding Seeds"


def test_multiple_required_casts_sum_their_resolved_resource_costs() -> None:
    sustain = _StubSustainService(
        events=(
            _event("Budding Seeds", 1993),
            _event("Budding Seeds", 1993),
            _event("Combat Prayer", 3764),
        )
    )
    service = RotationRequiredActionReserveService(sustain)

    result = service.derive(
        build=_build(),
        demand_name="Burst window",
        requirements=(
            RotationDemandActionRequirement(
                demand_name="Burst window",
                skill_name="Budding Seeds",
                minimum_casts=2,
            ),
            RotationDemandActionRequirement(
                demand_name="Burst window",
                skill_name="Combat Prayer",
                minimum_casts=1,
            ),
        ),
        resource=ResourceType.MAGICKA,
    )

    assert result.minimum_amount == 7750
    assert result.action_costs == (
        ("Budding Seeds", 2, 3986),
        ("Combat Prayer", 1, 3764),
    )
    assert result.resolved is True


def test_missing_cost_event_keeps_derivation_unresolved_and_blocks_requirement() -> None:
    service = RotationRequiredActionReserveService(
        _StubSustainService(
            events=(),
            unresolved=("Budding Seeds: action cost could not be resolved",),
        )
    )

    result = service.derive(
        build=_build(),
        demand_name="Phase 2 healing prep",
        requirements=(
            RotationDemandActionRequirement(
                demand_name="Phase 2 healing prep",
                skill_name="Budding Seeds",
            ),
        ),
    )

    assert result.resolved is False
    assert any("action cost could not be resolved" in item for item in result.blocking_unresolved)
    assert any(
        "expected 1 canonical magicka cost event(s), resolved 0" in item
        for item in result.blocking_unresolved
    )
    with pytest.raises(ValueError, match="unresolved action costs"):
        result.as_requirement()


def test_cost_relevant_armor_progression_uncertainty_stays_blocking() -> None:
    service = RotationRequiredActionReserveService(
        _StubSustainService(
            events=(_event("Budding Seeds", 1993),),
            unresolved=(
                "rotation sustain currently infers equipped armor skill-line ownership; canonical character-owned progression adoption is still incomplete",
                "Champion Point is dynamic or not yet stat-mapped: Celerity",
                "Potion selected; activation/uptime is not part of static build state: spell power",
            ),
        )
    )

    result = service.derive(
        build=_build(),
        demand_name="Phase 2 healing prep",
        requirements=(
            RotationDemandActionRequirement(
                demand_name="Phase 2 healing prep",
                skill_name="Budding Seeds",
            ),
        ),
    )

    assert result.resolved is False
    assert result.blocking_unresolved == (
        "rotation sustain currently infers equipped armor skill-line ownership; canonical character-owned progression adoption is still incomplete",
    )
    assert len(result.context_notes) == 2
    with pytest.raises(ValueError, match="unresolved action costs"):
        result.as_requirement()


def test_unrelated_context_warnings_remain_visible_without_blocking_resolved_cost() -> None:
    service = RotationRequiredActionReserveService(
        _StubSustainService(
            events=(_event("Budding Seeds", 1993),),
            unresolved=(
                "Champion Point is dynamic or not yet stat-mapped: Master Gatherer",
                "Champion Point is dynamic or not yet stat-mapped: Celerity",
                "Potion selected; activation/uptime is not part of static build state: spell power",
            ),
        )
    )

    result = service.derive(
        build=_build(),
        demand_name="Phase 2 healing prep",
        requirements=(
            RotationDemandActionRequirement(
                demand_name="Phase 2 healing prep",
                skill_name="Budding Seeds",
            ),
        ),
    )

    assert result.resolved is True
    assert result.blocking_unresolved == ()
    assert len(result.context_notes) == 3
    assert result.as_requirement().minimum_amount == 1993


def test_demand_requires_matching_explicit_action_obligation() -> None:
    service = RotationRequiredActionReserveService(_StubSustainService())

    with pytest.raises(ValueError, match="no explicit action requirements"):
        service.derive(
            build=_build(),
            demand_name="Phase 2 healing prep",
            requirements=(
                RotationDemandActionRequirement(
                    demand_name="Different demand",
                    skill_name="Budding Seeds",
                ),
            ),
        )
