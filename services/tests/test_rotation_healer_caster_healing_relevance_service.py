from services.rotation_healer_caster_healing_relevance_service import (
    RotationHealerCasterHealingRelevance,
    RotationHealerCasterHealingRelevanceService,
)


def test_reviewed_nonhealing_rotation_skills_are_explicitly_non_caster_healing():
    service = RotationHealerCasterHealingRelevanceService()

    for skill_id in (
        "elemental_susceptibility",
        "expansive_frost_cloak",
        "winters_revenge",
    ):
        evidence = service.resolve(skill_id)
        assert evidence is not None
        assert evidence.relevance is RotationHealerCasterHealingRelevance.NO_CASTER_HEALING
        assert evidence.provenance
        assert evidence.game_version == "U50"


def test_overflowing_altar_preserves_external_conditional_healing_identity():
    evidence = RotationHealerCasterHealingRelevanceService().resolve(
        "overflowing_altar"
    )

    assert evidence is not None
    assert (
        evidence.relevance
        is RotationHealerCasterHealingRelevance.EXTERNAL_CONDITIONAL_HEALING
    )
    assert any("Minor Lifesteal" in item for item in evidence.provenance)


def test_unknown_skill_identity_is_not_assumed_nonhealing():
    assert RotationHealerCasterHealingRelevanceService().resolve("mystery_skill") is None


def test_identity_lookup_is_case_insensitive_but_semantic():
    evidence = RotationHealerCasterHealingRelevanceService().resolve(
        "EXPANSIVE_FROST_CLOAK"
    )

    assert evidence is not None
    assert evidence.skill_id == "expansive_frost_cloak"
