from __future__ import annotations

import pytest

from minmax.resource_costs import ResourceType
from services.rotation_lokkestiiz_horn_candidate_obligation import (
    RotationLokkestiizHornCandidateObligation,
)
from services.rotation_lokkestiiz_landing_clock_service import (
    LokkestiizLandingClockEvidence,
)
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
)
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext
from ui.rotation_lokkestiiz_generate_context_support import (
    RotationLokkestiizGenerateContextSupport,
)
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
)


def _inputs() -> RotationSelectedEncounterEvidenceInputs:
    return RotationSelectedEncounterEvidenceInputs(
        demand_policies=(),
        evaluator_resolver=lambda candidate_id: object(),
        scorecard_resolver=lambda candidate_id: object(),
        resource=ResourceType.MAGICKA,
        maximum_amount=30000,
        trigger_fraction=0.25,
        restoration_resolver=lambda candidate_id: object(),
    )


def _clocks() -> LokkestiizLandingClockEvidence:
    return LokkestiizLandingClockEvidence(
        landing_times_seconds=(40.0, 90.0, 140.0),
        sources=("pull", "pull", "pull"),
    )


def test_composer_installs_horn_gate_and_preserves_existing_evaluation_evidence() -> None:
    evaluation = RotationSupportCadenceEvaluationContext(
        resource=ResourceType.STAMINA,
        runtime_uptime_requirements=(),
    )
    context = RotationGenerateCanonicalContext(
        evidence_inputs=_inputs(),
        cadence_evaluation_context=evaluation,
        cadence_max_iterations=5,
        character_id="magrat",
    )

    result = RotationLokkestiizGenerateContextSupport().apply_horn_gate(
        context,
        landing_clocks=_clocks(),
        starting_ultimate=500.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=True,
    )

    assert result is not context
    assert result.evidence_inputs is context.evidence_inputs
    assert result.cadence_max_iterations == 5
    assert result.character_id == "magrat"
    assert result.cadence_evaluation_context is not evaluation
    assert result.cadence_evaluation_context.resource is ResourceType.STAMINA

    resolver = result.cadence_evaluation_context.candidate_hard_obligation_resolver
    assert isinstance(resolver, RotationLokkestiizHornCandidateObligation)
    assert resolver.landing_clocks == _clocks()
    assert resolver.starting_ultimate == 500.0
    assert resolver.horn_cost == 250.0
    assert resolver.assume_scheduled_attacks_damage is True


def test_composer_creates_evaluation_context_when_generate_context_has_none() -> None:
    context = RotationGenerateCanonicalContext(evidence_inputs=_inputs())

    result = RotationLokkestiizGenerateContextSupport().apply_horn_gate(
        context,
        landing_clocks=_clocks(),
        starting_ultimate=0.0,
        horn_cost=250.0,
        assume_scheduled_attacks_damage=False,
    )

    assert result.cadence_evaluation_context is not None
    assert isinstance(
        result.cadence_evaluation_context.candidate_hard_obligation_resolver,
        RotationLokkestiizHornCandidateObligation,
    )


def test_composer_refuses_to_replace_existing_candidate_hard_obligation() -> None:
    existing = lambda plan: ("existing",)
    context = RotationGenerateCanonicalContext(
        evidence_inputs=_inputs(),
        cadence_evaluation_context=RotationSupportCadenceEvaluationContext(
            candidate_hard_obligation_resolver=existing,
        ),
    )

    with pytest.raises(
        ValueError,
        match="cannot replace an existing candidate hard-obligation resolver",
    ):
        RotationLokkestiizGenerateContextSupport().apply_horn_gate(
            context,
            landing_clocks=_clocks(),
            starting_ultimate=500.0,
            horn_cost=250.0,
            assume_scheduled_attacks_damage=True,
        )
