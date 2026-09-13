from services.ultimate_source_runtime_legality_service import (
    UltimateSourceRuntimeLegalityService,
    UltimateSourceRuntimeStatus,
)


def test_pillagers_profit_excludes_the_caster():
    row = UltimateSourceRuntimeLegalityService.review(
        "pillagers_profit",
        canonical_records=("grants Ultimate to up to 11 other group members",),
    )
    assert row.status is UltimateSourceRuntimeStatus.SELF_INCOMPATIBLE
    assert row.generated_ultimate_ceiling == 0.0


def test_cryptcanon_cannot_share_the_booming_voice_cast_route():
    row = UltimateSourceRuntimeLegalityService.review(
        "cryptcanon_vestments",
        canonical_records=("You can no longer cast Ultimate abilities.",),
    )
    assert row.status is UltimateSourceRuntimeStatus.ROUTE_INCOMPATIBLE


def test_blessing_at_the_peak_closes_four_points_of_the_gap():
    row = UltimateSourceRuntimeLegalityService.review(
        "blessing_peak",
        canonical_records=(
            "When you cast or deal damage with an Earthen Heart ability in combat "
            "you generate |cffffff1|r Ultimate. This effect can occur once every "
            "|cffffff6|r seconds.",
        ),
        trigger_seconds=(1.0, 7.0, 13.0, 19.0),
    )
    assert row.status is UltimateSourceRuntimeStatus.COMPATIBLE_INCREMENT
    assert row.generated_ultimate_ceiling == 4.0
    assert row.remaining_ultimate_gap == 110.0


def test_blessing_fails_closed_without_legal_trigger_witness():
    row = UltimateSourceRuntimeLegalityService.review(
        "blessing_peak",
        canonical_records=(
            "generate |cffffff1|r Ultimate once every |cffffff6|r seconds",
        ),
        trigger_seconds=(1.0, 6.0),
    )
    assert row.status is UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED


def test_unresolved_equipment_source_remains_a_search_mutation():
    row = UltimateSourceRuntimeLegalityService.review("arkasis")
    assert row.status is UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION
