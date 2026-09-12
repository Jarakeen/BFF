from __future__ import annotations

from typing import Mapping, Protocol

from minmax.fight_damage_trajectory import RaidDamageSegment
from minmax.resource_costs import ResourceType
from services.canonical_knowledge_gap import (
    CanonicalKnowledgeDomain,
    CanonicalKnowledgeGap,
)
from services.encounter_rotation_demand_service import EncounterRotationDemandPolicy
from services.encounter_threshold_rotation_demand_service import (
    EncounterThresholdRotationDemandPolicy,
)
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
    """Return explicit reviewed/configured demand policies for one encounter."""

    def policies_for(
        self,
        encounter_id: str,
    ) -> tuple[EncounterRotationDemandPolicy, ...] | None: ...

    def threshold_policies_for(
        self,
        encounter_id: str,
    ) -> tuple[EncounterThresholdRotationDemandPolicy, ...] | None: ...


def _canonical_role(value: object) -> str:
    return "_".join(str(value or "").strip().casefold().replace("-", " ").split())


class RotationGenerateApplicationContextProvider:
    """Compose live canonical Generate context from authoritative page/application facts.

    Clock-timed and health-threshold encounter policies are read from the reviewed
    persisted registry. Threshold policies additionally require explicit difficulty and
    raid DPS from the live page; constant raid DPS is represented as an explicit damage
    trajectory rather than inferred from build potency, parse targets, or encounter name.

    Persisted review blockers are converted into canonical blocking knowledge gaps. This
    lets partly researched encounters fail closed with the exact missing policy decision
    instead of collapsing back to a generic "no policy configured" state.

    Role evidence can be supplied either as one explicit composer override or through a
    role-keyed composer map. The saved build's persisted role selects from the map at
    Generate time. Missing role-specific composition is allowed so roles without a
    canonical composer remain on the existing role-neutral path instead of being guessed.
    """

    def __init__(
        self,
        *,
        static_context_service: RotationStaticBuildContextService | None = None,
        demand_policy_provider: RotationGenerateEncounterDemandPolicyProvider | None = None,
        role_evidence_composer: RotationGenerateRoleEvidenceComposer | None = None,
        role_evidence_composers: Mapping[
            str, RotationGenerateRoleEvidenceComposer
        ] | None = None,
    ) -> None:
        self.static_context_service = (
            static_context_service or RotationStaticBuildContextService()
        )
        self.demand_policy_provider = (
            demand_policy_provider or RotationEncounterDemandPolicyRegistryService()
        )
        self.role_evidence_composer = role_evidence_composer
        self.role_evidence_composers = {
            role_key: composer
            for raw_role, composer in dict(role_evidence_composers or {}).items()
            if (role_key := _canonical_role(raw_role))
        }

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

        demand_policies, threshold_policies, knowledge_gaps = self._demand_policy(
            encounter_id
        )
        difficulty = ""
        threshold_segments: tuple[RaidDamageSegment, ...] = ()
        if threshold_policies:
            threshold_context = page.canonical_threshold_projection_policy()
            difficulty = str(threshold_context.get("difficulty") or "").strip().casefold()
            raid_dps = threshold_context.get("raid_dps")
            if difficulty not in {"normal", "veteran", "hardmode"}:
                raise ValueError(
                    "select Normal, Veteran, or Hardmode before projecting health-threshold encounter demands"
                )
            if raid_dps is None or float(raid_dps) <= 0.0:
                raise ValueError(
                    "set explicit raid DPS before projecting health-threshold encounter demands"
                )
            threshold_segments = (
                RaidDamageSegment(
                    0.0,
                    None,
                    float(raid_dps),
                    "explicit Rotation Builder constant raid DPS input",
                ),
            )

        character_id = str(
            getattr(static_context.progression, "character_id", "") or ""
        ).strip() or None
        role_evidence_composer = self._role_evidence_composer_for(build)

        return RotationGenerateCanonicalContext(
            evidence_inputs=RotationSelectedEncounterEvidenceInputs(
                demand_policies=demand_policies,
                threshold_demand_policies=threshold_policies,
                threshold_damage_segments=threshold_segments,
                difficulty=difficulty,
                evaluator_resolver=None,
                scorecard_resolver=None,
                resource=resource,
                maximum_amount=maximum_amount,
                trigger_fraction=trigger,
                knowledge_gaps=knowledge_gaps,
            ),
            role_evidence_composer=role_evidence_composer,
            character_id=character_id,
        )

    def _role_evidence_composer_for(
        self,
        build,
    ) -> RotationGenerateRoleEvidenceComposer | None:
        if self.role_evidence_composer is not None:
            return self.role_evidence_composer
        role_key = _canonical_role(getattr(build, "Role", ""))
        if not role_key:
            return None
        return self.role_evidence_composers.get(role_key)

    def _demand_policy(
        self,
        encounter_id: str,
    ) -> tuple[
        tuple[EncounterRotationDemandPolicy, ...],
        tuple[EncounterThresholdRotationDemandPolicy, ...],
        tuple[CanonicalKnowledgeGap, ...],
    ]:
        provider = self.demand_policy_provider
        clock_policies = provider.policies_for(encounter_id)
        threshold_policies = provider.threshold_policies_for(encounter_id)

        review_blockers = ()
        blockers_for = getattr(provider, "review_blockers_for", None)
        if callable(blockers_for):
            review_blockers = tuple(blockers_for(encounter_id) or ())

        if clock_policies is not None and threshold_policies is not None:
            blocker_gaps = tuple(
                CanonicalKnowledgeGap(
                    domain=CanonicalKnowledgeDomain.ENCOUNTER_DEMAND,
                    key=f"{encounter_id}.{blocker.key}",
                    summary=blocker.summary,
                    needed_evidence=blocker.needed_evidence,
                    consumers=("rotation_maker",),
                    source_context=(
                        blocker.source_context
                        or f"selected encounter: {encounter_id}"
                    ),
                    blocking=True,
                )
                for blocker in review_blockers
            )
            return tuple(clock_policies), tuple(threshold_policies), blocker_gaps

        return (), (), (
            CanonicalKnowledgeGap(
                domain=CanonicalKnowledgeDomain.ENCOUNTER_DEMAND,
                key=f"{encounter_id}.rotation_demand_policy",
                summary=(
                    "No explicit rotation demand policy is configured for the selected encounter."
                ),
                needed_evidence=(
                    "Persist or configure reviewed clock/threshold rotation demand policy for "
                    "this encounter, or explicitly record that this Generate scope has no demand policies."
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
