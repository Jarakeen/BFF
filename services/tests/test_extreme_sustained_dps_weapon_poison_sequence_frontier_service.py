import pytest

from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_sustained_dps_weapon_poison_sequence_frontier_service import (
    ExtremeSustainedDPSWeaponPoisonProcOccurrence,
    ExtremeSustainedDPSWeaponPoisonSequenceChoice,
    ExtremeSustainedDPSWeaponPoisonSequenceFrontier,
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


def test_poison_sequence_choice_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        ExtremeSustainedDPSWeaponPoisonSequenceChoice(
            choice_id="choice",
            procs=(),
            chance_misses=(),
            cooldown_blocked=(),
            last_proc_time_seconds=None,
            branch_probability=1.1,
        )


def test_poison_proc_occurrence_requires_poison_identity() -> None:
    with pytest.raises(ValueError, match="requires poison_id"):
        ExtremeSustainedDPSWeaponPoisonProcOccurrence(
            event=_event(1.0, 0),
            poison_id="   ",
        )


def test_poison_sequence_frontier_rejects_candidate_count_drift() -> None:
    choice = ExtremeSustainedDPSWeaponPoisonSequenceChoice(
        choice_id="choice",
        procs=(),
        chance_misses=(),
        cooldown_blocked=(),
        last_proc_time_seconds=None,
        branch_probability=1.0,
    )

    with pytest.raises(ValueError, match="candidate_count must equal choice count"):
        ExtremeSustainedDPSWeaponPoisonSequenceFrontier(
            choices=(choice,),
            candidate_count=2,
            denominator_proven=True,
            evidence=(),
            unresolved=(),
        )


def test_poison_sequence_builder_requires_strict_event_denominator_flag() -> None:
    with pytest.raises(TypeError, match="event_denominator_proven must be boolean"):
        ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
            events=(_event(1.0, 0),),
            player_build=PlayerBuild(FrontBarPoison="Poison"),
            event_denominator_proven="false",
            source="malformed",
        )


def test_poison_sequence_builder_requires_canonical_events_and_build() -> None:
    with pytest.raises(TypeError, match="events must contain RuntimeEvent"):
        ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
            events=(object(),),
            player_build=PlayerBuild(FrontBarPoison="Poison"),
            event_denominator_proven=True,
            source="malformed",
        )

    with pytest.raises(TypeError, match="requires PlayerBuild"):
        ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
            events=(),
            player_build=object(),
            event_denominator_proven=True,
            source="malformed",
        )


def test_poison_sequence_builder_requires_tuple_events_and_string_source() -> None:
    with pytest.raises(TypeError, match="events must be a tuple"):
        ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
            events=[_event(1.0, 0)],  # type: ignore[arg-type]
            player_build=PlayerBuild(FrontBarPoison="Poison"),
            event_denominator_proven=True,
            source="strict",
        )

    with pytest.raises(TypeError, match="sequence source must be a string"):
        ExtremeSustainedDPSWeaponPoisonSequenceFrontierService().build(
            events=(_event(1.0, 0),),
            player_build=PlayerBuild(FrontBarPoison="Poison"),
            event_denominator_proven=True,
            source=7,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "field,value,match",
    (
        ("choice_id", 7, "choice_id must be a string"),
        ("procs", [], "procs must be a tuple"),
        ("chance_misses", [], "chance_misses must be a tuple"),
        ("cooldown_blocked", [], "cooldown_blocked must be a tuple"),
        ("last_proc_time_seconds", "1", "last proc time must be numeric"),
        ("branch_probability", "0.5", "branch probability must be numeric"),
    ),
)
def test_poison_sequence_choice_rejects_coerced_fields(field, value, match) -> None:
    kwargs = {
        "choice_id": "choice",
        "procs": (),
        "chance_misses": (),
        "cooldown_blocked": (),
        "last_proc_time_seconds": None,
        "branch_probability": 1.0,
    }
    kwargs[field] = value

    with pytest.raises(TypeError, match=match):
        ExtremeSustainedDPSWeaponPoisonSequenceChoice(**kwargs)


def test_poison_proc_occurrence_requires_string_poison_id() -> None:
    with pytest.raises(TypeError, match="poison_id must be a string"):
        ExtremeSustainedDPSWeaponPoisonProcOccurrence(
            event=_event(1.0, 0),
            poison_id=7,  # type: ignore[arg-type]
        )


def test_poison_sequence_frontier_requires_tuple_choices() -> None:
    with pytest.raises(TypeError, match="choices must be a tuple"):
        ExtremeSustainedDPSWeaponPoisonSequenceFrontier(
            choices=[],  # type: ignore[arg-type]
            candidate_count=0,
            denominator_proven=False,
            evidence=(),
            unresolved=("open",),
        )
