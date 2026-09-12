from __future__ import annotations

from typing import Protocol

from minmax.resource_costs import ResourceType
from services.canonical_knowledge_gap import (
    CanonicalKnowledgeDomain,
    CanonicalKnowledgeGap,
)
from services.encounter_rotation_demand_service import EncounterRotationDemandPolicy
from services.rotation_encounter_demand_policy_registry_service import (
    RotationEncounterDemandPolicyRegistryService,
)
from services.rotation_static_build_context_service import RotationStaticBuildContextService
from ui.rotation_generate_canonical_context import (
    RotationGenerateCanonicalContext,
    RotationGenerateRoleEvidenceComposer,
)
from ui.rotation_selected_encounter_evidence_support import (
    RotationSelectedEncounterEvidenceInputs,
)


class RotationGenerateEncounterDemandPolicyProvider(Protocol):
    """Return explicit reviewed/configured demand policies for one encounter.

    ``None`` means policy evidence is unavailable. An empty tuple is distinct: it means
    the provider explicitly resolved that this Generate scope has no demand policies.
    """

    def policies_for(
        self,
        encounter_id: str,
    ) -> tuple[EncounterRotationDemandPolicy, ...] | None: ...


class RotationGenerateApplicationContextProvider:
    """Compose live canonical Generate context from authoritative page/application facts.

    The provider is intentionally role-neutral. It reads the exact selected saved build,
    exact persisted encounter identity, and explicit recovery policy controls at click
    time. Canonical static build context owns the resource maximum. Candidate evaluator
    and final scorecard resolvers are left unset so the dashboard composes them from the
    exact generated seed plan.

    Encounter demand policy is read from the reviewed persisted policy registry by
    default and is never inferred from boss names, guide prose, role, or class. Missing
    registry coverage becomes a blocking knowledge gap. Optional role evidence is
    accepted only as an injected composer that sits above this shared boundary.
    """

    def __init__(
        self,
        *,
        static_context_service: RotationStaticBuildContextService | None = None,
        demand_policy_provider: RotationGenerateEncounterDemandPolicyProvider | None = None,
        role_evidence_composer: RotationGenerateRoleEvidenceComposer | None = None,
    ) -> None:
        self.static_context_service = (
            static_context_service or RotationStaticBuildContextService()
        )
        self.demand_policy_provider = (
            demand_policy_provider or RotationEncounterDemandPolicyRegistryService()
        )
        self.role_evidence_composer = role_evidence_composer

    def context_for(self, page) -> RotationGenerateCanonicalContext:
        build = page._selected_build()
        if build is None:
            raise ValueError("select a saved build before canonical rotation generation")

        encounter_id = str(page.selected_encounter_id() or "").strip()
        if not encounter_id:
            raise ValueError("select an encounter before canonical rotation generation")

        policy = page.canonical_recovery_policy()
        resource = policy.get("resource")
        trigger_fraction = policy.get("trigger_fraction")
        if not isinstance(resource, ResourceType):
            raise ValueError(
                "select Magicka or Stamina recovery before canonical rotation generation"
            )
        if trigger_fraction is None:
            raise ValueError(
                "set an explicit recovery trigger before canonical rotation generation"
            )
        trigger = float(trigger_fraction)
        if not 0.0 <= trigger <= 1.0:
            raise ValueError("canonical recovery trigger must be between 0% and 100%")

        static_context = self.static_context_service.resolve(build)
        if not static_context.resolved:
            detail = "; ".join(static_context.unresolved) or "static build context unavailable"
            raise ValueError(
                "canonical static build evidence is unresolved: " + detail
            )
        maximum_amount = static_context.maximum_amount_for("front", resource)
        if maximum_amount <= 0:
            raise ValueError("canonical recovery resource maximum must be positive")

        demand_policies, knowledge_gaps = self._demand_policy(encounter_id)
        character_id = str(
            getattr(static_context.progression, "character_id", "") or ""
        ).strip() or None

        return RotationGenerateCanonicalContext(
            evidence_inputs=RotationSelectedEncounterEvidenceInputs(
                demand_policies=demand_policies,
                evaluator_resolver=None,
                scorecard_resolver=None,
                resource=resource,
                maximum_amount=maximum_amount,
                trigger_fraction=trigger,
                knowledge_gaps=knowledge_gaps,
            ),
            role_evidence_composer=self.role_evidence_composer,
            character_id=character_id,
        )

    def _demand_policy(
        self,
        encounter_id: str,
    ) -> tuple[
        tuple[EncounterRotationDemandPolicy, ...],
        tuple[CanonicalKnowledgeGap, ...],
    ]:
        policies = self.demand_policy_provider.policies_for(encounter_id)
        if policies is not None:
            return tuple(policies), ()

        return (), (
            CanonicalKnowledgeGap(
                domain=CanonicalKnowledgeDomain.ENCOUNTER_DEMAND,
                key=f"{encounter_id}.rotation_demand_policy",
                summary=(
                    "No explicit rotation demand policy is configured for the selected encounter."
                ),
                needed_evidence=(
                    "Persist or configure reviewed rotation demand policy for this encounter, "
                    "or explicitly record that this Generate scope has no demand policies."
                ),
                consumers=("rotation_maker",),
                source_context=f"selected encounter: {encounter_id}",
                blocking=True,
            ),
        )


__all__ = [
    "RotationGenerateApplicationContextProvider",
    "RotationGenerateEncounterDemandPolicyProvider",
]
