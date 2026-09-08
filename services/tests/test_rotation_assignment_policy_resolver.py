from __future__ import annotations

import pytest

from services.canonical_knowledge_gap import CanonicalKnowledgeDomain
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateStatus,
)
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectPolicy,
)
from services.rotation_assignment_policy_resolver import (
    RotationAssignmentNonEffectPolicy,
    RotationAssignmentPolicyResolver,
)


def _provider(*, member_id: str = "char-a", requirement_id: str = "major_brittle") -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id=requirement_id,
        encounter_id="xalvakka_hm",
        requirement_type=requirement_id,
        member_id=member_id,
        character_name="Magrat",
        build_name="DF Healer",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("verified capability",),
    )


def _assignment(
    *,
    requirement_id: str = "major_brittle",
    member_id: str = "char-a",
    status: ProviderAssignmentStatus = ProviderAssignmentStatus.ASSIGNED,
) -> ProviderAssignment:
    primaries = () if status is not ProviderAssignmentStatus.ASSIGNED else (_provider(member_id=member_id, requirement_id=requirement_id),)
    return ProviderAssignment(
        requirement_id=requirement_id,
        encounter_id="xalvakka_hm",
        requirement_type=requirement_id,
        status=status,
        primary_providers=primaries,
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def _effect_policy(requirement_id: str = "major_brittle") -> RotationAssignmentEffectPolicy:
    return RotationAssignmentEffectPolicy(
        requirement_id=requirement_id,
        encounter_id="xalvakka_hm",
        requirement_type=requirement_id,
        effect_name="chilled",
        source_skill_name="Winter's Revenge",
        minimum_uptime=0.90,
        source="reviewed strategy evidence",
        bar="back",
    )


def _non_effect_policy(requirement_id: str = "portal_position") -> RotationAssignmentNonEffectPolicy:
    return RotationAssignmentNonEffectPolicy(
        requirement_id=requirement_id,
        encounter_id="xalvakka_hm",
        requirement_type=requirement_id,
        reason="Fulfilled by explicit positioning mechanics, not effect uptime.",
        source="reviewed strategy evidence",
    )


def test_resolves_effect_and_explicit_non_effect_dispositions() -> None:
    resolution = RotationAssignmentPolicyResolver().resolve(
        member_id="char-a",
        assignments=(
            _assignment(requirement_id="major_brittle"),
            _assignment(requirement_id="portal_position"),
        ),
        effect_policies=(_effect_policy(),),
        non_effect_policies=(_non_effect_policy(),),
    )

    assert resolution.ready is True
    assert [item.requirement_id for item in resolution.effect_policies] == ["major_brittle"]
    assert [item.requirement_id for item in resolution.non_effect_policies] == ["portal_position"]
    assert resolution.knowledge_gaps == ()


def test_owned_assignment_without_disposition_becomes_shared_research_gap() -> None:
    resolution = RotationAssignmentPolicyResolver().resolve(
        member_id="char-a",
        assignments=(_assignment(requirement_id="major_brittle"),),
    )

    assert resolution.ready is False
    assert len(resolution.knowledge_gaps) == 1
    gap = resolution.knowledge_gaps[0]
    assert gap.domain is CanonicalKnowledgeDomain.ASSIGNMENT_POLICY
    assert gap.key == "xalvakka_hm:major_brittle"
    assert gap.consumers == ("comp_maker", "rotation_maker", "optimizer")
    assert "effect identity" in gap.needed_evidence
    assert "non-effect disposition" in gap.needed_evidence


def test_assignment_owned_by_another_member_does_not_block_requested_member() -> None:
    resolution = RotationAssignmentPolicyResolver().resolve(
        member_id="char-a",
        assignments=(_assignment(member_id="char-b"),),
    )

    assert resolution.ready is True
    assert resolution.effect_policies == ()
    assert resolution.non_effect_policies == ()
    assert resolution.knowledge_gaps == ()


def test_unresolved_assignment_does_not_claim_member_ownership() -> None:
    resolution = RotationAssignmentPolicyResolver().resolve(
        member_id="char-a",
        assignments=(
            _assignment(status=ProviderAssignmentStatus.UNRESOLVED_SELECTION),
        ),
    )

    assert resolution.ready is True
    assert resolution.knowledge_gaps == ()


def test_requirement_cannot_be_declared_effect_and_non_effect() -> None:
    with pytest.raises(ValueError, match="both effect and non-effect"):
        RotationAssignmentPolicyResolver().resolve(
            member_id="char-a",
            assignments=(_assignment(),),
            effect_policies=(_effect_policy(),),
            non_effect_policies=(
                RotationAssignmentNonEffectPolicy(
                    requirement_id="major_brittle",
                    encounter_id="xalvakka_hm",
                    requirement_type="major_brittle",
                    reason="not actually appropriate",
                    source="test",
                ),
            ),
        )


def test_policy_metadata_must_match_assignment() -> None:
    with pytest.raises(ValueError, match="encounter_id does not match"):
        RotationAssignmentPolicyResolver().resolve(
            member_id="char-a",
            assignments=(_assignment(),),
            effect_policies=(
                RotationAssignmentEffectPolicy(
                    requirement_id="major_brittle",
                    encounter_id="other_encounter",
                    requirement_type="major_brittle",
                    effect_name="chilled",
                    source_skill_name="Winter's Revenge",
                    minimum_uptime=0.90,
                    source="test",
                ),
            ),
        )
