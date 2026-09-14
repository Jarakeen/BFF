from minmax.ultimate_generation_sources import (
    CombatAttackUltimateGenerationSource,
    HeroismTier,
    HeroismUltimateGenerationSource,
    HeroismWindow,
)
from minmax.ultimate_resource_timeline import UltimateGenerationEvent
from services.ultimate_source_runtime_legality_service import (
    UltimateSourceRuntimeLegalityService,
)


def test_decisive_merges_minor_and_major_heroism_same_tick_once():
    events = (
        UltimateGenerationEvent(1.0, 3.0, "base combat Ultimate generation"),
        UltimateGenerationEvent(1.5, 1.0, "Minor source: Minor Heroism tick 1"),
        UltimateGenerationEvent(1.5, 3.0, "Major source: Major Heroism tick 1"),
        UltimateGenerationEvent(2.0, 3.0, "base combat Ultimate generation"),
        UltimateGenerationEvent(3.0, 1.0, "Minor source: Minor Heroism tick 2"),
        UltimateGenerationEvent(3.0, 3.0, "Major source: Major Heroism tick 2"),
    )

    row = UltimateSourceRuntimeLegalityService.decisive_opportunities_from_generation_events(
        events,
        score_seconds=3.0,
    )

    assert row.generation_events_reviewed == 6
    assert row.non_heroism_opportunities == 2
    assert row.heroism_events_reviewed == 4
    assert row.merged_heroism_opportunities == 2
    assert row.total_opportunities == 4
    assert row.all_procs_ultimate_ceiling == 4.0
    assert round(row.expected_extra_ultimate, 3) == 0.764


def test_reviewed_full_window_produces_40_decisive_opportunities():
    duration = 24.999
    base = CombatAttackUltimateGenerationSource().events(
        attack_times=tuple(float(second) for second in range(25)),
        duration_seconds=duration,
    )
    heroism = HeroismUltimateGenerationSource().events(
        windows=(
            HeroismWindow(HeroismTier.MINOR, 0.0, duration, source="Minor Heroism"),
            HeroismWindow(HeroismTier.MAJOR, 0.0, duration, source="Major Heroism"),
        ),
        duration_seconds=duration,
    )

    row = UltimateSourceRuntimeLegalityService.decisive_opportunities_from_generation_events(
        tuple((*base, *heroism)),
        score_seconds=duration,
    )

    assert len(base) == 24
    assert len(heroism) == 32
    assert row.heroism_events_reviewed == 32
    assert row.merged_heroism_opportunities == 16
    assert row.non_heroism_opportunities == 24
    assert row.total_opportunities == 40
    assert row.all_procs_ultimate_ceiling == 40.0
    assert round(row.expected_extra_ultimate, 3) == 7.64


def test_baron_requirement_uses_only_18_procs_after_40_decisive_ceiling():
    row = UltimateSourceRuntimeLegalityService.baron_zaudrus_requirement_after_decisive(
        required_ultimate_gap=110.0,
        decisive_all_procs_ceiling=40.0,
        score_window_seconds=24.999,
    )

    assert row.residual_gap_after_decisive == 70.0
    assert row.minimum_baron_procs == 18
    assert row.minimum_status_applications == 54
    assert row.baron_ultimate_at_minimum_procs == 72.0
    assert row.combined_ultimate_ceiling == 112.0
    assert row.surplus_over_gap == 2.0
    assert round(row.minimum_average_status_applications_per_second, 3) == 2.160
    assert row.closes_gap_at_all_procs_ceiling is True


def test_baron_requirement_fails_closed_on_invalid_trigger_semantics():
    try:
        UltimateSourceRuntimeLegalityService.baron_zaudrus_requirement_after_decisive(
            required_ultimate_gap=110.0,
            decisive_all_procs_ceiling=40.0,
            score_window_seconds=24.999,
            stacks_per_baron_proc=0,
        )
    except ValueError as exc:
        assert "stacks per proc" in str(exc)
    else:
        raise AssertionError("invalid Baron stack requirement must fail closed")
