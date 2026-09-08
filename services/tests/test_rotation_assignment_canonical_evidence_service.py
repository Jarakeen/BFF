from __future__ import annotations

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.role import Role
from services.encounter_provider_assignment import (
    ProviderAssignment,
    ProviderAssignmentStatus,
)
from services.encounter_provider_candidate import (
    ProviderCandidate,
    ProviderCandidateStatus,
)
from services.rotation_assignment_canonical_evidence_service import (
    RotationAssignmentCanonicalEvidenceService,
)
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectPolicy,
)
from services.rotation_assignment_policy_resolver import RotationAssignmentNonEffectPolicy


def _build() -> CharacterBuild:
    return CharacterBuild(
        name="DF Healer",
        character_class=CharacterClass.WARDEN,
        role=Role.HEALER,
        character_id="char-a",
        character_name="Magrat",
    )


def _provider(requirement_id: str) -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id=requirement_id,
        encounter_id="xalvakka_hm",
        requirement_type=requirement_id,
        member_id="char-a",
        character_name="Magrat",
        build_name="DF Healer",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("verified capability",),
    )


def _assignment(requirement_id: str) -> ProviderAssignment:
    return ProviderAssignment(
        requirement_id=requirement_id,
        encounter_id="xalvakka_hm",
        requirement_type=requirement_id,
        status=ProviderAssignmentStatus.ASSIGNED,
        primary_providers=(_provider(requirement_id),),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def test_complete_effect_policy_becomes_runtime_uptime_requirement() -> None:
    evidence = RotationAssignmentCanonicalEvidenceService().build(
        build=_build(),
        member_id="char-a",
        assignments=(_assignment("major_brittle"),),
        effect_policies=(
            RotationAssignmentEffectPolicy(
                requirement_id="major_brittle",
                encounter_id="xalvakka_hm",
                requirement_type="major_brittle",
                effect_name="chilled",
                source_skill_name="Winter's Revenge",
                minimum_uptime=0.90,
                bar="back",
                source="reviewed assignment strategy",
            ),
        ),
    )

    assert evidence.ready is True
    assert evidence.knowledge_gaps == ()
    assert evidence.obligation_projection is not None
    assert len(evidence.requirements) == 1
    requirement = evidence.requirements[0]
    assert requirement.effect_name == "chilled"
    assert requirement.source_skill_name == "Winter's Revenge"
    assert requirement.minimum_uptime == 0.90
    assert requirement.bar == "back"


def test_explicit_non_effect_assignment_is_ready_without_fake_uptime_requirement() -> None:
    evidence = RotationAssignmentCanonicalEvidenceService().build(
        build=_build(),
        member_id="char-a",
        assignments=(_assignment("portal_position"),),
        non_effect_policies=(
            RotationAssignmentNonEffectPolicy(
                requirement_id="portal_position",
                encounter_id="xalvakka_hm",
                requirement_type="portal_position",
                reason="Positioning model owns this responsibility.",
                source="reviewed strategy evidence",
            ),
        ),
    )

    assert evidence.ready is True
    assert evidence.requirements == ()
    assert evidence.obligation_projection is not None
    assert evidence.policy_resolution.non_effect_policies[0].requirement_id == "portal_position"


def test_missing_assignment_policy_stops_obligation_derivation_and_surfaces_research() -> None:
    evidence = RotationAssignmentCanonicalEvidenceService().build(
        build=_build(),
        member_id="char-a",
        assignments=(_assignment("major_brittle"),),
    )

    assert evidence.ready is False
    assert evidence.requirements == ()
    assert evidence.obligation_projection is None
    assert len(evidence.knowledge_gaps) == 1
    gap = evidence.knowledge_gaps[0]
    assert gap.key == "xalvakka_hm:major_brittle"
    assert "comp_maker" in gap.consumers
    assert "rotation_maker" in gap.consumers
    assert "optimizer" in gap.consumers
