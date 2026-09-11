from types import SimpleNamespace

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerDemandWindowOutput,
    RotationCandidateHealerMultiDemandOutput,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)
from services.rotation_healer_canonical_role_output_factory_service import (
    RotationHealerCanonicalRoleOutputFactoryResult,
)


def test_static_context_blocker_preserves_window_value_but_poison_aggregate_output():
    demand = RotationDemandWindow(
        name="Xalvakka Phase 2 healing prep",
        start_seconds=10.0,
        end_seconds=12.0,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )
    evidence = RotationHealerDemandHealingEvidence(
        demand=demand,
        direct_events=(),
        periodic_events=(),
        delayed_events=(),
        modeled_direct_healing=2000.0,
        modeled_periodic_healing=0.0,
        modeled_delayed_healing=0.0,
        unresolved=(),
    )
    output = RotationCandidateHealerMultiDemandOutput(
        candidate_id="candidate",
        windows=(
            RotationCandidateHealerDemandWindowOutput(
                evidence=evidence,
                modeled_healing_per_demand_second=1000.0,
            ),
        ),
    )

    role_output = SimpleNamespace(evaluate_windows=lambda _candidate: output)
    factory_result = RotationHealerCanonicalRoleOutputFactoryResult(
        static_context=SimpleNamespace(),  # type: ignore[arg-type]
        context_relevance=SimpleNamespace(),  # type: ignore[arg-type]
        demand_evidence_provider=SimpleNamespace(),  # type: ignore[arg-type]
        role_output_provider=role_output,  # type: ignore[arg-type]
        unresolved=(
            "Potion selected; activation/uptime is not part of static build state: spell power",
        ),
    )
    candidate = GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Magrat",
            build_name="DF Healer",
            duration_seconds=60.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )

    result = factory_result.evaluate_windows(candidate)

    assert result.windows[0].modeled_healing_per_demand_second == 1000.0
    assert result.weakest_window_value is None
    assert result.unresolved == (
        "static healer-output context: Potion selected; activation/uptime is not part of static build state: spell power",
    )
