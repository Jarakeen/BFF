from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport,
    RotationDDPeriodicEsoLogsMagnitudeTransition,
    RotationDDPeriodicEsoLogsStateEventEvidence,
)
from services.rotation_scalding_rune_magnitude_multistate_signature_service import (
    RotationScaldingRuneMagnitudeMultistateSignatureService,
)


def _event(*, target_id: int, ability_id: int, name: str, event_type: str):
    return RotationDDPeriodicEsoLogsStateEventEvidence(
        timestamp_ms=0.0,
        event_index=1,
        event_type=event_type,
        source_id=1,
        target_id=target_id,
        ability_game_id=ability_id,
        ability_name=name,
    )


def _transition(*, before: float, after: float, events):
    return RotationDDPeriodicEsoLogsMagnitudeTransition(
        report_code="R",
        fight_id=1,
        source_id=10,
        target_id=20,
        cast_track_id=30,
        hit_type=1,
        from_timestamp_ms=1000.0,
        to_timestamp_ms=3000.0,
        from_amount=before,
        to_amount=after,
        state_events=tuple(events),
    )


def _report(*transitions):
    return RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport(
        skill_entity_id="scalding_rune",
        periodic_ability_id=40468,
        transitions=tuple(transitions),
    )


def test_groups_repeated_exact_multistate_signature_and_preserves_actor_scope() -> None:
    events = (
        _event(target_id=10, ability_id=100, name="Source Buff", event_type="state_gained"),
        _event(target_id=20, ability_id=200, name="Target Debuff", event_type="state_gained"),
    )
    result = RotationScaldingRuneMagnitudeMultistateSignatureService().analyze(
        _report(
            _transition(before=100, after=120, events=events),
            _transition(before=200, after=240, events=events),
        )
    )

    assert result.multistate_transition_count == 2
    assert len(result.signatures) == 1
    summary = result.signatures[0]
    assert summary.sample_count == 2
    assert summary.direction_consistent is True
    assert summary.amount_increased == 2
    assert summary.median_ratio == 1.2
    assert [(factor.actor_scope, factor.ability_game_id) for factor in summary.factors] == [
        ("source", 100),
        ("target", 200),
    ]


def test_single_state_transitions_are_excluded() -> None:
    result = RotationScaldingRuneMagnitudeMultistateSignatureService().analyze(
        _report(
            _transition(
                before=100,
                after=110,
                events=(_event(target_id=10, ability_id=100, name="Buff", event_type="state_gained"),),
            )
        )
    )
    assert result.multistate_transition_count == 0
    assert result.signatures == ()
    assert result.unresolved


def test_reversible_signature_pair_is_counted_once() -> None:
    gained = (
        _event(target_id=10, ability_id=100, name="Buff", event_type="state_gained"),
        _event(target_id=20, ability_id=200, name="Debuff", event_type="state_gained"),
    )
    lost = (
        _event(target_id=10, ability_id=100, name="Buff", event_type="state_lost"),
        _event(target_id=20, ability_id=200, name="Debuff", event_type="state_lost"),
    )
    result = RotationScaldingRuneMagnitudeMultistateSignatureService().analyze(
        _report(
            _transition(before=100, after=120, events=gained),
            _transition(before=200, after=240, events=gained),
            _transition(before=120, after=100, events=lost),
            _transition(before=240, after=200, events=lost),
        )
    )
    assert len(result.signatures) == 2
    assert result.reversible_signature_pairs == 1


def test_minimum_samples_filters_one_off_signatures() -> None:
    events = (
        _event(target_id=10, ability_id=100, name="Buff", event_type="state_gained"),
        _event(target_id=20, ability_id=200, name="Debuff", event_type="state_gained"),
    )
    result = RotationScaldingRuneMagnitudeMultistateSignatureService().analyze(
        _report(_transition(before=100, after=120, events=events)),
        minimum_samples=2,
    )
    assert result.multistate_transition_count == 1
    assert result.signatures == ()
    assert any("minimum sample count 2" in item for item in result.unresolved)
