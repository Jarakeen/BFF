from __future__ import annotations

import pytest

from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.role import Role
from services.encounter_provider_assignment import ProviderAssignment, ProviderAssignmentStatus
from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateStatus
from services.rotation_assignment_taunt_maintenance_service import (
    RotationAssignmentTauntMaintenancePolicy,
    RotationAssignmentTauntMaintenanceService,
    RotationAssignmentTauntMaintenanceWindow,
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


def _policy() -> RotationAssignmentTauntMaintenancePolicy:
    return RotationAssignmentTauntMaintenancePolicy(
        requirement_id="boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="boss_taunt",
        source_skill_name="Pierce Armor",
        windows=(
            RotationAssignmentTauntMaintenanceWindow(
                occurrence_id="main_phase",
                target_key="taleria",
                active_start_seconds=0.0,
                active_end_seconds=45.0,
                bar="front",
            ),
            RotationAssignmentTauntMaintenanceWindow(
                occurrence_id="post_portal",
                target_key="taleria",
                active_start_seconds=55.0,
                active_end_seconds=90.0,
                bar="front",
            ),
        ),
        source="reviewed encounter ownership strategy",
    )


def test_assigned_policy_projects_continuous_target_ownership_windows() -> None:
    result = RotationAssignmentTauntMaintenanceService().derive(
        build=_build(),
        member_id="tank-a",
        assignments=(_assignment(),),
        policies=(_policy(),),
    )

    assert result.member_id == "tank-a"
    assert result.role == Role.TANK.value
    assert [item.requirement.requirement_id for item in result.obligations] == [
        "boss_taunt:main_phase",
        "boss_taunt:post_portal",
    ]
    assert [item.target_key for item in result.requirements] == ["taleria", "taleria"]
    assert [item.active_start_seconds for item in result.requirements] == [0.0, 55.0]
    assert [item.active_end_seconds for item in result.requirements] == [45.0, 90.0]
    assert result.requirements[0].provenance == (
        "assignment=boss_taunt",
        "encounter=taleria_hm",
        "source=reviewed encounter ownership strategy",
    )


def test_assignment_owned_by_other_member_does_not_create_maintenance() -> None:
    result = RotationAssignmentTauntMaintenanceService().derive(
        build=_build(),
        member_id="tank-a",
        assignments=(_assignment(provider=_provider(member_id="tank-b")),),
        policies=(_policy(),),
    )

    assert result.requirements == ()


def test_unresolved_assignment_does_not_create_maintenance() -> None:
    result = RotationAssignmentTauntMaintenanceService().derive(
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


def test_maintenance_requires_explicit_target_and_positive_window() -> None:
    with pytest.raises(ValueError, match="target_key is required"):
        RotationAssignmentTauntMaintenanceWindow(
            occurrence_id="bad",
            target_key=" ",
            active_start_seconds=0.0,
            active_end_seconds=10.0,
        )

    with pytest.raises(ValueError, match="greater than start"):
        RotationAssignmentTauntMaintenanceWindow(
            occurrence_id="bad",
            target_key="boss",
            active_start_seconds=10.0,
            active_end_seconds=10.0,
        )


def test_policy_metadata_and_provider_build_identity_fail_closed() -> None:
    bad_policy = RotationAssignmentTauntMaintenancePolicy(
        requirement_id="boss_taunt",
        encounter_id="taleria_hm",
        requirement_type="other",
        source_skill_name="Pierce Armor",
        windows=(
            RotationAssignmentTauntMaintenanceWindow(
                "main",
                "taleria",
                0.0,
                30.0,
            ),
        ),
        source="reviewed",
    )
    with pytest.raises(ValueError, match="requirement_type does not match"):
        RotationAssignmentTauntMaintenanceService().derive(
            build=_build(),
            member_id="tank-a",
            assignments=(_assignment(),),
            policies=(bad_policy,),
        )

    with pytest.raises(ValueError, match="provider build does not match"):
        RotationAssignmentTauntMaintenanceService().derive(
            build=_build(name="Different Tank"),
            member_id="tank-a",
            assignments=(_assignment(),),
            policies=(_policy(),),
        )


def test_policy_requires_unique_explicit_maintenance_windows() -> None:
    window = RotationAssignmentTauntMaintenanceWindow(
        "main",
        "taleria",
        0.0,
        30.0,
    )
    with pytest.raises(ValueError, match="duplicate rotation assignment taunt maintenance occurrence_id"):
        RotationAssignmentTauntMaintenancePolicy(
            requirement_id="boss_taunt",
            encounter_id="taleria_hm",
            requirement_type="boss_taunt",
            source_skill_name="Pierce Armor",
            windows=(window, window),
            source="reviewed",
        )


def test_assignment_maintenance_policy_does_not_encode_duration_or_refresh_strategy() -> None:
    policy = _policy()

    assert not hasattr(policy, "duration_seconds")
    assert not hasattr(policy, "refresh_lead_seconds")
    assert not hasattr(policy, "recast_interval_seconds")
