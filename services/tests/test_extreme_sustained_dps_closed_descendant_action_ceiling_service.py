from __future__ import annotations

from services.extreme_sustained_dps_closed_descendant_action_ceiling_service import (
    ExtremeSustainedDPSClosedActionConsequence,
    ExtremeSustainedDPSClosedDescendantActionCeilingService,
    ExtremeSustainedDPSClosedDescendantActionWitness,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)


def _action(time, sequence, *damages, complete=True, unresolved=()):
    return ExtremeSustainedDPSClosedActionConsequence(
        occurrence_evidence=RotationActionDamageOccurrenceEvidence(
            action_time_seconds=time,
            action_sequence=sequence,
            occurrences=tuple(
                RotationActionDamageOccurrence(
                    time_seconds=time + index * 0.5,
                    sequence=index,
                    damage_value=value,
                    source_name=f"source-{index}",
                )
                for index, value in enumerate(damages)
            ),
            unresolved=tuple(unresolved),
        ),
        covers_periodic_and_triggered=complete,
    )


def _witness(key, *actions):
    return ExtremeSustainedDPSClosedDescendantActionWitness(
        candidate_key=key,
        expected_damage_action_count=len(actions),
        consequences=tuple(actions),
    )


def test_closed_complete_descendants_prove_maximum_total_action_damage() -> None:
    result = ExtremeSustainedDPSClosedDescendantActionCeilingService.evaluate(
        "branch:a",
        expected_descendant_keys=("a1", "a2"),
        denominator_proven=True,
        witnesses=(
            _witness(
                "a1",
                _action(0.0, 0, 100.0),
                _action(1.0, 0, 60.0, 70.0),
            ),
            _witness(
                "a2",
                _action(0.0, 0, 120.0),
                _action(1.0, 0, 90.0),
            ),
        ),
    )

    assert result.ceiling.complete is True
    assert result.maximum_action_damage == 130.0
    assert result.observed_action_count == 4


def test_missing_descendant_blocks_ceiling() -> None:
    result = ExtremeSustainedDPSClosedDescendantActionCeilingService.evaluate(
        "branch:b",
        expected_descendant_keys=("b1", "b2"),
        denominator_proven=True,
        witnesses=(_witness("b1", _action(0.0, 0, 100.0)),),
    )

    assert result.ceiling.complete is False
    assert result.maximum_action_damage is None
    assert any("missing candidate" in row for row in result.unresolved)


def test_incomplete_periodic_triggered_coverage_blocks_ceiling() -> None:
    result = ExtremeSustainedDPSClosedDescendantActionCeilingService.evaluate(
        "branch:c",
        expected_descendant_keys=("c1",),
        denominator_proven=True,
        witnesses=(
            _witness(
                "c1",
                _action(0.0, 0, 100.0, complete=False),
            ),
        ),
    )

    assert result.ceiling.complete is False
    assert any("periodic/triggered" in row for row in result.unresolved)


def test_unresolved_action_evidence_blocks_ceiling() -> None:
    result = ExtremeSustainedDPSClosedDescendantActionCeilingService.evaluate(
        "branch:d",
        expected_descendant_keys=("d1",),
        denominator_proven=True,
        witnesses=(
            _witness(
                "d1",
                _action(0.0, 0, unresolved=("proc timing unavailable",)),
            ),
        ),
    )

    assert result.ceiling.complete is False
    assert any("proc timing unavailable" in row for row in result.unresolved)


def test_unproven_denominator_blocks_ceiling_even_with_complete_witnesses() -> None:
    result = ExtremeSustainedDPSClosedDescendantActionCeilingService.evaluate(
        "branch:e",
        expected_descendant_keys=("e1",),
        denominator_proven=False,
        witnesses=(_witness("e1", _action(0.0, 0, 100.0)),),
    )

    assert result.ceiling.complete is False
    assert any("not proven complete" in row for row in result.unresolved)


def test_action_count_mismatch_blocks_ceiling() -> None:
    witness = ExtremeSustainedDPSClosedDescendantActionWitness(
        candidate_key="f1",
        expected_damage_action_count=2,
        consequences=(_action(0.0, 0, 100.0),),
    )
    result = ExtremeSustainedDPSClosedDescendantActionCeilingService.evaluate(
        "branch:f",
        expected_descendant_keys=("f1",),
        denominator_proven=True,
        witnesses=(witness,),
    )

    assert result.ceiling.complete is False
    assert any("expected 2 damage-bearing" in row for row in result.unresolved)
