from __future__ import annotations

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service import (
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService,
)


def _effect(name, *, trigger="damage_dealt", chance=None, condition=None):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source=name,
        trigger=trigger,
        chance=chance,
        condition=condition,
        duration=5.0,
    )


def _event():
    return RuntimeEvent(
        time_seconds=1.0,
        trigger="damage_dealt",
        source="Attack",
        target="Boss",
        sequence=0,
    )


def test_chance_rolls_reduce_to_threshold_equivalence_regions() -> None:
    result = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
        events=(_event(),),
        effects=(
            _effect("a", chance=0.25),
            _effect("b", chance=0.50),
            _effect("always", chance=1.0),
        ),
        event_denominator_proven=True,
        source="reviewed event family",
    )

    rolls = tuple(choice.attempts[0].chance_roll for choice in result.choices)
    assert rolls == (0.0, 0.25, 0.5)
    assert result.denominator_proven is True


def test_condition_contexts_enumerate_explicit_relevant_subsets() -> None:
    result = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
        events=(_event(),),
        effects=(
            _effect("a", condition="target_off_balance"),
            _effect("b", condition="target_chilled"),
        ),
        event_denominator_proven=True,
        source="reviewed event family",
    )

    contexts = {
        choice.attempts[0].condition_context
        for choice in result.choices
    }
    assert contexts == {
        frozenset(),
        frozenset({"target_off_balance"}),
        frozenset({"target_chilled"}),
        frozenset({"target_off_balance", "target_chilled"}),
    }
    assert all(context is not None for context in contexts)


def test_multiple_events_form_finite_cartesian_evidence_family() -> None:
    event_b = RuntimeEvent(
        time_seconds=2.0,
        trigger="critical_damage",
        source="Crit",
        target="Boss",
        sequence=0,
    )
    result = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
        events=(_event(), event_b),
        effects=(
            _effect("a", trigger="damage_dealt", chance=0.5),
            _effect("b", trigger="critical_damage", condition="target_chilled"),
        ),
        event_denominator_proven=True,
        source="reviewed event family",
    )

    # event A: two chance regions, one condition context.
    # event B: one chance region, two explicit condition contexts.
    assert result.candidate_count == 4
    assert result.denominator_proven is True


def test_unproven_event_skeleton_denominator_fails_closed() -> None:
    result = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
        events=(_event(),),
        effects=(_effect("a", chance=0.5),),
        event_denominator_proven=False,
        source="partial events",
    )

    assert result.denominator_proven is False
    assert any(
        "event skeleton denominator is not proven complete" in row
        for row in result.unresolved
    )



def test_zero_chance_effect_gets_concrete_failure_representative() -> None:
    result = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
        events=(_event(),),
        effects=(_effect("never", chance=0.0),),
        event_denominator_proven=True,
        source="reviewed event family",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 1
    assert result.choices[0].attempts[0].chance_roll == 0.0


def test_proven_empty_event_family_has_one_empty_evidence_choice() -> None:
    result = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
        events=(),
        effects=(),
        event_denominator_proven=True,
        source="reviewed no-event scenario",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 1
    assert result.choices[0].attempts == ()
    assert result.unresolved == ()



def test_zero_threshold_does_not_duplicate_mixed_chance_regions() -> None:
    result = ExtremeSustainedDPSRuntimeAttemptEvidenceFrontierService.build(
        events=(_event(),),
        effects=(
            _effect("never", chance=0.0),
            _effect("quarter", chance=0.25),
            _effect("half", chance=0.5),
        ),
        event_denominator_proven=True,
        source="reviewed event family",
    )

    rolls = tuple(choice.attempts[0].chance_roll for choice in result.choices)
    assert rolls == (0.0, 0.25, 0.5)
    assert result.candidate_count == 3
