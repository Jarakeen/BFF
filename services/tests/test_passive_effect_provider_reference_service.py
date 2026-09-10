from services.passive_effect_provider_reference_service import PassiveEffectProviderReferenceService


def test_passive_provider_catalog_contains_reviewed_named_effect_relationships():
    rows = PassiveEffectProviderReferenceService().all()
    pairs = {(row.passive_name, row.effect_name) for row in rows}

    assert ("Elder Dragon", "Minor Brutality") in pairs
    assert ("Illuminate", "Minor Sorcery") in pairs
    assert ("Sacred Ground", "Minor Mending") in pairs
    assert ("Accelerated Growth", "Major Mending") in pairs
    assert ("Maturation", "Minor Toughness") in pairs
    assert ("Shadow Barrier", "Major Resolve") in pairs


def test_passive_provider_preserves_conditions_targets_and_rank_durations():
    service = PassiveEffectProviderReferenceService()

    sacred_ground = service.for_passive("Sacred Ground")[0]
    assert sacred_ground.effect_name == "Minor Mending"
    assert sacred_ground.target == "Self"
    assert sacred_ground.duration_rank_1 == 2.0
    assert sacred_ground.duration_rank_2 == 4.0
    assert "Cleansing Ritual" in sacred_ground.condition

    shadow_barrier = service.for_passive("Shadow Barrier")[0]
    assert shadow_barrier.duration_rank_1 == 6.0
    assert shadow_barrier.duration_rank_2 == 12.0
    assert "2 seconds" in shadow_barrier.condition
    assert "Heavy Armor" in shadow_barrier.condition


def test_passive_provider_effect_lookup_is_case_insensitive_and_bounded():
    service = PassiveEffectProviderReferenceService()

    assert {row.passive_name for row in service.for_effect("major mending")} == {
        "Accelerated Growth"
    }
    assert service.for_effect("Imaginary Buff") == ()
    assert service.for_passive("Imaginary Passive") == ()


def test_minor_sorcery_provider_keeps_u50_version_boundary_visible():
    illuminate = PassiveEffectProviderReferenceService().for_passive("Illuminate")[0]

    assert illuminate.game_update == "U50"
    assert illuminate.effect_name == "Minor Sorcery"
    assert any("U51" in evidence for evidence in illuminate.evidence)
