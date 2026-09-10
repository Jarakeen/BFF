from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerDemandWindowOutput,
    RotationCandidateHealerMultiDemandOutput,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)
from tools.audit_phase13_xalvakka_healer_encounter_output import (
    _with_static_context_blockers,
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

    result = _with_static_context_blockers(
        output,
        ("Potion selected; activation/uptime is not part of static build state: spell power",),
    )

    assert result.windows[0].modeled_healing_per_demand_second == 1000.0
    assert result.weakest_window_value is None
    assert result.unresolved == (
        "static healer-output context: Potion selected; activation/uptime is not part of static build state: spell power",
    )
