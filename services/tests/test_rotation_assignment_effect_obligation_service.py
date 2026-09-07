from __future__ import annotations

import pytest

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
from services.rotation_assignment_effect_obligation_service import (
    RotationAssignmentEffectObligationService,
    RotationAssignmentEffectPolicy,
)


def _build(role: Role = Role.HEALER, *, name: str = "DF Healer") -> CharacterBuild:
    return CharacterBuild(
        name=name,
        character_class=CharacterClass.WARDEN,
        role=role,
        character_id="char-a",
        character_name="Magrat",
    )


def _provider(
    *,
    member_id: str = "char-a",
    character_name: str = "Magrat",
    build_name: str = "DF Healer",
    requirement_id: str = "major_brittle",
    requirement_type: str = "major_brittle",
    encounter_id: str = "xalvakka_hm",
) -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id=requirement_id,
        encounter_id=encounter_id,
        requirement_type=requirement_type,
        member_id=member_id,
        character_name=character_name,
        build_name=build_name,
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("verified capability",),
    )


def _assignment(
    *,
    status: ProviderAssignmentStatus = ProviderAssignmentStatus.ASSIGNED,
    provider: ProviderCandidate | None = None,
    requirement_id: str = "major_brittle",
    requirement_type: str = "major_brittle",
    encounter_id: str = "xalvakka_hm",
) -> ProviderAssignment:
    primary = () if provider is None else (provider,)
    return ProviderAssignment(
        requirement_id=requirement_id,
        encounter_id=encounter_id,
        requirement_type=requirement_type,
        status=status,
        primary_providers=primary,
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def _policy(
    *,
    requirement_id: str = "major_brittle",
    requirement_type: str = "major_brittle",
    encounter_id: str = "xalvakka_hm",
) -> RotationAssignmentEffectPolicy:
    return RotationAssignmentEffectPolicy(
        requirement_id=requirement_id,
        encounter_id=encounter_id,
        requirement_type=requirement_type,
        effect_name="chilled",
        source_skill_name="Winter's Revenge",
        minimum_uptime=0.90,
        bar="back",
        source="verified rotation assignment policy",
    )


@pytest.mark.parametrize("role", (Role.HEALER, Role.TANK, Role.DAMAGE_DEALER))
def test_assignment_effect_obligation_derivation_is_role_neutral(role: Role) -> None:
    provider = _provider(build_name="Assigned Build")
    projection = RotationAssignmentEffectObligationService().derive(
        build=_build(role, name="Assigned Build"),
        member_id="char-a",
        assignments=(_assignment(provider=provider),),
        policies=(_policy(),),
    )

    assert projection.member_id == "char-a"
    assert projection.build_name == "Assigned Build"
    assert projection.role == role.value
    assert len(projection.obligations) == 1
    obligation = projection.obligations[0]
    assert obligation.assignment.requirement_id == "major_brittle"
    assert obligation.policy.source == "verified rotation assignment policy"
    assert obligation.requirement.effect_name == "chilled"
    assert obligation.requirement.source_skill_name == "Winter's Revenge"
    assert obligation.requirement.minimum_uptime == pytest.approx(0.90)
    assert obligation.requirement.bar == "back"


def test_only_assignments_owned_by_requested_member_become_obligations() -> None:
    projection = RotationAssignmentEffectObligationService().derive(
        build=_build(),
        member_id="char-a",
        assignments=(_assignment(provider=_provider(member_id="char-b")),),
        policies=(_policy(),),
    )

    assert projection.obligations == ()
    assert projection.requirements == ()


def test_unresolved_assignment_does_not_create_rotation_obligation() -> None:
    projection = RotationAssignmentEffectObligationService().derive(
        build=_build(),
        member_id="char-a",
        assignments=(
            _assignment(
                status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
                provider=None,
            ),
        ),
        policies=(_policy(),),
    )

    assert projection.requirements == ()


def test_assignment_without_effect_policy_is_outside_declared_effect_scope() -> None:
    projection = RotationAssignmentEffectObligationService().derive(
        build=_build(),
        member_id="char-a",
        assignments=(_assignment(provider=_provider()),),
        policies=(),
    )

    assert projection.requirements == ()


def test_policy_must_reference_existing_assignment() -> None:
    with pytest.raises(ValueError, match="without a provider assignment"):
        RotationAssignmentEffectObligationService().derive(
            build=_build(),
            member_id="char-a",
            assignments=(),
            policies=(_policy(),),
        )


def test_policy_metadata_must_match_exact_assignment() -> None:
    with pytest.raises(ValueError, match="requirement_type does not match"):
        RotationAssignmentEffectObligationService().derive(
            build=_build(),
            member_id="char-a",
            assignments=(_assignment(provider=_provider()),),
            policies=(_policy(requirement_type="major_force"),),
        )


def test_assigned_provider_build_must_match_rotation_build() -> None:
    with pytest.raises(ValueError, match="provider build does not match"):
        RotationAssignmentEffectObligationService().derive(
            build=_build(name="DF Healer"),
            member_id="char-a",
            assignments=(
                _assignment(provider=_provider(build_name="GH Healer")),
            ),
            policies=(_policy(),),
        )


def test_assigned_provider_character_must_match_rotation_build_when_known() -> None:
    with pytest.raises(ValueError, match="provider character does not match"):
        RotationAssignmentEffectObligationService().derive(
            build=_build(),
            member_id="char-a",
            assignments=(
                _assignment(provider=_provider(character_name="Not Magrat")),
            ),
            policies=(_policy(),),
        )


def test_duplicate_policy_requirement_id_fails_closed() -> None:
    assignment = _assignment(provider=_provider())
    with pytest.raises(ValueError, match="duplicate rotation assignment effect policy"):
        RotationAssignmentEffectObligationService().derive(
            build=_build(),
            member_id="char-a",
            assignments=(assignment,),
            policies=(_policy(), _policy()),
        )


def test_policy_requires_explicit_provenance_and_valid_uptime() -> None:
    with pytest.raises(ValueError, match="source must be non-empty"):
        RotationAssignmentEffectPolicy(
            requirement_id="major_brittle",
            encounter_id="xalvakka_hm",
            requirement_type="major_brittle",
            effect_name="chilled",
            source_skill_name="Winter's Revenge",
            minimum_uptime=0.90,
            source="",
        )

    with pytest.raises(ValueError, match="minimum_uptime"):
        RotationAssignmentEffectPolicy(
            requirement_id="major_brittle",
            encounter_id="xalvakka_hm",
            requirement_type="major_brittle",
            effect_name="chilled",
            source_skill_name="Winter's Revenge",
            minimum_uptime=1.1,
            source="verified",
        )
