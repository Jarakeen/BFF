from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_runtime_attempt_evidence_frontier_service import (
    ExtremeSustainedDPSRuntimeAttemptEvidenceChoice,
    ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier,
)
from services.extreme_sustained_dps_runtime_attempt_frontier_composition_service import (
    ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService,
)


def _attempt(time_seconds, source):
    return RuntimeEffectEventAttempt(
        event=RuntimeEvent(
            time_seconds=time_seconds,
            trigger="damage_dealt",
            source=source,
        )
    )


def _frontier(prefix, attempts, *, proven=True, unresolved=()):
    choices = tuple(
        ExtremeSustainedDPSRuntimeAttemptEvidenceChoice(
            choice_id=f"{prefix}:{index}",
            attempts=(attempt,),
            evidence=(f"{prefix} evidence",),
        )
        for index, attempt in enumerate(attempts)
    )
    return ExtremeSustainedDPSRuntimeAttemptEvidenceFrontier(
        choices=choices,
        candidate_count=len(choices),
        denominator_proven=proven,
        evidence=(),
        unresolved=unresolved,
    )


def test_composition_crosses_independent_attempt_choice_families():
    left = _frontier(
        "left",
        (_attempt(1.0, "a"), _attempt(1.0, "b")),
    )
    right = _frontier(
        "right",
        (_attempt(2.0, "c"), _attempt(2.0, "d"), _attempt(2.0, "e")),
    )

    result = ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService.compose(
        (left, right),
        source="reviewed fixture",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 6
    assert all(len(choice.attempts) == 2 for choice in result.choices)


def test_unproven_input_frontier_keeps_composition_open():
    left = _frontier(
        "left",
        (_attempt(1.0, "a"),),
        proven=False,
        unresolved=("left incomplete",),
    )
    right = _frontier(
        "right",
        (_attempt(2.0, "b"),),
    )

    result = ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService.compose(
        (left, right),
        source="partial fixture",
    )

    assert result.denominator_proven is False
    assert any("left incomplete" in row for row in result.unresolved)


def test_no_frontiers_produces_one_empty_identity_choice():
    result = ExtremeSustainedDPSRuntimeAttemptFrontierCompositionService.compose(
        (),
        source="empty fixture",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 1
    assert result.choices[0].attempts == ()
