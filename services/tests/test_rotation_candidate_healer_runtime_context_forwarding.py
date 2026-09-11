from types import SimpleNamespace

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_role_output_service import (
    RotationCandidateHealerRoleOutputService,
)


_DEMAND = RotationDemandWindow(
    name="runtime healing",
    start_seconds=10.0,
    end_seconds=15.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
    target_count=12,
)


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="runtime-healer",
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Runtime Healer",
            duration_seconds=30.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _LegacyDemandProvider:
    def evaluate_demand(self, *, candidate, demand):
        return SimpleNamespace(
            demand=demand,
            unresolved=(),
            modeled_total_healing=1000.0,
        )


class _RuntimeDemandProvider:
    def __init__(self) -> None:
        self.calls = []

    def evaluate_demand(
        self,
        *,
        candidate,
        demand,
        runtime_build_context_resolver=None,
    ):
        self.calls.append((candidate, demand, runtime_build_context_resolver))
        return SimpleNamespace(
            demand=demand,
            unresolved=(),
            modeled_total_healing=1500.0,
        )


def test_static_role_output_does_not_force_runtime_keyword_on_legacy_provider() -> None:
    service = RotationCandidateHealerRoleOutputService(
        demand=_DEMAND,
        demand_evidence_provider=_LegacyDemandProvider(),
    )

    result = service.evaluate_plan(_candidate())

    assert result.resolved_value == 200.0


def test_runtime_role_output_forwards_exact_context_resolver_to_demand_provider() -> None:
    provider = _RuntimeDemandProvider()
    service = RotationCandidateHealerRoleOutputService(
        demand=_DEMAND,
        demand_evidence_provider=provider,
    )
    resolver = lambda time_seconds, sequence=None: (time_seconds, sequence)

    result = service.evaluate_plan(
        _candidate(),
        runtime_build_context_resolver=resolver,
    )

    assert result.resolved_value == 300.0
    assert len(provider.calls) == 1
    candidate, demand, forwarded = provider.calls[0]
    assert candidate.candidate_id == "runtime-healer"
    assert demand is _DEMAND
    assert forwarded is resolver
