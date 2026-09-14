from __future__ import annotations

import pytest

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.role import Role
from services.encounter_provider_assignment import ProviderAssignment, ProviderAssignmentStatus
from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateStatus
from services.rotation_assignment_taunt_obligation_service import (
    RotationAssignmentTauntApplicationWindow,
    RotationAssignmentTauntObligationService,
    RotationAssignmentTauntPolicy,
)


def _build(*, name: str = "Main Tank") -> CharacterBuild:
    return CharacterBuild(
        name=name,
        character_class=CharacterClass.DRAGONKNIGHT,
        role=Role.TANK,
        character_id="tank-a",
        character_name="Tanky",
    )


def _provider(
    *,
    member_id: str = "tank-a",
    character_name: str = "Tanky",
    build_name: str = "Main Tank",
) -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id="boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="boss_taunt",
        member_id=member_id,
        character_name=character_name,
        build_name=build_name,
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("reviewed assignment capability",),
    )


def _assignment(
    *,
    status: ProviderAssignmentStatus = ProviderAssignmentStatus.ASSIGNED,
    provider: ProviderCandidate | None = None,
) -> ProviderAssignment:
    if provider is None and status is ProviderAssignmentStatus.ASSIGNED:
        provider = _provider()
    return ProviderAssignment(
        requirement_id="boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="boss_taunt",
        status=status,
        primary_providers=() if provider is None else (provider,),
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="reviewed tank assignment",
    )


def _policy() -> RotationAssignmentTauntPolicy:
    return RotationAssignmentTauntPolicy(
        requirement_id="boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="boss_taunt",
        source_skill_name="Pierce Armor",
        windows=(
            RotationAssignmentTauntApplicationWindow(
                occurrence_id="pull",
                window_start_seconds=0.0,
                window_end_seconds=2.0,
                bar="front",
            ),
            RotationAssignmentTauntApplicationWindow(
                occurrence_id="return_from_portal",
                window_start_seconds=45.0,
                window_end_seconds=47.0,
                bar="front",
            ),
        ),
        source="reviewed encounter strategy",
    )


def test_assigned_taunt_policy_projects_each_explicit_occurrence() -> None:
    result = RotationAssignmentTauntObligationService().derive(
        build=_build(),
        member_id="tank-a",
        assignments=(_assignment(),),
        policies=(_policy(),),
    )

    assert result.member_id == "tank-a"
    assert result.role == Role.TANK.value
    assert [row.requirement.requirement_id for row in result.obligations] == [
        "boss_taunt:pull",
        "boss_taunt:return_from_portal",
    ]
    assert [row.requirement.source_skill_name for row in result.obligations] == [
        "Pierce Armor",
        "Pierce Armor",
    ]
    assert result.requirements[0].window_start_seconds == 0.0
    assert result.requirements[1].window_start_seconds == 45.0
    assert result.requirements[0].provenance == (
        "assignment=boss_taunt",
        "encounter=taleria_hm",
        "source=reviewed encounter strategy",
    )


def test_assignment_owned_by_other_member_does_not_create_taunt_obligation() -> None:
    result = RotationAssignmentTauntObligationService().derive(
        build=_build(),
        member_id="tank-a",
        assignments=(_assignment(provider=_provider(member_id="tank-b")),),
        policies=(_policy(),),
    )

    assert result.requirements == ()


def test_unresolved_assignment_does_not_create_taunt_obligation() -> None:
    result = RotationAssignmentTauntObligationService().derive(
        build=_build(),
        member_id="tank-a",
        assignments=(
            _assignment(
                status=ProviderAssignmentStatus.UNRESOLVED_SELECTION,
                provider=None,
            ),
        ),
        policies=(_policy(),),
    )

    assert result.requirements == ()


def test_policy_metadata_and_provider_build_identity_fail_closed() -> None:
    bad_policy = RotationAssignmentTauntPolicy(
        requirement_id="boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="other",
        source_skill_name="Pierce Armor",
        windows=(RotationAssignmentTauntApplicationWindow("pull", 0.0, 2.0),),
        source="reviewed",
    )
    with pytest.raises(ValueError, match="requirement_type does not match"):
        RotationAssignmentTauntObligationService().derive(
            build=_build(),
            member_id="tank-a",
            assignments=(_assignment(),),
            policies=(bad_policy,),
        )

    with pytest.raises(ValueError, match="provider build does not match"):
        RotationAssignmentTauntObligationService().derive(
            build=_build(name="Different Tank"),
            member_id="tank-a",
            assignments=(_assignment(),),
            policies=(_policy(),),
        )


def test_policy_requires_unique_explicit_application_windows() -> None:
    window = RotationAssignmentTauntApplicationWindow("pull", 0.0, 2.0)
    with pytest.raises(ValueError, match="duplicate rotation assignment taunt occurrence_id"):
        RotationAssignmentTauntPolicy(
            requirement_id="boss_taunt",
            encounter_id="taleria_hm",
            requirement_type="boss_taunt",
            source_skill_name="Pierce Armor",
            windows=(window, window),
            source="reviewed",
        )


def test_assignment_taunt_policy_does_not_encode_duration_or_refresh_cadence() -> None:
    policy = _policy()

    assert not hasattr(policy, "duration_seconds")
    assert not hasattr(policy, "refresh_seconds")
    assert not hasattr(policy, "minimum_uptime")
