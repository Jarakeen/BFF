from __future__ import annotations

from types import SimpleNamespace

import pytest

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_generated_finalized_potion_axis_adapter_service import (
    ExtremeSustainedDPSFinalizedPotionTimingEvidence,
    ExtremeSustainedDPSGeneratedFinalizedPotionAxisAdapterService,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


class _DenominatorService:
    def __init__(self):
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            denominator_proven=True,
            unresolved=(),
            observation_frontier=SimpleNamespace(
                observation_times=(1.0, 4.0),
            ),
            breakpoint_frontier=SimpleNamespace(
                full_potion_timing_closed=True,
                choices=(
                    SimpleNamespace(
                        first_use_seconds=1.0,
                        kind="boundary",
                    ),
                    SimpleNamespace(
                        first_use_seconds=2.0,
                        kind="open_interval_representative",
                    ),
                ),
            ),
        )


class _Legality:
    def __init__(self):
        self.calls = []

    def assess(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            is_legal=True,
            unresolved=(),
        )


def _candidate() -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id="runtime-candidate",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=10.0,
            actions=(
                RotationAction(
                    0.0,
                    0,
                    RotationActionKind.POTION,
                    "Potion X",
                ),
                RotationAction(
                    1.0,
                    0,
                    RotationActionKind.SKILL,
                    "Skill A",
                    "front",
                ),
                RotationAction(
                    4.0,
                    0,
                    RotationActionKind.LIGHT_ATTACK,
                    "Light Attack",
                    "front",
                ),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _upstream(candidate=None):
    return SimpleNamespace(
        complete=True,
        current_candidate=candidate or _candidate(),
    )


def _resolver(candidate):
    assert candidate.candidate_id == "runtime-candidate"
    return ExtremeSustainedDPSFinalizedPotionTimingEvidence(
        additional_resource_event_denominator_proven=True,
    )


def _adapter():
    denominator = _DenominatorService()
    legality = _Legality()
    return (
        ExtremeSustainedDPSGeneratedFinalizedPotionAxisAdapterService(
            denominator_service=denominator,
            legality_service=legality,
        ),
        denominator,
        legality,
    )


def test_axis_owns_finalized_potion_timing_canonical_dimension() -> None:
    adapter, _denominator, _legality = _adapter()
    axis = adapter.axis()

    assert axis.name == "Finalized Potion Timing Policy"
    assert axis.canonical_axes == ("potion_timing_policy",)
    assert axis.omitted_scope == ()


def test_selected_potion_enumerates_no_use_boundaries_and_open_intervals() -> None:
    adapter, denominator, _legality = _adapter()
    state = adapter.root(
        _upstream(),
        build=PlayerBuild(Potion="Potion X"),
        progression="progression",
        potion_cooldown_seconds=45.0,
        evidence_resolver=_resolver,
    )

    axis = adapter.axis()
    assert axis.candidate_count(state) == 4
    call = denominator.calls[-1]
    assert call["instant_restoration_timing_closed"] is False
    assert call["resource_observation_denominator_proven"] is True
    assert call["resource_observation_times"]
    assert call["observation_frontier"].observation_times == (1.0, 4.0)


def test_exact_observation_boundary_preserves_before_and_after_ordering() -> None:
    adapter, _denominator, _legality = _adapter()
    root = adapter.root(
        _upstream(),
        build=PlayerBuild(Potion="Potion X"),
        progression="progression",
        potion_cooldown_seconds=45.0,
        evidence_resolver=_resolver,
    )
    axis = adapter.axis()

    before = axis.candidate_at(root, 1)
    after = axis.candidate_at(root, 2)

    before_at_one = tuple(
        action
        for action in before.candidate.plan.actions
        if action.time_seconds == 1.0
    )
    after_at_one = tuple(
        action
        for action in after.candidate.plan.actions
        if action.time_seconds == 1.0
    )

    assert tuple((row.kind, row.sequence) for row in before_at_one) == (
        (RotationActionKind.POTION, 0),
        (RotationActionKind.SKILL, 1),
    )
    assert tuple((row.kind, row.sequence) for row in after_at_one) == (
        (RotationActionKind.SKILL, 0),
        (RotationActionKind.POTION, 1),
    )
    assert sum(
        action.kind is RotationActionKind.POTION
        for action in before.candidate.plan.actions
    ) == 1
    assert before.selected_policy.policy_id.startswith("potion:1:before")
    assert after.selected_policy.policy_id.startswith("potion:1:after")


def test_open_interval_representative_materializes_one_deterministic_cadence() -> None:
    adapter, _denominator, _legality = _adapter()
    root = adapter.root(
        _upstream(),
        build=PlayerBuild(Potion="Potion X"),
        progression="progression",
        potion_cooldown_seconds=45.0,
        evidence_resolver=_resolver,
    )

    state = adapter.axis().candidate_at(root, 3)

    potion_actions = tuple(
        action
        for action in state.candidate.plan.actions
        if action.kind is RotationActionKind.POTION
    )
    assert tuple(row.time_seconds for row in potion_actions) == (2.0,)
    assert state.selected_policy.same_timestamp_order == "after"
    assert state.complete is True


def test_no_potion_selection_has_one_trivially_closed_no_use_policy() -> None:
    adapter, denominator, _legality = _adapter()
    root = adapter.root(
        _upstream(),
        build=PlayerBuild(Potion=""),
        progression="progression",
        potion_cooldown_seconds=45.0,
        evidence_resolver=_resolver,
    )

    axis = adapter.axis()
    assert axis.candidate_count(root) == 1
    state = axis.candidate_at(root, 0)

    assert state.selected_policy.policy_id == "potion:none"
    assert all(
        action.kind is not RotationActionKind.POTION
        for action in state.candidate.plan.actions
    )
    assert state.denominator is None
    assert denominator.calls == []
    assert state.complete is True



def test_missing_resource_event_denominator_proof_fails_closed() -> None:
    adapter, _denominator, _legality = _adapter()

    def unresolved_resource_evidence(candidate):
        assert candidate.candidate_id == "runtime-candidate"
        return ExtremeSustainedDPSFinalizedPotionTimingEvidence()

    root = adapter.root(
        _upstream(),
        build=PlayerBuild(Potion="Potion X"),
        progression="progression",
        potion_cooldown_seconds=45.0,
        evidence_resolver=unresolved_resource_evidence,
    )

    import pytest

    with pytest.raises(ValueError, match="resource observation denominator"):
        adapter.axis().candidate_count(root)


def test_finalized_potion_evidence_rejects_truthy_non_boolean_denominator_flag() -> None:
    with pytest.raises(TypeError, match="proof flag must be boolean"):
        ExtremeSustainedDPSFinalizedPotionTimingEvidence(
            additional_resource_event_denominator_proven="false",
        )


def test_finalized_potion_root_rejects_truthy_non_boolean_complete_flag() -> None:
    adapter, _denominator, _legality = _adapter()
    upstream = SimpleNamespace(
        runtime=SimpleNamespace(complete="false", current_candidate=_candidate()),
        complete=False,
    )

    with pytest.raises(TypeError, match="complete flag must be boolean"):
        adapter.root(
            upstream,
            build=PlayerBuild(Potion="Potion X"),
            progression="progression",
            potion_cooldown_seconds=45.0,
            evidence_resolver=_resolver,
        )


def test_finalized_potion_root_rejects_boolean_cooldown() -> None:
    adapter, _denominator, _legality = _adapter()

    with pytest.raises(TypeError, match="cooldown must be numeric"):
        adapter.root(
            _upstream(),
            build=PlayerBuild(Potion="Potion X"),
            progression="progression",
            potion_cooldown_seconds=True,
            evidence_resolver=_resolver,
        )


def test_finalized_potion_denominator_requires_canonical_timing_evidence() -> None:
    adapter, _denominator, _legality = _adapter()
    root = adapter.root(
        _upstream(),
        build=PlayerBuild(Potion="Potion X"),
        progression="progression",
        potion_cooldown_seconds=45.0,
        evidence_resolver=lambda _candidate: SimpleNamespace(
            periodic_projections=(),
            heavy_attack_completion_evidence=(),
            additional_resource_event_times=(),
            additional_resource_event_denominator_proven=True,
            unresolved=(),
        ),
    )

    with pytest.raises(TypeError, match="canonical timing evidence"):
        adapter.axis().candidate_count(root)



def test_finalized_potion_policy_index_rejects_boolean() -> None:
    adapter, _denominator, _legality = _adapter()
    root = adapter.root(
        _upstream(),
        build=PlayerBuild(Potion=""),
        progression="progression",
        potion_cooldown_seconds=45.0,
        evidence_resolver=_resolver,
    )

    with pytest.raises(TypeError, match="policy index must be an integer"):
        adapter.axis().candidate_at(root, True)



@pytest.mark.parametrize("value", (True, "1.0"))
def test_finalized_potion_evidence_rejects_non_numeric_resource_event_times(value) -> None:
    with pytest.raises(TypeError, match="event times must be numeric"):
        ExtremeSustainedDPSFinalizedPotionTimingEvidence(
            additional_resource_event_times=(value,),
            additional_resource_event_denominator_proven=True,
        )


@pytest.mark.parametrize("value", (-1.0, float("inf"), float("nan")))
def test_finalized_potion_evidence_rejects_invalid_resource_event_times(value) -> None:
    with pytest.raises(ValueError, match="finite and non-negative"):
        ExtremeSustainedDPSFinalizedPotionTimingEvidence(
            additional_resource_event_times=(value,),
            additional_resource_event_denominator_proven=True,
        )
