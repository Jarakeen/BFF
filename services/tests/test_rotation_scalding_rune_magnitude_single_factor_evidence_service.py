from services.rotation_dd_periodic_esologs_magnitude_state_transition_service import (
    RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport,
    RotationDDPeriodicEsoLogsMagnitudeTransition,
    RotationDDPeriodicEsoLogsStateEventEvidence,
)
from services.rotation_scalding_rune_magnitude_single_factor_evidence_service import (
    RotationScaldingRuneMagnitudeSingleFactorEvidenceService,
)


def _state(*, ability_id=61744, name="Major Sorcery", kind="state_gained", target_id=1):
    return RotationDDPeriodicEsoLogsStateEventEvidence(
        timestamp_ms=1500.0,
        event_index=10,
        event_type=kind,
        source_id=1,
        target_id=target_id,
        ability_game_id=ability_id,
        ability_name=name,
    )


def _transition(
    *,
    from_amount,
    to_amount,
    states,
    source_id=1,
    target_id=9,
    track=77,
):
    return RotationDDPeriodicEsoLogsMagnitudeTransition(
        report_code="R",
        fight_id=1,
        source_id=source_id,
        target_id=target_id,
        cast_track_id=track,
        hit_type=1,
        from_timestamp_ms=1000.0,
        to_timestamp_ms=3000.0,
        from_amount=float(from_amount),
        to_amount=float(to_amount),
        state_events=tuple(states),
    )


def _report(transitions, *, state_same_amount_changed=0):
    return RotationDDPeriodicEsoLogsMagnitudeStateTransitionReport(
        skill_entity_id="scalding_rune",
        periodic_ability_id=40468,
        transitions=tuple(transitions),
        comparable_occurrence_pairs=12,
        state_changed_amount_changed=len(transitions),
        state_same_amount_changed=state_same_amount_changed,
    )


def test_groups_repeated_single_factor_transitions_and_reports_ratio_direction() -> None:
    base = _report(
        (
            _transition(from_amount=100, to_amount=120, states=(_state(),)),
            _transition(from_amount=200, to_amount=240, states=(_state(),)),
        )
    )

    report = RotationScaldingRuneMagnitudeSingleFactorEvidenceService.from_transition_report(base)

    assert report.single_factor_amount_change_transitions == 2
    assert report.multi_factor_amount_change_transitions == 0
    assert len(report.summaries) == 1
    summary = report.summaries[0]
    assert summary.ability_game_id == 61744
    assert summary.ability_name == "Major Sorcery"
    assert summary.affected_actor == "source"
    assert summary.state_event_type == "state_gained"
    assert summary.sample_count == 2
    assert summary.amount_increase_count == 2
    assert summary.amount_decrease_count == 0
    assert summary.directionally_consistent is True
    assert summary.median_amount_ratio == 1.2
    assert summary.minimum_amount_ratio == 1.2
    assert summary.maximum_amount_ratio == 1.2


def test_separates_gain_loss_and_source_target_factors() -> None:
    base = _report(
        (
            _transition(
                from_amount=120,
                to_amount=100,
                states=(_state(kind="state_lost", target_id=1),),
            ),
            _transition(
                from_amount=100,
                to_amount=110,
                states=(_state(ability_id=145975, name="Vulnerability", target_id=9),),
            ),
        )
    )

    report = RotationScaldingRuneMagnitudeSingleFactorEvidenceService.from_transition_report(base)

    assert len(report.summaries) == 2
    by_name = {item.ability_name: item for item in report.summaries}
    assert by_name["Major Sorcery"].affected_actor == "source"
    assert by_name["Major Sorcery"].state_event_type == "state_lost"
    assert by_name["Major Sorcery"].amount_decrease_count == 1
    assert by_name["Vulnerability"].affected_actor == "damage_target"
    assert by_name["Vulnerability"].amount_increase_count == 1


def test_multi_factor_and_state_same_changes_remain_explicitly_unresolved() -> None:
    base = _report(
        (
            _transition(
                from_amount=100,
                to_amount=130,
                states=(
                    _state(),
                    _state(ability_id=145975, name="Vulnerability", target_id=9),
                ),
            ),
        ),
        state_same_amount_changed=3,
    )

    report = RotationScaldingRuneMagnitudeSingleFactorEvidenceService.from_transition_report(base)

    assert report.single_factor_amount_change_transitions == 0
    assert report.multi_factor_amount_change_transitions == 1
    assert report.summaries == ()
    assert any("no usable one-state" in item for item in report.unresolved)
    assert any("not a complete magnitude model" in item for item in report.unresolved)


def test_non_positive_or_non_finite_ratios_are_not_promoted_as_factor_evidence() -> None:
    base = _report(
        (
            _transition(from_amount=0, to_amount=100, states=(_state(),)),
            _transition(from_amount=100, to_amount=0, states=(_state(),)),
        )
    )

    report = RotationScaldingRuneMagnitudeSingleFactorEvidenceService.from_transition_report(base)

    assert report.single_factor_amount_change_transitions == 0
    assert report.summaries == ()
