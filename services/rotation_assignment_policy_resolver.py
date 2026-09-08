from __future__ import annotations

from dataclasses import dataclass

from services.canonical_knowledge_gap import (
    CanonicalKnowledgeDomain,
    CanonicalKnowledgeGap,
)
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectPolicy,
)


@dataclass(frozen=True)
class RotationAssignmentNonEffectPolicy:
    """Verified declaration that an assignment is not an effect-uptime obligation.

    This is not a loophole for missing data. It is positive evidence that the exact
    assignment is fulfilled through another mechanic model, such as positioning,
    target handling, interrupt timing, survival, or another non-uptime obligation.
    """

    requirement_id: str
    encounter_id: str
    requirement_type: str
    reason: str
    source: str

    def __post_init__(self) -> None:
        for field_name in (
            "requirement_id",
            "encounter_id",
            "requirement_type",
            "reason",
            "source",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"rotation non-effect policy {field_name} must be non-empty")
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True)
class RotationAssignmentPolicyResolution:
    """Complete policy disposition for assignments owned by one member."""

    member_id: str
    effect_policies: tuple[RotationAssignmentEffectPolicy, ...]
    non_effect_policies: tuple[RotationAssignmentNonEffectPolicy, ...]
    knowledge_gaps: tuple[CanonicalKnowledgeGap, ...]

    @property
    def ready(self) -> bool:
        return not self.knowledge_gaps

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(gap.summary for gap in self.knowledge_gaps)


class RotationAssignmentPolicyResolver:
    """Resolve every owned assignment to explicit rotation semantics or a gap.

    The resolver deliberately refuses to use absence of an effect policy as proof
    that an assignment is irrelevant to Rotation Maker. Every assignment owned by
    the requested member must have exactly one explicit disposition:

    * RotationAssignmentEffectPolicy: a timed cast-produced effect obligation, or
    * RotationAssignmentNonEffectPolicy: verified evidence that another mechanic
      model owns the responsibility.

    Missing disposition becomes a reusable CanonicalKnowledgeGap for Comp Maker,
    Rotation Maker, and Optimizer research/readiness reporting.
    """

    def resolve(
        self,
        *,
        member_id: str,
        assignments: tuple[ProviderAssignment, ...],
        effect_policies: tuple[RotationAssignmentEffectPolicy, ...] = (),
        non_effect_policies: tuple[RotationAssignmentNonEffectPolicy, ...] = (),
    ) -> RotationAssignmentPolicyResolution:
        resolved_member_id = str(member_id or "").strip()
        if not resolved_member_id:
            raise ValueError("rotation assignment policy resolution requires member_id")

        assignment_by_id = self._unique_by_requirement(
            assignments,
            kind="provider assignment",
        )
        effect_by_id = self._unique_by_requirement(
            effect_policies,
            kind="rotation assignment effect policy",
        )
        non_effect_by_id = self._unique_by_requirement(
            non_effect_policies,
            kind="rotation assignment non-effect policy",
        )

        overlap = set(effect_by_id) & set(non_effect_by_id)
        if overlap:
            requirement_id = sorted(overlap)[0]
            raise ValueError(
                "rotation assignment requirement cannot be both effect and non-effect policy: "
                f"{requirement_id!r}"
            )

        for policy in (*effect_policies, *non_effect_policies):
            assignment = assignment_by_id.get(policy.requirement_id.casefold())
            if assignment is None:
                raise ValueError(
                    "rotation assignment policy references a requirement without a provider assignment: "
                    f"{policy.requirement_id!r}"
                )
            self._validate_policy_metadata(policy, assignment)

        resolved_effects: list[RotationAssignmentEffectPolicy] = []
        resolved_non_effects: list[RotationAssignmentNonEffectPolicy] = []
        gaps: list[CanonicalKnowledgeGap] = []

        for assignment in assignments:
            if assignment.status is not ProviderAssignmentStatus.ASSIGNED:
                continue
            primaries = tuple(
                provider
                for provider in assignment.primary_providers
                if provider.member_id == resolved_member_id
            )
            if not primaries:
                continue
            if len(primaries) > 1:
                raise ValueError(
                    "provider assignment contains duplicate primary provider identity for "
                    f"member {resolved_member_id!r} and requirement {assignment.requirement_id!r}"
                )

            key = assignment.requirement_id.casefold()
            effect_policy = effect_by_id.get(key)
            non_effect_policy = non_effect_by_id.get(key)
            if effect_policy is not None:
                resolved_effects.append(effect_policy)
                continue
            if non_effect_policy is not None:
                resolved_non_effects.append(non_effect_policy)
                continue

            gaps.append(
                CanonicalKnowledgeGap(
                    domain=CanonicalKnowledgeDomain.ASSIGNMENT_POLICY,
                    key=f"{assignment.encounter_id}:{assignment.requirement_id}",
                    summary=(
                        "Owned encounter assignment has no explicit rotation policy disposition: "
                        f"{assignment.requirement_id}"
                    ),
                    needed_evidence=(
                        "Determine whether this assignment is fulfilled by a timed cast-produced "
                        "effect. If yes, provide exact effect identity, source skill, bar if "
                        "required, minimum uptime, and provenance. If no, provide a verified "
                        "non-effect disposition identifying the mechanic model that owns it."
                    ),
                    consumers=("comp_maker", "rotation_maker", "optimizer"),
                    source_context=(
                        f"encounter={assignment.encounter_id}; "
                        f"requirement_type={assignment.requirement_type}; "
                        f"provider_member={resolved_member_id}"
                    ),
                )
            )

        return RotationAssignmentPolicyResolution(
            member_id=resolved_member_id,
            effect_policies=tuple(resolved_effects),
            non_effect_policies=tuple(resolved_non_effects),
            knowledge_gaps=tuple(gaps),
        )

    @staticmethod
    def _unique_by_requirement(rows, *, kind: str):
        result = {}
        for row in rows:
            key = row.requirement_id.casefold()
            if key in result:
                raise ValueError(f"duplicate {kind} requirement_id: {row.requirement_id!r}")
            result[key] = row
        return result

    @staticmethod
    def _validate_policy_metadata(policy, assignment: ProviderAssignment) -> None:
        if policy.encounter_id != assignment.encounter_id:
            raise ValueError(
                f"rotation assignment policy encounter_id does not match assignment for {policy.requirement_id!r}"
            )
        if policy.requirement_type != assignment.requirement_type:
            raise ValueError(
                f"rotation assignment policy requirement_type does not match assignment for {policy.requirement_id!r}"
            )


__all__ = [
    "RotationAssignmentNonEffectPolicy",
    "RotationAssignmentPolicyResolution",
    "RotationAssignmentPolicyResolver",
]
