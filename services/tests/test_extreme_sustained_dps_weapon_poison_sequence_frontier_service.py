import pytest

from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonSequenceFrontierService,
)


def _event(time_seconds, sequence, bar="front"):
    return RuntimeEvent(
        time_seconds=time_seconds,
        sequence=sequence,
        trigger="weapon_poison_activation",
        source="Weapon Hit",
        target="Boss",
        source_bar=bar,
    )


def test_one_ready_poison_opportunity_branches_proc_and_miss() -> None:
    result = ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
        events=(_event(1.0, 0),),
        player_build=PlayerBuild(FrontBarPoison="Damage Health Poison IX"),
        event_denominator_proven=True,
        source="reviewed poison sequence",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 2
    assert sorted(choice.branch_probability for choice in result.choices) == pytest.approx(
        [0.2, 0.8]
    )
    assert sorted(len(choice.procs) for choice in result.choices) == [0, 1]


def test_successful_proc_blocks_both_bars_on_global_cooldown() -> None:
    result = ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
        events=(
            _event(1.0, 0, "front"),
            _event(2.0, 1, "back"),
        ),
        player_build=PlayerBuild(
            FrontBarPoison="Front Poison",
            BackBarPoison="Back Poison",
        ),
        event_denominator_proven=True,
        source="reviewed poison sequence",
    )

    assert result.denominator_proven is True
    assert result.candidate_count == 3

    proc_first = [
        choice
        for choice in result.choices
        if choice.procs and choice.procs[0].event.time_seconds == 1.0
    ]
    assert len(proc_first) == 1
    assert len(proc_first[0].procs) == 1
    assert [row.time_seconds for row in proc_first[0].cooldown_blocked] == [2.0]
    assert proc_first[0].branch_probability == pytest.approx(0.2)


def test_missed_proc_does_not_start_global_cooldown() -> None:
    result = ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
        events=(_event(1.0, 0), _event(2.0, 1)),
        player_build=PlayerBuild(FrontBarPoison="Poison"),
        event_denominator_proven=True,
        source="reviewed poison sequence",
    )

    miss_then_proc = [
        choice
        for choice in result.choices
        if len(choice.chance_misses) == 1
        and choice.chance_misses[0].time_seconds == 1.0
        and len(choice.procs) == 1
        and choice.procs[0].event.time_seconds == 2.0
    ]
    assert len(miss_then_proc) == 1
    assert miss_then_proc[0].branch_probability == pytest.approx(0.8 * 0.2)


def test_poison_can_proc_again_when_global_cooldown_expires() -> None:
    result = ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
        events=(_event(1.0, 0), _event(11.0, 1)),
        player_build=PlayerBuild(FrontBarPoison="Poison"),
        event_denominator_proven=True,
        source="reviewed poison sequence",
    )

    double_proc = [
        choice for choice in result.choices if len(choice.procs) == 2
    ]
    assert len(double_proc) == 1
    assert double_proc[0].branch_probability == pytest.approx(0.2 * 0.2)


def test_event_without_poison_source_bar_fails_closed() -> None:
    result = ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
        events=(_event(1.0, 0, "back"),),
        player_build=PlayerBuild(FrontBarPoison="Poison"),
        event_denominator_proven=True,
        source="bad poison sequence",
    )

    assert result.denominator_proven is False
    assert any("has no equipped poison" in row for row in result.unresolved)
