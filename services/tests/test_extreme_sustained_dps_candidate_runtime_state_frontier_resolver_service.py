from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_candidate_runtime_state_frontier_resolver_service import (
    ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService,
)
from services.extreme_sustained_dps_runtime_external_history_frontier_service import (
    ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult,
)
from services.extreme_sustained_dps_runtime_scenario_frontier_service import (
    ExtremeSustainedDPSRuntimeScenarioFrontierResult,
)
from services.extreme_sustained_dps_runtime_state_frontier_service import (
    ExtremeSustainedDPSRuntimeStateChoice,
    ExtremeSustainedDPSRuntimeStateFrontierService,
)


def _state(candidate_id="candidate"):
    candidate = SimpleNamespace(candidate_id=candidate_id, plan="plan")
    return SimpleNamespace(
        complete=True,
        finalized_potion=SimpleNamespace(candidate=candidate),
        runtime=SimpleNamespace(current_candidate=SimpleNamespace(candidate_id="runtime", plan="old-plan")),
        late=SimpleNamespace(
            assembled=SimpleNamespace(build="build"),
        ),
        target_identity="Boss",
    )


class _Scenario:
    def __init__(self):
        self.calls = []

    def build_from_candidate(self, **kwargs):
        self.calls.append(kwargs)
        candidate_id = kwargs["candidate"].candidate_id
        frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
            (
                ExtremeSustainedDPSRuntimeStateChoice(
                    f"runtime:{candidate_id}",
                    f"snapshot:{candidate_id}",
                ),
            ),
            denominator_proven=True,
            source=f"runtime family {candidate_id}",
        )
        return ExtremeSustainedDPSRuntimeScenarioFrontierResult(
            runtime=ExtremeSustainedDPSRuntimeExternalHistoryFrontierResult(
                frontier=frontier,
                evidence=(f"runtime {candidate_id}",),
                unresolved=(),
            ),
            evidence=(f"scenario {candidate_id}",),
            unresolved=(),
        )


def test_resolver_uses_finalized_candidate_and_assembled_build() -> None:
    scenario = _Scenario()
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
        scenario_frontier=scenario,
        supplemental_event_denominator_proven=True,
        supplemental_history_denominator_proven=True,
    )

    result = resolver.resolve(_state("final"))

    assert result.frontier.choices[0].snapshot == "snapshot:final"
    call = scenario.calls[-1]
    assert call["candidate"].candidate_id == "final"
    assert call["player_build"] == "build"
    assert call["target_identity"] == "Boss"
    assert call["effects"] is None


def test_resolver_recomputes_runtime_family_per_candidate() -> None:
    scenario = _Scenario()
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
        scenario_frontier=scenario,
        supplemental_event_denominator_proven=True,
        supplemental_history_denominator_proven=True,
    )

    first = resolver.resolve(_state("a"))
    second = resolver.resolve(_state("b"))

    assert first.frontier.choices[0].runtime_state_id == "runtime:a"
    assert second.frontier.choices[0].runtime_state_id == "runtime:b"
    assert [row["candidate"].candidate_id for row in scenario.calls] == ["a", "b"]


def test_resolver_threads_candidate_owned_supplemental_evidence() -> None:
    scenario = _Scenario()
    occurrence_provider = object()
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
        scenario_frontier=scenario,
        occurrence_provider_resolver=lambda state: occurrence_provider,
        supplemental_event_resolver=lambda state: ("event-a",),
        supplemental_event_denominator_proven=True,
        supplemental_history_resolver=lambda state: (),
        supplemental_history_denominator_proven=True,
        source="reviewed scenario",
    )

    resolver.resolve(_state())

    call = scenario.calls[-1]
    assert call["occurrence_provider"] is occurrence_provider
    assert call["supplemental_events"] == ("event-a",)
    assert call["supplemental_event_denominator_proven"] is True
    assert call["supplemental_denominator_proven"] is True
    assert call["source"] == "reviewed scenario"


def test_resolver_requires_complete_final_pipeline_state() -> None:
    scenario = _Scenario()
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
        scenario_frontier=scenario,
        supplemental_history_denominator_proven=True,
    )

    with pytest.raises(ValueError, match="complete finalized pipeline state"):
        resolver.resolve(SimpleNamespace(complete=False))




def test_resolver_can_supply_candidate_scoped_poison_consequence_authority() -> None:
    scenario = _Scenario()
    authority = object()
    seen = []

    def authority_for(state):
        seen.append(state)
        return authority

    resolver = ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
        scenario_frontier=scenario,
        supplemental_event_denominator_proven=True,
        supplemental_history_denominator_proven=True,
        weapon_poison_consequence_resolver_resolver=authority_for,
    )
    state = _state("poison-candidate")

    resolver.resolve(state)

    assert seen == [state]
    assert scenario.calls[-1]["weapon_poison_consequence_resolver"] is authority


@pytest.mark.parametrize(
    "field",
    (
        "supplemental_event_denominator_proven",
        "supplemental_history_denominator_proven",
    ),
)
def test_resolver_requires_strict_boolean_denominator_flags(field) -> None:
    kwargs = {
        "scenario_frontier": _Scenario(),
        "supplemental_event_denominator_proven": False,
        "supplemental_history_denominator_proven": False,
    }
    kwargs[field] = "false"

    with pytest.raises(TypeError, match="must be boolean"):
        ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(**kwargs)


def test_resolver_requires_callable_optional_hooks() -> None:
    with pytest.raises(TypeError, match="occurrence_provider_resolver must be callable"):
        ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
            scenario_frontier=_Scenario(),
            occurrence_provider_resolver=object(),
        )


def test_resolver_requires_scenario_build_from_candidate_contract() -> None:
    with pytest.raises(TypeError, match="build_from_candidate"):
        ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
            scenario_frontier=object(),
        )


def test_resolver_rejects_truthy_non_boolean_pipeline_complete_flag() -> None:
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
        scenario_frontier=_Scenario(),
    )
    state = _state()
    state.complete = "false"

    with pytest.raises(TypeError, match="complete flag must be boolean"):
        resolver.resolve(state)


def test_resolver_rejects_mutable_supplemental_event_collection() -> None:
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
        scenario_frontier=_Scenario(),
        supplemental_event_resolver=lambda _state: ["event"],
    )

    with pytest.raises(TypeError, match="supplemental events must be a tuple"):
        resolver.resolve(_state())
