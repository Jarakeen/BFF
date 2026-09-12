from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_healer_canonical_role_output_factory_service import (
    RotationHealerCanonicalRoleOutputFactoryService,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
    RotationHealerExternalConditionalDemandAssumption,
)
from services.rotation_healer_demand_criteria_service import (
    RotationCandidateHealerCriteriaHardObligationService,
    RotationHealerDemandCriterion,
    RotationHealerDemandCriterionSourceKind,
)
from services.service_catalog import EvidenceClass, canonical_service_for


_HEALING_DEMAND = RotationDemandWindow(
    name="reviewed healing window",
    start_seconds=10.0,
    end_seconds=15.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
    target_count=12,
)


class _StaticContext:
    def __init__(self, *, front=object(), back=object(), unresolved=()):
        self.front = front
        self.back = back
        self.unresolved = tuple(unresolved)

    def context_for(self, bar):
        return {"front": self.front, "back": self.back}.get(bar)


class _StaticContextService:
    def __init__(self, result):
        self.result = result
        self.builds = []

    def resolve(self, build):
        self.builds.append(build)
        return self.result


class _DemandEvidenceProvider:
    def evaluate_demand(self, *, candidate, demand):
        return RotationHealerDemandHealingEvidence(
            demand=demand,
            direct_events=(),
            periodic_events=(),
            delayed_events=(),
            modeled_direct_healing=2500.0,
            modeled_periodic_healing=1500.0,
            modeled_delayed_healing=0.0,
            unresolved=(),
        )


class _DemandEvidenceFactory:
    def __init__(self):
        self.calls = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return _DemandEvidenceProvider()


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="healer-candidate",
        plan=RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=60.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _service(static_context, demand_factory=None):
    return RotationHealerCanonicalRoleOutputFactoryService(
        database_path="unused.sqlite",
        static_context_service=_StaticContextService(static_context),
        demand_evidence_factory=demand_factory or _DemandEvidenceFactory(),
    )


def test_factory_composes_multi_demand_healer_output_from_explicit_evidence() -> None:
    front = object()
    back = object()
    static = _StaticContext(front=front, back=back)
    demand_factory = _DemandEvidenceFactory()
    service = _service(static, demand_factory)
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    observation = object()
    assumption = RotationHealerExternalConditionalDemandAssumption(
        effect_name="minor_lifesteal",
        active_attacker_count=8,
    )

    result = service.build(
        build=build,
        demands=(_HEALING_DEMAND,),
        reviewed_runtime_observations=(observation,),  # type: ignore[arg-type]
        external_conditional_assumptions=(assumption,),
    )

    assert result.ready is True
    assert result.unresolved == ()
    assert result.context_relevance.relevant == ()
    assert result.role_output_provider is not None
    assert len(demand_factory.calls) == 1
    call = demand_factory.calls[0]
    assert call["build"] is build
    assert call["context"] is front
    assert call["contexts_by_bar"] == {"front": front, "back": back}
    assert call["reviewed_runtime_observations"] == (observation,)
    assert call["external_conditional_assumptions"] == (assumption,)

    output = result.evaluate_windows(_candidate())
    assert output.unresolved == ()
    assert output.weakest_window_value == pytest.approx(800.0)


def test_relevant_static_context_gap_remains_role_output_blocker() -> None:
    static = _StaticContext(unresolved=("unknown healing potency modifier",))
    result = _service(static).build(
        build=PlayerBuild(Role="Healer"),
        demands=(_HEALING_DEMAND,),
    )

    assert result.ready is False
    assert result.unresolved == ("unknown healing potency modifier",)
    assert result.role_output_provider is not None

    candidate = _candidate()
    output = result.evaluate_windows(candidate)
    assert output.weakest_window_value is None
    assert output.unresolved == (
        "static healer-output context: unknown healing potency modifier",
    )
    assert output.windows[0].modeled_healing_per_demand_second is None
    assert output.windows[0].unresolved == output.unresolved

    plan_output = result.evaluate_plan(candidate)
    assert plan_output.candidate_id == candidate.candidate_id
    assert plan_output.value is None
    assert plan_output.unresolved == output.unresolved

    hard_gate = RotationCandidateHealerCriteriaHardObligationService(
        multi_demand_output_service=result,  # type: ignore[arg-type]
        criteria=(
            RotationHealerDemandCriterion(
                demand_name=_HEALING_DEMAND.name,
                minimum_modeled_healing_per_demand_second=500.0,
                source_kind=(
                    RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE
                ),
                provenance=("encounter_fact=reviewed_healer_floor",),
            ),
        ),
    )
    hard_result = hard_gate.evaluate_plan(candidate)
    assert hard_result.satisfied is None
    assert any(
        "static healer-output context: unknown healing potency modifier" in reason
        for reason in hard_result.reasons
    )


def test_proven_ambient_static_gap_does_not_block_healer_output() -> None:
    message = "movement_speed unresolved: test fixture"
    static = _StaticContext(unresolved=(message,))
    result = _service(static).build(
        build=PlayerBuild(Role="Healer"),
        demands=(_HEALING_DEMAND,),
    )

    assert result.ready is True
    assert result.unresolved == ()
    assert result.context_relevance.ambient == (message,)
    assert result.evaluate_windows(_candidate()).weakest_window_value == pytest.approx(
        800.0
    )


def test_missing_bar_context_fails_closed_before_provider_construction() -> None:
    demand_factory = _DemandEvidenceFactory()
    result = _service(
        _StaticContext(back=None),
        demand_factory,
    ).build(
        build=PlayerBuild(Role="Healer"),
        demands=(_HEALING_DEMAND,),
    )

    assert result.ready is False
    assert result.role_output_provider is None
    assert result.demand_evidence_provider is None
    assert result.unresolved == ("back canonical static context is unavailable",)
    assert demand_factory.calls == []
    with pytest.raises(ValueError, match="back canonical static context"):
        result.evaluate_windows(_candidate())


def test_factory_rejects_non_healing_demand_policy() -> None:
    damage = RotationDemandWindow(
        name="damage window",
        start_seconds=0.0,
        end_seconds=5.0,
        kind=RotationDemandKind.DAMAGE,
        pattern=RotationDemandPattern.BURST,
    )

    with pytest.raises(ValueError, match="only healing demands"):
        _service(_StaticContext()).build(
            build=PlayerBuild(Role="Healer"),
            demands=(damage,),
        )


def test_factory_is_registered_as_shared_canonical_service() -> None:
    descriptor = canonical_service_for(
        "rotation_healer_canonical_role_output_composition"
    )

    assert descriptor is not None
    assert descriptor.service_id == "rotation.healer.canonical_role_output_factory"
    assert descriptor.evidence_class is EvidenceClass.MIXED
    assert descriptor.roles == ("Healer",)
    assert descriptor.encounter_aware is True
    assert "caller policy" in descriptor.notes
