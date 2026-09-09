from __future__ import annotations

from dataclasses import replace

import pytest

from minmax.resource_costs import ResourceType
from ui.rotation_generate_canonical_context import RotationGenerateCanonicalContext
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


def test_generate_context_preserves_explicit_inputs_without_inference() -> None:
    inputs = _inputs()
    context = RotationGenerateCanonicalContext(
        evidence_inputs=inputs,
        cadence_max_iterations=5,
        character_id="magrat",
    )

    assert context.evidence_inputs is inputs
    assert context.cadence_obligations == ()
    assert context.cadence_max_iterations == 5
    assert context.character_id == "magrat"


def test_generate_context_rejects_non_positive_cadence_iteration_limit() -> None:
    with pytest.raises(ValueError, match="cadence_max_iterations must be positive"):
        RotationGenerateCanonicalContext(
            evidence_inputs=_inputs(),
            cadence_max_iterations=0,
        )
