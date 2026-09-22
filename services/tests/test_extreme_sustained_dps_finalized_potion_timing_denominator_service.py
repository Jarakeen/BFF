from __future__ import annotations

from minmax.character_progression import CharacterProgression
from minmax.potion_use_event import PotionBuffGrant, PotionTraitUse, PotionUseEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_finalized_potion_timing_denominator_service import (
    ExtremeSustainedDPSFinalizedPotionTimingDenominatorService,
)
from services.extreme_sustained_dps_potion_observation_frontier_service import (
    ExtremeSustainedDPSPotionObservationFrontier,
)


class _Resolver:
    def resolve(self, name):
        assert name == "Potion X"
        return PotionUseEvent(
            selected_label="Potion X",
            traits=(
                PotionTraitUse(
                    trait="Increase Spell Power",
                    kind="timed_trait",
                    magnitude=None,
                    duration=36.6,
                    triple_duration=None,
                    tier_name="CP 150",
                    solvent="Lorkhan's Tears",
                    level=50,
                ),
            ),
            buff_grants=(
                PotionBuffGrant(
                    source_trait="Increase Spell Power",
                    buff_name="Major Sorcery",
                    duration=36.6,
                    triple_duration=None,
                    tier_name="CP 150",
                ),
            ),
        )


def _observations(*times, unresolved=()):
    return ExtremeSustainedDPSPotionObservationFrontier(
        points=(),
        observation_times=tuple(float(value) for value in times),
        denominator_proven=not unresolved and bool(times),
        evidence=("test observations",),
        unresolved=tuple(unresolved),
    )


def _progression(rank=3):
    return CharacterProgression(
        passive_ranks={"Medicinal Use": rank},
    )


def test_finalized_denominator_uses_medicinal_use_adjusted_duration() -> None:
    result = ExtremeSustainedDPSFinalizedPotionTimingDenominatorService(
        event_resolver=_Resolver()
    ).build(
        player_build=PlayerBuild(Potion="Potion X"),
        progression=_progression(3),
        observation_frontier=_observations(1.0, 20.0, 50.0),
        duration_seconds=60.0,
        cooldown_seconds=45.0,
    )

    assert result.denominator_proven is True
    assert result.effective_buff_durations == (47.58,)
    assert result.breakpoint_frontier.named_buff_state_denominator_proven is True
    assert result.breakpoint_frontier.full_potion_timing_closed is False
    assert result.omitted_scope == (
        "potion instant-restoration timing is not closed by named-buff breakpoint coverage",
    )


def test_full_timing_can_close_when_restoration_timing_is_explicitly_closed() -> None:
    result = ExtremeSustainedDPSFinalizedPotionTimingDenominatorService(
        event_resolver=_Resolver()
    ).build(
        player_build=PlayerBuild(Potion="Potion X"),
        progression=_progression(3),
        observation_frontier=_observations(1.0, 20.0, 50.0),
        duration_seconds=60.0,
        cooldown_seconds=45.0,
        instant_restoration_timing_closed=True,
    )

    assert result.denominator_proven is True
    assert result.breakpoint_frontier.full_potion_timing_closed is True
    assert result.omitted_scope == ()


def test_unresolved_observation_frontier_keeps_denominator_open() -> None:
    result = ExtremeSustainedDPSFinalizedPotionTimingDenominatorService(
        event_resolver=_Resolver()
    ).build(
        player_build=PlayerBuild(Potion="Potion X"),
        progression=_progression(3),
        observation_frontier=_observations(
            1.0,
            unresolved=("periodic timing unresolved",),
        ),
        duration_seconds=60.0,
        cooldown_seconds=45.0,
    )

    assert result.denominator_proven is False
    assert "periodic timing unresolved" in result.unresolved


def test_missing_medicinal_use_rank_fails_closed() -> None:
    result = ExtremeSustainedDPSFinalizedPotionTimingDenominatorService(
        event_resolver=_Resolver()
    ).build(
        player_build=PlayerBuild(Potion="Potion X"),
        progression=CharacterProgression(),
        observation_frontier=_observations(1.0, 20.0),
        duration_seconds=60.0,
        cooldown_seconds=45.0,
    )

    assert result.denominator_proven is False
    assert any("Medicinal Use rank is unresolved" in row for row in result.unresolved)



def test_resource_observation_boundaries_close_instant_restoration_timing() -> None:
    result = ExtremeSustainedDPSFinalizedPotionTimingDenominatorService(
        event_resolver=_Resolver()
    ).build(
        player_build=PlayerBuild(Potion="Potion X"),
        progression=_progression(3),
        observation_frontier=_observations(1.0, 20.0, 50.0),
        duration_seconds=60.0,
        cooldown_seconds=45.0,
        resource_observation_times=(2.0, 4.0, 6.0, 8.0),
        resource_observation_denominator_proven=True,
    )

    assert result.denominator_proven is True
    assert result.breakpoint_frontier.full_potion_timing_closed is True
    assert result.omitted_scope == ()
    assert any(
        "resource observation timestamps: 4" in row
        for row in result.evidence
    )


def test_unproven_resource_observation_times_fail_closed() -> None:
    result = ExtremeSustainedDPSFinalizedPotionTimingDenominatorService(
        event_resolver=_Resolver()
    ).build(
        player_build=PlayerBuild(Potion="Potion X"),
        progression=_progression(3),
        observation_frontier=_observations(1.0, 20.0),
        duration_seconds=60.0,
        cooldown_seconds=45.0,
        resource_observation_times=(2.0, 4.0),
        resource_observation_denominator_proven=False,
    )

    assert result.denominator_proven is False
    assert any(
        "without denominator proof" in row
        for row in result.unresolved
    )
