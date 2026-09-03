from minmax.build_candidate_capability import (
    compare_capability_coverage,
    compare_provider_responsibilities,
)
from minmax.build_candidate_comparison import ConstraintStatus
from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from services.encounter_provider_assignment import ProviderAssignment, ProviderAssignmentStatus
from services.encounter_provider_candidate import ProviderCandidate, ProviderCandidateStatus
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _audit(*names: str, capability_unresolved: tuple[str, ...] = ()) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name="Magrat",
        build_name="DF Healer",
        character_id="magrat",
        resolved_sources=("test",),
        resolved_effects=tuple(
            EffectVariant(name=name, layer=EffectLayer.CAST, source=f"source:{name}")
            for name in names
        ),
        conditional_sources=(),
        unresolved=capability_unresolved,
        capability_unresolved=capability_unresolved,
        boundaries=(),
    )


def _provider(member_id: str = "magrat") -> ProviderCandidate:
    return ProviderCandidate(
        requirement_id="req-1",
        encounter_id="enc-1",
        requirement_type="major_courage",
        member_id=member_id,
        character_name="Magrat",
        build_name="DF Healer",
        status=ProviderCandidateStatus.VIABLE,
        evidence_sources=("canonical:test",),
    )


def _assignment(
    status: ProviderAssignmentStatus,
    *,
    primary: tuple[ProviderCandidate, ...] = (),
) -> ProviderAssignment:
    return ProviderAssignment(
        requirement_id="req-1",
        encounter_id="enc-1",
        requirement_type="major_courage",
        status=status,
        primary_providers=primary,
        backup_providers=(),
        unresolved_candidates=(),
        conflicting_candidates=(),
        explanation="test assignment",
    )


def test_capability_coverage_preserves_stable_effect_identities() -> None:
    result = compare_capability_coverage(
        _audit("major_courage", "minor_intellect"),
        _audit("minor_intellect", "major_courage"),
    )

    assert result.status is ConstraintStatus.PRESERVED


def test_capability_coverage_blocks_lost_resolved_effect() -> None:
    result = compare_capability_coverage(
        _audit("major_courage", "minor_intellect"),
        _audit("minor_intellect"),
    )

    assert result.status is ConstraintStatus.WORSENED
    assert "major_courage" in result.explanation


def test_capability_coverage_keeps_unresolved_baseline_unknown() -> None:
    result = compare_capability_coverage(
        _audit("major_courage", capability_unresolved=("baseline skill unresolved",)),
        _audit("major_courage"),
    )

    assert result.status is ConstraintStatus.UNKNOWN
    assert "baseline skill unresolved" in result.explanation


def test_capability_coverage_keeps_unresolved_candidate_unknown() -> None:
    result = compare_capability_coverage(
        _audit("major_courage"),
        _audit("major_courage", capability_unresolved=("candidate skill unresolved",)),
    )

    assert result.status is ConstraintStatus.UNKNOWN
    assert "candidate skill unresolved" in result.explanation


def test_provider_responsibility_preserves_exact_primary_assignment() -> None:
    provider = _provider()
    result = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=(_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(provider,)),),
        candidate_assignments=(_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(provider,)),),
    )

    assert result.status is ConstraintStatus.PRESERVED


def test_provider_responsibility_blocks_candidate_that_loses_primary_duty() -> None:
    baseline_provider = _provider()
    other_provider = _provider("other-healer")
    result = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=(_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(baseline_provider,)),),
        candidate_assignments=(_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(other_provider,)),),
    )

    assert result.status is ConstraintStatus.WORSENED
    assert "req-1" in result.explanation


def test_provider_responsibility_keeps_unresolved_reassignment_unknown() -> None:
    provider = _provider()
    result = compare_provider_responsibilities(
        member_id="magrat",
        baseline_assignments=(_assignment(ProviderAssignmentStatus.ASSIGNED, primary=(provider,)),),
        candidate_assignments=(_assignment(ProviderAssignmentStatus.UNRESOLVED_CAPABILITY),),
    )

    assert result.status is ConstraintStatus.UNKNOWN
    assert "req-1" in result.explanation
