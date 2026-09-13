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



def test_named_gear_sources_receive_canonical_window_ceilings():
    fixtures = {
        "bloodspawn": (
            "6|r% chance to generate 0-13 Ultimate once every |cffffff5|r seconds",
            (1.0, 6.0, 11.0, 16.0, 21.0),
            65.0,
        ),
        "baron_zaudrus": (
            "gain 3 stacks then gain 4 Ultimate; lockout |cffffff1|r second",
            tuple(float(value) for value in range(1, 25)),
            96.0,
        ),
        "hide_of_the_werewolf": (
            "generate 6 Ultimate once every |cffffff5|r seconds",
            (1.0, 6.0, 11.0, 16.0, 21.0),
            30.0,
        ),
        "arkasis": (
            "gain |cffffff1-44|r Ultimate once every |cffffff30|r seconds",
            (1.0,),
            44.0,
        ),
        "arkays_charity": (
            "restore |cffffff13|r Ultimate once every |cffffff9|r seconds",
            (1.0, 10.0, 19.0),
            39.0,
        ),
    }
    for source_id, (record, triggers, expected) in fixtures.items():
        row = UltimateSourceRuntimeLegalityService.review(
            source_id,
            canonical_records=(record,),
            trigger_seconds=triggers,
        )
        assert row.status is UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION
        assert row.generated_ultimate_ceiling == expected
        assert row.remaining_ultimate_gap == 114.0 - expected


def test_named_gear_ceiling_fails_closed_when_cooldown_is_violated():
    row = UltimateSourceRuntimeLegalityService.review(
        "arkays_charity",
        canonical_records=(
            "restore |cffffff13|r Ultimate once every |cffffff9|r seconds",
        ),
        trigger_seconds=(1.0, 9.0),
    )
    assert row.status is UltimateSourceRuntimeStatus.CANONICAL_EVIDENCE_REQUIRED



def test_exhilarating_drain_max_rank_window_ceiling_is_115():
    row = UltimateSourceRuntimeLegalityService.review(
        "exhilarating_drain",
        canonical_records=(
            "generating |cffffff5|r Ultimate every |cffffff1|r second "
            "for |cffffff3|r seconds",
        ),
        trigger_seconds=tuple(float(value) for value in range(2, 25)),
    )
    assert row.status is UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION
    assert row.generated_ultimate_ceiling == 115.0
    assert row.remaining_ultimate_gap == 0.0


def test_decisive_all_proc_ceiling_counts_merged_heroism_once():
    opportunities = (
        *(float(value) for value in range(1, 25)),
        *(1.5 * float(value) for value in range(1, 17)),
    )
    row = UltimateSourceRuntimeLegalityService.review(
        "decisive",
        canonical_records=(
            "weapon_trait effect_type='ultimate_gain_chance' value=19.1 "
            "secondary_value=1.0 unit='percent'",
        ),
        trigger_seconds=opportunities,
    )
    assert row.status is UltimateSourceRuntimeStatus.SEARCH_STATE_MUTATION
    assert len(opportunities) == 40
    assert row.generated_ultimate_ceiling == 40.0
    assert row.remaining_ultimate_gap == 74.0
