from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_candidate_runtime_state_frontier_resolver_service import (
    ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService,
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
                    effects=("effect-a",),
                ),
            ),
            denominator_proven=True,
            source=f"runtime family {candidate_id}",
        )
        return SimpleNamespace(
            frontier=frontier,
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
    assert result.effects == ("effect-a",)
    assert result.effect_denominator_proven is True


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



class _ScenarioWithDivergentEffects(_Scenario):
    def build_from_candidate(self, **kwargs):
        candidate_id = kwargs["candidate"].candidate_id
        frontier = ExtremeSustainedDPSRuntimeStateFrontierService.build(
            (
                ExtremeSustainedDPSRuntimeStateChoice(
                    f"runtime:{candidate_id}:a",
                    "snapshot:a",
                    effects=("effect-a",),
                ),
                ExtremeSustainedDPSRuntimeStateChoice(
                    f"runtime:{candidate_id}:b",
                    "snapshot:b",
                    effects=("effect-b",),
                ),
            ),
            denominator_proven=True,
            source="divergent runtime effects",
        )
        return SimpleNamespace(frontier=frontier, evidence=(), unresolved=())


def test_resolver_does_not_claim_shared_effect_denominator_when_choices_diverge() -> None:
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFrontierResolverService(
        scenario_frontier=_ScenarioWithDivergentEffects(),
        supplemental_history_denominator_proven=True,
    )

    result = resolver.resolve(_state())

    assert result.effects == ()
    assert result.effect_denominator_proven is False
