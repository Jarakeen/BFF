from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
    RotationCandidateRoleOutputEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidatePlanEvidence,
)
from services.rotation_healer_demand_criteria_service import (
    RotationCandidateHealerCriteriaHardObligationService,
    RotationHealerDemandCriterion,
    RotationHealerDemandCriterionSourceKind,
)
from services.rotation_recovery_heavy_candidate_orchestration_service import (
    RecoveryHeavyStabilizedCandidateSnapshot,
)
from ui.rotation_generate_healer_role_evidence_support import (
    RotationGenerateHealerRoleEvidenceSupport,
)


_HEALING = RotationDemandWindow(
    name="healing window",
    start_seconds=10.0,
    end_seconds=15.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
    target_count=12,
)
_DAMAGE = RotationDemandWindow(
    name="damage window",
    start_seconds=20.0,
    end_seconds=25.0,
    kind=RotationDemandKind.DAMAGE,
    pattern=RotationDemandPattern.BURST,
)


class _RoleOutputFactory:
    def __init__(self, result=None):
        self.result = result or SimpleNamespace(
            role_output_provider=object(),
            unresolved=(),
        )
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _PlanEvidenceFactory:
    def __init__(self):
        self.calls = []
        self.result = object()

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _CanonicalPlanProvider(RotationCandidateCanonicalPlanEvidenceService):
    def __init__(self) -> None:
        self.calls = []

    def evaluate_plan(self, candidate):
        self.calls.append(candidate)
        return RotationCandidatePlanEvidence(
            sustain=object(),  # type: ignore[arg-type]
            role_output_value=111.0,
            sustain_margin=1000.0,
        )


class _CanonicalPlanFactory:
    def __init__(self) -> None:
        self.calls = []
        self.result = _CanonicalPlanProvider()

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _RuntimeRoleOutputResult:
    role_output_provider = object()
    unresolved = ()

    def __init__(self) -> None:
        self.calls = []

    def evaluate_plan(self, candidate, *, runtime_build_context_resolver=None):
        self.calls.append((candidate, runtime_build_context_resolver))
        value = 111.0
        if runtime_build_context_resolver is not None:
            resolved = runtime_build_context_resolver(12.0, 2)
            assert resolved.context == "runtime-healer-context"
            value = 777.0
        return RotationCandidateRoleOutputEvidence(
            candidate_id=candidate.candidate_id,
            value=value,
        )


class _RuntimeBuildContextService:
    def __init__(self) -> None:
        self.calls = []

    def resolve(self, build, **kwargs):
        self.calls.append((build, kwargs))
        kwargs["runtime_combat_state_resolver"](
            kwargs["time_seconds"],
            kwargs["sequence"],
        )
        return SimpleNamespace(context="runtime-healer-context")


def _bundle(*demands):
    return SimpleNamespace(
        demands=tuple(demands),
        resource=ResourceType.MAGICKA,
        content_type="trial",
    )


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="final-healer",
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Runtime Healer",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def test_generate_healer_composer_joins_exact_build_and_healing_demands() -> None:
    role_factory = _RoleOutputFactory()
    plan_factory = _PlanEvidenceFactory()
    runtime = object()
    delayed = object()
    channel = object()
    reviewed_channel = object()
    external = object()
    support = RotationGenerateHealerRoleEvidenceSupport(
        role_output_factory=role_factory,
        plan_evidence_factory=plan_factory,
        reviewed_runtime_observations=(runtime,),  # type: ignore[arg-type]
        delayed_runtime_evidence=(delayed,),  # type: ignore[arg-type]
        channel_runtime_evidence=(channel,),  # type: ignore[arg-type]
        reviewed_channel_observations=(reviewed_channel,),  # type: ignore[arg-type]
        external_conditional_assumptions=(external,),  # type: ignore[arg-type]
        reliable_group_healing=True,
        exception_contexts=("split_assignment", "split_assignment"),
    )
    build = PlayerBuild(Role="Healer")

    evidence = support.compose(
        player_build=build,
        evidence_bundle=_bundle(_HEALING, _DAMAGE),  # type: ignore[arg-type]
    )

    assert len(role_factory.calls) == 1
    assert role_factory.calls[0] == {
        "build": build,
        "demands": (_HEALING,),
        "reviewed_runtime_observations": (runtime,),
        "delayed_runtime_evidence": (delayed,),
        "channel_runtime_evidence": (channel,),
        "reviewed_channel_observations": (reviewed_channel,),
        "external_conditional_assumptions": (external,),
    }
    assert plan_factory.calls == [
        {
            "build": build,
            "resource": ResourceType.MAGICKA,
            "role_output_evidence_provider": role_factory.result,
        }
    ]
    assert evidence.plan_evidence_provider is plan_factory.result
    assert evidence.role_key == "healer"
    assert evidence.content_type == "trial"
    assert evidence.role_output_label == "healing demand coverage"
    assert evidence.assigned_support_label == "assigned support coverage"
    assert evidence.reliable_group_healing is True
    assert evidence.exception_contexts == ("split_assignment",)


def test_generate_healer_composer_requires_explicit_healer_role() -> None:
    support = RotationGenerateHealerRoleEvidenceSupport(
        role_output_factory=_RoleOutputFactory(),
        plan_evidence_factory=_PlanEvidenceFactory(),
    )

    with pytest.raises(ValueError, match="explicit healer saved-build role"):
        support.compose(
            player_build=PlayerBuild(Role="Damage Dealer"),
            evidence_bundle=_bundle(_HEALING),  # type: ignore[arg-type]
        )


def test_generate_healer_composer_requires_canonical_healing_demand() -> None:
    role_factory = _RoleOutputFactory()
    support = RotationGenerateHealerRoleEvidenceSupport(
        role_output_factory=role_factory,
        plan_evidence_factory=_PlanEvidenceFactory(),
    )

    with pytest.raises(ValueError, match="at least one canonical healing demand"):
        support.compose(
            player_build=PlayerBuild(Role="Healer"),
            evidence_bundle=_bundle(_DAMAGE),  # type: ignore[arg-type]
        )

    assert role_factory.calls == []


def test_generate_healer_composer_blocks_unavailable_role_output_provider() -> None:
    role_factory = _RoleOutputFactory(
        SimpleNamespace(
            role_output_provider=None,
            unresolved=("back canonical static context is unavailable",),
        )
    )
    plan_factory = _PlanEvidenceFactory()
    support = RotationGenerateHealerRoleEvidenceSupport(
        role_output_factory=role_factory,
        plan_evidence_factory=plan_factory,
    )

    with pytest.raises(ValueError, match="back canonical static context"):
        support.compose(
            player_build=PlayerBuild(Role="Healer"),
            evidence_bundle=_bundle(_HEALING),  # type: ignore[arg-type]
        )

    assert plan_factory.calls == []


def test_generate_healer_composer_attaches_verified_criteria_as_separate_hard_gate() -> None:
    criterion = RotationHealerDemandCriterion(
        demand_name=_HEALING.name,
        minimum_modeled_healing_per_demand_second=1250.0,
        source_kind=(
            RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE
        ),
        provenance=("encounter_fact=reviewed_healer_floor",),
    )
    role_factory = _RoleOutputFactory()
    plan_factory = _PlanEvidenceFactory()
    support = RotationGenerateHealerRoleEvidenceSupport(
        role_output_factory=role_factory,
        plan_evidence_factory=plan_factory,
        criteria=(criterion,),
    )
    build = PlayerBuild(Role="Healer")

    evidence = support.compose(
        player_build=build,
        evidence_bundle=_bundle(_HEALING),  # type: ignore[arg-type]
    )

    assert evidence.plan_evidence_provider is plan_factory.result
    hard_gate = plan_factory.calls[0]["role_hard_obligation_evidence_provider"]
    assert isinstance(
        hard_gate,
        RotationCandidateHealerCriteriaHardObligationService,
    )
    assert hard_gate.multi_demand_output_service is role_factory.result
    assert hard_gate.criteria == (criterion,)


def test_production_healer_plan_evidence_rebinds_role_output_after_stabilization() -> None:
    role_output = _RuntimeRoleOutputResult()
    role_factory = _RoleOutputFactory(role_output)
    plan_factory = _CanonicalPlanFactory()
    runtime_context = _RuntimeBuildContextService()
    build = PlayerBuild(Name="Healer Tester", BuildName="Runtime Healer", Role="Healer")
    support = RotationGenerateHealerRoleEvidenceSupport(
        role_output_factory=role_factory,
        plan_evidence_factory=plan_factory,
        runtime_build_context_service=runtime_context,  # type: ignore[arg-type]
    )

    evidence = support.compose(
        player_build=build,
        evidence_bundle=_bundle(_HEALING),  # type: ignore[arg-type]
    )
    binder = getattr(evidence.plan_evidence_provider, "for_stabilized_snapshot", None)
    assert callable(binder)

    runtime_calls = []

    def runtime_state(time_seconds, sequence=None):
        runtime_calls.append((time_seconds, sequence))
        return object()

    candidate = _candidate()
    snapshot = RecoveryHeavyStabilizedCandidateSnapshot(
        candidate_id=candidate.candidate_id,
        plan=candidate.plan,
        replay=object(),
        stabilization=object(),
        runtime_combat_state_resolver=runtime_state,
    )
    rebound = binder(snapshot)
    result = rebound.evaluate_plan(candidate)

    assert result.role_output_value == pytest.approx(777.0)
    assert result.role_output_unresolved == ()
    assert len(plan_factory.result.calls) == 1
    assert runtime_calls == [(12.0, 2)]
    assert len(runtime_context.calls) == 1
    assert runtime_context.calls[0][0] is build
    assert len(role_output.calls) == 1
    assert role_output.calls[0][1] is not None
