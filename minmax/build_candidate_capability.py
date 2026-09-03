from __future__ import annotations

from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from services.encounter_provider_assignment import ProviderAssignment, ProviderAssignmentStatus
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _effect_names(audit: SavedBuildCapabilityAudit) -> set[str]:
    """Return stable logical capability identities from a Phase 10 audit."""

    return {
        effect.name
        for effect in audit.resolved_effects
        if effect.eligible
    }


def compare_capability_coverage(
    baseline: SavedBuildCapabilityAudit,
    candidate: SavedBuildCapabilityAudit,
) -> CandidateConstraint:
    """Compare candidate static capability coverage through Phase 10 evidence.

    Phase 12 does not reinterpret skills, gear, potions, conditions, or effect
    magnitudes here. ``SavedBuildCapabilityService`` remains authoritative for
    resolving those details. Effect identity follows ``EffectVariant.name``.
    """

    if candidate.capability_unresolved:
        return CandidateConstraint(
            name="capability_coverage",
            status=ConstraintStatus.UNKNOWN,
            explanation=(
                "Candidate capability coverage is unresolved: "
                + "; ".join(candidate.capability_unresolved)
            ),
        )

    baseline_names = _effect_names(baseline)
    candidate_names = _effect_names(candidate)
    lost = tuple(sorted(baseline_names - candidate_names))
    gained = tuple(sorted(candidate_names - baseline_names))

    if lost:
        return CandidateConstraint(
            name="capability_coverage",
            status=ConstraintStatus.WORSENED,
            explanation="Candidate loses resolved capability: " + ", ".join(lost),
        )
    if gained:
        return CandidateConstraint(
            name="capability_coverage",
            status=ConstraintStatus.IMPROVED,
            explanation="Candidate preserves baseline coverage and adds: " + ", ".join(gained),
        )
    return CandidateConstraint(
        name="capability_coverage",
        status=ConstraintStatus.PRESERVED,
        explanation="Candidate preserves all resolved baseline capability identities.",
    )


def compare_provider_responsibilities(
    *,
    member_id: str,
    baseline_assignments: tuple[ProviderAssignment, ...],
    candidate_assignments: tuple[ProviderAssignment, ...],
) -> CandidateConstraint:
    """Require candidate Phase 11 assignments to preserve exact primary duties.

    Assignment selection itself remains owned by Phase 11. This function only
    compares the resulting exact requirement ownership for one roster member.
    """

    baseline_primary = {
        assignment.requirement_id
        for assignment in baseline_assignments
        if assignment.status is ProviderAssignmentStatus.ASSIGNED
        and any(provider.member_id == member_id for provider in assignment.primary_providers)
    }
    if not baseline_primary:
        return CandidateConstraint(
            name="provider_responsibility",
            status=ConstraintStatus.PRESERVED,
            explanation="Baseline has no assigned primary provider responsibilities for this member.",
        )

    candidate_by_requirement = {
        assignment.requirement_id: assignment
        for assignment in candidate_assignments
    }
    missing_rows = tuple(sorted(baseline_primary - set(candidate_by_requirement)))
    if missing_rows:
        return CandidateConstraint(
            name="provider_responsibility",
            status=ConstraintStatus.UNKNOWN,
            explanation=(
                "Candidate assignment evidence is missing for baseline responsibility: "
                + ", ".join(missing_rows)
            ),
        )

    unresolved: list[str] = []
    lost: list[str] = []
    for requirement_id in sorted(baseline_primary):
        assignment = candidate_by_requirement[requirement_id]
        if assignment.status is not ProviderAssignmentStatus.ASSIGNED:
            if assignment.status in {
                ProviderAssignmentStatus.UNRESOLVED_SELECTION,
                ProviderAssignmentStatus.UNRESOLVED_CAPABILITY,
                ProviderAssignmentStatus.UNRESOLVED_SUITABILITY,
            }:
                unresolved.append(requirement_id)
            else:
                lost.append(requirement_id)
            continue
        if not any(provider.member_id == member_id for provider in assignment.primary_providers):
            lost.append(requirement_id)

    if lost:
        return CandidateConstraint(
            name="provider_responsibility",
            status=ConstraintStatus.WORSENED,
            explanation="Candidate no longer owns assigned primary responsibility: " + ", ".join(lost),
        )
    if unresolved:
        return CandidateConstraint(
            name="provider_responsibility",
            status=ConstraintStatus.UNKNOWN,
            explanation="Candidate responsibility is unresolved for: " + ", ".join(unresolved),
        )

    return CandidateConstraint(
        name="provider_responsibility",
        status=ConstraintStatus.PRESERVED,
        explanation="Candidate preserves every baseline primary provider responsibility.",
    )
