from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_ability_priority import AbilityPriorityList
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidatePlanEvidenceProvider,
)
from services.rotation_support_cadence_evaluation_service import (
    RotationSupportCadenceEvaluationContext,
)
from services.rotation_support_cadence_neighborhood_service import (
    RotationSupportCadenceNeighborhoodObligation,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalRoleEvidence
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
)


@dataclass(frozen=True)
class RotationGenerateRoleEvidenceInputs:
    """Authoritative plan evidence plus explicit gameplay-policy context.

    The saved build may supply its persisted role identity and the selected encounter
    may supply its persisted content type. Group-healing reliability and assignment
    exceptions remain explicit because neither fact follows from role or encounter
    identity alone.
    """

    plan_evidence_provider: RotationCandidatePlanEvidenceProvider
    role_output_label: str
    assigned_support_label: str
    reliable_group_healing: bool | None = None
    exception_contexts: tuple[str, ...] = ()
    role_key: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("role_output_label", "assigned_support_label"):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"{field_name} must be non-empty")
            object.__setattr__(self, field_name, value)
        object.__setattr__(
            self,
            "exception_contexts",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.exception_contexts
                    if str(item).strip()
                )
            ),
        )
        if self.role_key is not None:
            object.__setattr__(self, "role_key", str(self.role_key).strip() or None)

    def compose(
        self,
        *,
        player_build,
        content_type: object = "",
    ) -> RotationCanonicalRoleEvidence:
        role_key = str(
            self.role_key
            or getattr(player_build, "Role", "")
            or ""
        ).strip()
        if not role_key:
            raise ValueError(
                "automatic canonical role evidence requires an explicit saved-build role"
            )
        return RotationCanonicalRoleEvidence(
            plan_evidence_provider=self.plan_evidence_provider,
            role_output_label=self.role_output_label,
            assigned_support_label=self.assigned_support_label,
            content_type=str(content_type or "").strip(),
            reliable_group_healing=self.reliable_group_healing,
            exception_contexts=self.exception_contexts,
            role_key=role_key,
        )


@dataclass(frozen=True)
class RotationGenerateCanonicalContext:
    """Explicit encounter-aware inputs used by the dashboard Generate action.

    Presence of this object opts Generate Rotation into canonical encounter-aware
    orchestration. Absence preserves the legacy/plain generation path. The context
    contains explicit evidence/runtime inputs only; it does not infer them from role,
    class, encounter display names, or UI labels. Optional ``role_evidence`` carries
    already-resolved application facts into the canonical role-aware ranking path.
    """

    evidence_inputs: RotationSelectedEncounterEvidenceInputs
    role_evidence: RotationCanonicalRoleEvidence | None = None
    role_evidence_inputs: RotationGenerateRoleEvidenceInputs | None = None
    cadence_obligations: tuple[RotationSupportCadenceNeighborhoodObligation, ...] = ()
    cadence_priorities: AbilityPriorityList | None = None
    cadence_evaluation_context: RotationSupportCadenceEvaluationContext | None = None
    cadence_max_iterations: int = 8
    character_id: str | None = None

    def __post_init__(self) -> None:
        if self.role_evidence is not None and self.role_evidence_inputs is not None:
            raise ValueError(
                "supply either explicit role_evidence or role_evidence_inputs, not both"
            )
        iterations = int(self.cadence_max_iterations)
        if iterations <= 0:
            raise ValueError("cadence_max_iterations must be positive")
        object.__setattr__(self, "cadence_max_iterations", iterations)
        object.__setattr__(self, "cadence_obligations", tuple(self.cadence_obligations))

    def role_evidence_for(
        self,
        *,
        player_build,
        content_type: object = "",
    ) -> RotationCanonicalRoleEvidence | None:
        if self.role_evidence is not None:
            return self.role_evidence.with_content_type_if_missing(content_type)
        if self.role_evidence_inputs is None:
            return None
        return self.role_evidence_inputs.compose(
            player_build=player_build,
            content_type=content_type,
        )


__all__ = [
    "RotationGenerateCanonicalContext",
    "RotationGenerateRoleEvidenceInputs",
]
