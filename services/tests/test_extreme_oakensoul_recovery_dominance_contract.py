from __future__ import annotations

from minmax.ultimate_generation_sources import (
    HeroismTier,
    HeroismUltimateGenerationSource,
    HeroismWindow,
)
from services.extreme_percent_vs_flat_dominance_service import (
    ExtremePercentVsFlatDominanceService,
)
from services.named_buff_resolution_service import (
    NamedBuffContribution,
    NamedBuffResolutionService,
)


def test_duplicate_minor_heroism_does_not_stack_across_runtime_and_gear_sources() -> None:
    source = HeroismUltimateGenerationSource()
    duration = 24.999
    events = source.events(
        windows=(
            HeroismWindow(
                HeroismTier.MINOR,
                0.0,
                duration,
                source="reviewed Strategic Reserve baseline",
            ),
        ),
        duration_seconds=duration,
    )
    generated = sum(event.amount for event in events)
    assert generated == 16.0

    result = NamedBuffResolutionService.explain(
        (
            NamedBuffContribution(
                "Minor Heroism",
                "ultimate_generation",
                generated,
                "reviewed Strategic Reserve baseline",
                "runtime",
            ),
            NamedBuffContribution(
                "Minor Heroism",
                "ultimate_generation",
                generated,
                "Oakensoul Ring",
                "gear",
            ),
        ),
        objective_key="ultimate_generation",
    )

    assert len(result.selected) == 1
    assert len(result.suppressed) == 1
    assert result.selected[0].projected_delta == 16.0


def test_oakensoul_incumbent_percent_ceiling_is_below_adamant_displacement() -> None:
    result = ExtremePercentVsFlatDominanceService.assess(
        pre_percent_subtotal_upper_bound=7764.806,
        percent_ceiling=15.0,
        displaced_flat_value=1247.0,
    )

    assert round(result.percent_gain_upper_bound, 3) == 1164.721
    assert result.dominated is True


def test_oakensoul_survivor_percent_ceiling_is_below_adamant_displacement() -> None:
    result = ExtremePercentVsFlatDominanceService.assess(
        pre_percent_subtotal_upper_bound=7635.806,
        percent_ceiling=15.0,
        displaced_flat_value=1247.0,
    )

    assert round(result.percent_gain_upper_bound, 3) == 1145.371
    assert result.dominated is True
