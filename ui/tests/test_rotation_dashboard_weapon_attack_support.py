from ui.rotation_automatic_potion_cadence_candidate_support import (
    RotationAutomaticPotionCadenceCandidateSupport,
)
from ui.rotation_canonical_candidate_support import RotationCanonicalCandidateSupport
from ui.rotation_dashboard_canonical_candidate_support import (
    RotationDashboardCanonicalCandidateSupport,
)
from ui.rotation_runtime_snapshot_candidate_support import (
    RotationRuntimeSnapshotCandidateSupport,
)
from ui.rotation_saved_build_target_candidate_support import (
    RotationSavedBuildTargetCandidateSupport,
)
from ui.rotation_ultimate_affordability_candidate_support import (
    RotationUltimateAffordabilityCandidateSupport,
)
from ui.rotation_weapon_attack_candidate_support import (
    RotationWeaponAttackCandidateSupport,
)


def test_dashboard_default_shares_canonical_adapter_with_weapon_attack_support() -> None:
    support = RotationDashboardCanonicalCandidateSupport()

    runtime = support.canonical_candidates
    assert isinstance(runtime, RotationRuntimeSnapshotCandidateSupport)

    ultimate = runtime.canonical_candidates
    assert isinstance(ultimate, RotationUltimateAffordabilityCandidateSupport)

    potion = ultimate.canonical_candidates
    assert isinstance(potion, RotationAutomaticPotionCadenceCandidateSupport)

    target = potion.canonical_candidates
    assert isinstance(target, RotationSavedBuildTargetCandidateSupport)

    weapon = target.canonical_candidates
    assert isinstance(weapon, RotationWeaponAttackCandidateSupport)

    canonical = weapon.canonical_candidates
    assert isinstance(canonical, RotationCanonicalCandidateSupport)
    assert runtime.base_canonical is canonical
    assert runtime.build_adapter is canonical.build_adapter
    assert runtime.static_context_service is canonical.static_context_service
    assert weapon.build_adapter is canonical.build_adapter
    assert target.static_context_service is canonical.static_context_service
    assert weapon.static_context_service is canonical.static_context_service
