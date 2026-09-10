from types import SimpleNamespace

import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerMultiDemandRoleOutputService,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)


def _demand(name: str, start: float, end: float) -> RotationDemandWindow:
    return RotationDemandWindow(
        name=name,
        start_seconds=start,
        end_seconds=end,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.SUSTAINED,
    )


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="healer-candidate",
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Multi Demand Healer",
            duration_seconds=60.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _DemandEvidenceProvider:
    def __init__(self, totals, unresolved_by_name=None):
        self.totals = dict(totals)
        self.unresolved_by_name = dict(unresolved_by_name or {})
        self.calls = []

    def evaluate_demand(self, *, candidate, demand):
        self.calls.append((candidate.candidate_id, demand.name))
        return RotationHealerDemandHealingEvidence(
            demand=demand,
            direct_events=(),
            periodic_events=(),
            delayed_events=(),
            modeled_direct_healing=float(self.totals[demand.name]),
            modeled_periodic_healing=0.0,
            modeled_delayed_healing=0.0,
            unresolved=tuple(self.unresolved_by_name.get(demand.name, ())),
        )


def test_multi_demand_output_preserves_each_window_and_uses_weakest_rate() -> None:
    first = _demand("first danger", 10.0, 15.0)
    second = _demand("second danger", 30.0, 40.0)
    provider = _DemandEvidenceProvider(
        {
            "first danger": 5000.0,   # 1000 per demand-second
            "second danger": 2500.0,  # 250 per demand-second
        }
    )
    service = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=(first, second),
        demand_evidence_provider=provider,
    )

    detailed = service.evaluate_windows(_candidate())
    role_output = service.evaluate_plan(_candidate())

    assert [item.demand.name for item in detailed.windows] == [
        "first danger",
        "second danger",
    ]
    assert [item.modeled_healing_per_demand_second for item in detailed.windows] == [
        pytest.approx(1000.0),
        pytest.approx(250.0),
    ]
    assert detailed.weakest_window_value == pytest.approx(250.0)
    assert role_output.resolved_value == pytest.approx(250.0)
    assert role_output.unresolved == ()


def test_excess_healing_in_one_window_cannot_hide_weak_output_in_another() -> None:
    first = _demand("easy burn", 0.0, 5.0)
    second = _demand("hard burn", 20.0, 25.0)
    service = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=(first, second),
        demand_evidence_provider=_DemandEvidenceProvider(
            {
                "easy burn": 500000.0,
                "hard burn": 500.0,
            }
        ),
    )

    result = service.evaluate_plan(_candidate())

    # A giant first-window result does not average the weak second window upward.
    assert result.resolved_value == pytest.approx(100.0)


def test_unresolved_required_window_keeps_aggregate_role_output_unknown() -> None:
    first = _demand("resolved window", 0.0, 5.0)
    second = _demand("unknown window", 20.0, 25.0)
    service = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=(first, second),
        demand_evidence_provider=_DemandEvidenceProvider(
            {
                "resolved window": 5000.0,
                "unknown window": 5000.0,
            },
            unresolved_by_name={
                "unknown window": ("periodic refresh behavior unresolved",),
            },
        ),
    )

    detailed = service.evaluate_windows(_candidate())
    result = service.evaluate_plan(_candidate())

    assert detailed.windows[0].modeled_healing_per_demand_second == pytest.approx(1000.0)
    assert detailed.windows[1].modeled_healing_per_demand_second is None
    assert detailed.weakest_window_value is None
    assert result.value is None
    assert result.resolved_value is None
    assert result.unresolved == (
        "unknown window: periodic refresh behavior unresolved",
    )


def test_each_required_window_is_evaluated_independently() -> None:
    first = _demand("window one", 5.0, 10.0)
    second = _demand("window two", 10.0, 15.0)
    provider = _DemandEvidenceProvider(
        {"window one": 1000.0, "window two": 1000.0}
    )
    service = RotationCandidateHealerMultiDemandRoleOutputService(
        demands=(first, second),
        demand_evidence_provider=provider,
    )

    service.evaluate_plan(_candidate())

    assert provider.calls == [
        ("healer-candidate", "window one"),
        ("healer-candidate", "window two"),
    ]


def test_multi_demand_service_rejects_empty_nonhealing_and_duplicate_scope() -> None:
    provider = _DemandEvidenceProvider({})

    with pytest.raises(ValueError, match="at least one demand"):
        RotationCandidateHealerMultiDemandRoleOutputService(
            demands=(),
            demand_evidence_provider=provider,
        )

    support = RotationDemandWindow(
        name="support window",
        start_seconds=0.0,
        end_seconds=5.0,
        kind=RotationDemandKind.SUPPORT,
        pattern=RotationDemandPattern.SUSTAINED,
    )
    with pytest.raises(ValueError, match="only healing demands"):
        RotationCandidateHealerMultiDemandRoleOutputService(
            demands=(support,),
            demand_evidence_provider=provider,
        )

    first = _demand("same", 0.0, 5.0)
    second = _demand("SAME", 10.0, 15.0)
    with pytest.raises(ValueError, match="duplicate healer demand name"):
        RotationCandidateHealerMultiDemandRoleOutputService(
            demands=(first, second),
            demand_evidence_provider=provider,
        )
