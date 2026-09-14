from types import SimpleNamespace

from services.rotation_recovery_final_role_evidence_service import (
    RotationRecoveryFinalRoleEvidenceConfiguration,
    RotationRecoveryFinalRoleEvidenceService,
)


class _Provider:
    def __init__(self):
        self.candidate_projector = object()

    def evaluate_plan(self, _candidate):
        return SimpleNamespace(
            role_output_value=1.0,
            assigned_support_value=0.0,
            primary_role_displacement_seconds=0.0,
            role_hard_obligation_satisfied=True,
            role_hard_obligation_reasons=(),
        )


def test_final_role_resolver_carries_candidate_projector_metadata():
    provider = _Provider()
    service = RotationRecoveryFinalRoleEvidenceService(
        plan_evidence_provider=provider,
        scorecard_resolver=lambda _snapshot: object(),
        configuration=RotationRecoveryFinalRoleEvidenceConfiguration(
            role_key="tank",
            role_output_label="tank role output unresolved",
            assigned_support_label="assigned support coverage",
        ),
    )

    resolver = service.resolver()

    assert resolver.candidate_projector is provider.candidate_projector
