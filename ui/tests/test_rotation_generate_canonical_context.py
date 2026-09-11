from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_generate_canonical_context import (
    RotationGenerateCanonicalContext,
    RotationGenerateRoleEvidenceInputs,
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


def test_generate_context_composes_role_evidence_from_authoritative_inputs() -> None:
    provider = object()
    context = RotationGenerateCanonicalContext(
        evidence_inputs=_inputs(),
        role_evidence_inputs=RotationGenerateRoleEvidenceInputs(
            plan_evidence_provider=provider,  # type: ignore[arg-type]
            role_output_label="effective damage",
            assigned_support_label="assigned support coverage",
        ),
    )

    evidence = context.role_evidence_for(
        player_build=SimpleNamespace(Role="Damage Dealer"),
        content_type="trial",
    )

    assert isinstance(evidence, RotationCanonicalRoleEvidence)
    assert evidence.plan_evidence_provider is provider
    assert evidence.role_key == "Damage Dealer"
    assert evidence.content_type == "trial"
    assert evidence.reliable_group_healing is None
    assert evidence.exception_contexts == ()


def test_generate_context_preserves_explicit_gameplay_policy_facts() -> None:
    context = RotationGenerateCanonicalContext(
        evidence_inputs=_inputs(),
        role_evidence_inputs=RotationGenerateRoleEvidenceInputs(
            plan_evidence_provider=object(),  # type: ignore[arg-type]
            role_output_label="effective damage",
            assigned_support_label="assigned support coverage",
            reliable_group_healing=False,
            exception_contexts=(
                "portal_or_split_group_assignment",
                "portal_or_split_group_assignment",
            ),
            role_key="dd",
        ),
    )

    evidence = context.role_evidence_for(
        player_build=SimpleNamespace(Role="Healer"),
        content_type="trial",
    )

    assert evidence is not None
    assert evidence.role_key == "dd"
    assert evidence.reliable_group_healing is False
    assert evidence.exception_contexts == ("portal_or_split_group_assignment",)


def test_generate_context_rejects_ambiguous_role_evidence_sources() -> None:
    explicit = RotationCanonicalRoleEvidence(
        plan_evidence_provider=object(),  # type: ignore[arg-type]
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
        content_type="trial",
    )
    inputs = RotationGenerateRoleEvidenceInputs(
        plan_evidence_provider=object(),  # type: ignore[arg-type]
        role_output_label="effective damage",
        assigned_support_label="assigned support coverage",
    )

    with pytest.raises(ValueError, match="either explicit role_evidence"):
        RotationGenerateCanonicalContext(
            evidence_inputs=_inputs(),
            role_evidence=explicit,
            role_evidence_inputs=inputs,
        )


def test_automatic_role_evidence_requires_explicit_saved_build_role() -> None:
    context = RotationGenerateCanonicalContext(
        evidence_inputs=_inputs(),
        role_evidence_inputs=RotationGenerateRoleEvidenceInputs(
            plan_evidence_provider=object(),  # type: ignore[arg-type]
            role_output_label="primary role output",
            assigned_support_label="assigned support coverage",
        ),
    )

    with pytest.raises(ValueError, match="explicit saved-build role"):
        context.role_evidence_for(
            player_build=SimpleNamespace(Role=""),
            content_type="trial",
        )
