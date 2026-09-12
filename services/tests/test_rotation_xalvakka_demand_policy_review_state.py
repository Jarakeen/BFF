from services.rotation_encounter_demand_policy_registry_service import (
    RotationEncounterDemandPolicyRegistryService,
)


def test_production_xalvakka_policy_keeps_distinct_healer_obligations_blocked() -> None:
    service = RotationEncounterDemandPolicyRegistryService()

    assert service.policies_for("xalvakka") == ()
    assert service.threshold_policies_for("xalvakka") == ()

    blockers = service.review_blockers_for("xalvakka")
    assert blockers is not None
    assert tuple(blocker.key for blocker in blockers) == (
        "creeping_manifold_healer_demand",
        "xalvakka_stair_transition_healer_demand",
        "xalvakka_split_floor_healer_demand",
    )

    manifold, stairs, split = blockers
    assert "unavoidable flame damage" in manifold.summary
    assert "Heal-Check (Manifold)" in manifold.source_context

    assert "70% and 40%" in stairs.summary
    assert "3-second preparation lead" in stairs.needed_evidence
    assert "Healing Stairs" in stairs.source_context

    assert "continuous flame damage" in split.summary
    assert "Healing/sustained pressure is source-supported" in split.needed_evidence
    assert "Healing Triple Split Damage" in split.source_context
