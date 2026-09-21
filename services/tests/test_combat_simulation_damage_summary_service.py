from models.combat_simulation import (
    CombatSimulationCombatant,
    CombatSimulationEvent,
    CombatSimulationResult,
    CombatSimulationTargetState,
    SimulationEventPriority,
)
from services.combat_simulation_damage_summary_service import (
    CombatSimulationDamageSummaryService,
)


def _event(time, sequence, event_type, source, **payload):
    priority = {
        "outgoing_damage": int(SimulationEventPriority.DIRECT_RESULT),
        "health_change": int(SimulationEventPriority.HEALTH_CHANGE),
        "death": int(SimulationEventPriority.EXPIRATION),
    }.get(event_type, int(SimulationEventPriority.TRIGGER))
    return CombatSimulationEvent(
        time_seconds=time,
        priority=priority,
        sequence=sequence,
        event_type=event_type,
        source=source,
        payload=tuple(payload.items()),
    )


def test_damage_summary_totals_target_damage_and_sources() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(1.0, 0, "outgoing_damage", "Skill A", recipient="Boss", amount=3000.0),
            _event(
                1.0,
                1,
                "health_change",
                "Skill A",
                recipient="Boss",
                before=10000,
                applied_damage=3000.0,
                overkill=0.0,
                after=7000,
                origin_event_type="outgoing_damage",
            ),
            _event(2.0, 0, "outgoing_damage", "Skill A", recipient="Boss", amount=2000.0),
            _event(
                2.0,
                1,
                "health_change",
                "Skill A",
                recipient="Boss",
                before=7000,
                applied_damage=2000.0,
                overkill=0.0,
                after=5000,
                origin_event_type="outgoing_damage",
            ),
            _event(3.0, 0, "outgoing_damage", "Skill B", recipient="Boss", amount=1000.0),
            _event(
                3.0,
                1,
                "health_change",
                "Skill B",
                recipient="Boss",
                before=5000,
                applied_damage=1000.0,
                overkill=0.0,
                after=4000,
                origin_event_type="outgoing_damage",
            ),
        ),
        unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.outgoing_event_count == 3
    assert summary.attempted_damage == 6000.0
    assert summary.applied_damage == 6000.0
    assert summary.ending_target_health == 4000
    assert summary.target_dead is False
    assert summary.modeled_dps == 1200.0
    assert [
        (
            row.source,
            row.event_count,
            row.attempted_damage,
            row.applied_damage,
            row.overkill,
            row.killing_blow,
        )
        for row in summary.damage_by_source
    ] == [
        ("Skill A", 2, 5000.0, 5000.0, 0.0, False),
        ("Skill B", 1, 1000.0, 1000.0, 0.0, False),
    ]
    assert summary.total_overkill == 0.0
    assert summary.killing_source is None


def test_damage_summary_withholds_dps_when_damage_evidence_is_unresolved() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(),
        unresolved=("DoT runtime anchor unavailable",),
        damage_unresolved=("DoT runtime anchor unavailable",),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.complete_damage_evidence is False
    assert summary.modeled_dps is None
    assert summary.unresolved == ("DoT runtime anchor unavailable",)



def test_damage_summary_attributes_lethal_overkill_to_killing_source() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=3000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=2.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Execute",
                recipient="Boss",
                amount=8000.0,
            ),
            _event(
                1.0,
                0,
                "health_change",
                "Execute",
                recipient="Boss",
                before=3000,
                attempted_damage=8000.0,
                applied_damage=3000.0,
                overkill=5000.0,
                after=0,
                origin_event_type="outgoing_damage",
            ),
            _event(
                1.0,
                0,
                "death",
                "Execute",
                recipient="Boss",
                overkill=5000.0,
                origin_event_type="outgoing_damage",
            ),
        ),
        unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 8000.0
    assert summary.applied_damage == 3000.0
    assert summary.total_overkill == 5000.0
    assert summary.target_dead is True
    assert summary.death_time_seconds == 1.0
    assert summary.killing_source == "Execute"
    assert summary.killing_origin_event_type == "outgoing_damage"
    assert summary.modeled_dps == 1500.0
    assert len(summary.damage_by_source) == 1
    row = summary.damage_by_source[0]
    assert row.source == "Execute"
    assert row.attempted_damage == 8000.0
    assert row.applied_damage == 3000.0
    assert row.overkill == 5000.0
    assert row.killing_blow is True


def test_damage_summary_ignores_non_outgoing_health_damage_for_dd_totals() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "health_change",
                "Environmental Hazard",
                recipient="Boss",
                before=10000,
                attempted_damage=2000.0,
                applied_damage=2000.0,
                overkill=0.0,
                after=8000,
                origin_event_type="incoming_damage",
            ),
        ),
        unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 0.0
    assert summary.applied_damage == 0.0
    assert summary.damage_by_source == ()
    assert summary.killing_source is None



def test_damage_summary_allows_dps_when_only_non_damage_unresolved_remains() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Skill A",
                recipient="Boss",
                amount=3000.0,
            ),
            _event(
                1.0,
                0,
                "health_change",
                "Skill A",
                recipient="Boss",
                before=10000,
                applied_damage=3000.0,
                overkill=0.0,
                after=7000,
                origin_event_type="outgoing_damage",
            ),
        ),
        unresolved=(
            "1s Skill A: damage consequence is wired; remaining unsupported non-damage skill consequences are unresolved",
        ),
        damage_unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.complete_damage_evidence is True
    assert summary.modeled_dps == 600.0
    assert summary.damage_unresolved == ()
    assert summary.unresolved


def test_damage_summary_counts_raw_components_but_applies_one_health_transition() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Mixed Skill",
                recipient="Boss",
                amount=2000.0,
                damage_type="magic",
            ),
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Mixed Skill",
                recipient="Boss",
                amount=3000.0,
                damage_type="flame",
            ),
            _event(
                1.0,
                0,
                "health_change",
                "Mixed Skill",
                recipient="Boss",
                before=10000,
                attempted_damage=5000.0,
                applied_damage=5000.0,
                overkill=0.0,
                after=5000,
                origin_event_type="outgoing_damage",
            ),
        ),
        unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.outgoing_event_count == 2
    assert summary.attempted_damage == 5000.0
    assert summary.applied_damage == 5000.0
    assert summary.total_overkill == 0.0
    assert len(summary.damage_by_source) == 1
    row = summary.damage_by_source[0]
    assert row.source == "Mixed Skill"
    assert row.event_count == 2
    assert row.attempted_damage == 5000.0
    assert row.applied_damage == 5000.0
    assert row.overkill == 0.0


def test_damage_summary_keeps_proven_partial_totals_but_withholds_dps() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Proven Hit",
                recipient="Boss",
                amount=3000.0,
            ),
            _event(
                1.0,
                0,
                "health_change",
                "Proven Hit",
                recipient="Boss",
                before=10000,
                attempted_damage=3000.0,
                applied_damage=3000.0,
                overkill=0.0,
                after=7000,
                origin_event_type="outgoing_damage",
            ),
        ),
        unresolved=("Later DoT tick ordering unresolved",),
        damage_unresolved=("Later DoT tick ordering unresolved",),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 3000.0
    assert summary.applied_damage == 3000.0
    assert summary.ending_target_health == 7000
    assert summary.complete_damage_evidence is False
    assert summary.modeled_dps is None


def test_environmental_death_is_not_attributed_as_dd_killing_blow() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=5000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Player Hit",
                recipient="Boss",
                amount=2000.0,
            ),
            _event(
                1.0,
                0,
                "health_change",
                "Player Hit",
                recipient="Boss",
                before=5000,
                attempted_damage=2000.0,
                applied_damage=2000.0,
                overkill=0.0,
                after=3000,
                origin_event_type="outgoing_damage",
            ),
            _event(
                2.0,
                0,
                "health_change",
                "Environmental Hazard",
                recipient="Boss",
                before=3000,
                attempted_damage=5000.0,
                applied_damage=3000.0,
                overkill=2000.0,
                after=0,
                origin_event_type="incoming_damage",
            ),
            _event(
                2.0,
                0,
                "death",
                "Environmental Hazard",
                recipient="Boss",
                overkill=2000.0,
                origin_event_type="incoming_damage",
            ),
        ),
        unresolved=(),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.target_dead is True
    assert summary.killing_source is None
    assert summary.death_time_seconds is None
    assert summary.applied_damage == 2000.0
    assert summary.damage_by_source[0].source == "Player Hit"
    assert summary.damage_by_source[0].killing_blow is False


def test_damage_summary_rejects_target_missing_from_target_state() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(),
        target_state=state,
    )

    try:
        CombatSimulationDamageSummaryService().summarize(
            result,
            target_identity="Not The Boss",
        )
    except ValueError as exc:
        assert "not present in target state" in str(exc)
    else:
        raise AssertionError("Expected mismatched summary target to fail closed")


def test_damage_summary_withholds_dps_without_target_health_state() -> None:
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Resolved Hit",
                recipient="Boss",
                amount=2500.0,
            ),
        ),
        unresolved=(),
        damage_unresolved=(),
        target_state=None,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 2500.0
    assert summary.applied_damage == 0.0
    assert summary.complete_damage_evidence is False
    assert summary.modeled_dps is None
    assert any(
        "target Health state is required to prove applied outgoing damage" in message
        for message in summary.damage_unresolved
    )


def test_damage_summary_fails_closed_on_invalid_raw_outgoing_amount() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )

    for amount in ("banana", float("nan"), float("inf"), float("-inf")):
        result = CombatSimulationResult(
            duration_seconds=5.0,
            initial_bar="front",
            final_bar="front",
            events=(
                _event(
                    1.0,
                    0,
                    "outgoing_damage",
                    "Invalid Hit",
                    recipient="Boss",
                    amount=amount,
                ),
            ),
            target_state=state,
        )

        summary = CombatSimulationDamageSummaryService().summarize(
            result,
            target_identity="Boss",
        )

        assert summary.outgoing_event_count == 1
        assert summary.attempted_damage == 0.0
        assert summary.applied_damage == 0.0
        assert summary.complete_damage_evidence is False
        assert summary.modeled_dps is None
        assert any(
            "damage amount must be finite and non-negative" in message
            for message in summary.damage_unresolved
        )


def test_damage_summary_fails_closed_when_outgoing_health_evidence_is_incomplete() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Incomplete Hit",
                recipient="Boss",
                amount=3000.0,
            ),
            _event(
                1.0,
                0,
                "health_change",
                "Incomplete Hit",
                recipient="Boss",
                before=10000,
                after=7000,
                origin_event_type="outgoing_damage",
            ),
        ),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 3000.0
    assert summary.applied_damage == 0.0
    assert summary.complete_damage_evidence is False
    assert summary.modeled_dps is None
    assert any(
        "applied outgoing damage is unavailable or invalid" in message
        for message in summary.damage_unresolved
    )
    assert any(
        "outgoing damage overkill is unavailable or invalid" in message
        for message in summary.damage_unresolved
    )


def test_damage_summary_withholds_dps_when_raw_outgoing_has_no_health_transition() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "outgoing_damage",
                "Unapplied Hit",
                recipient="Boss",
                amount=3000.0,
            ),
        ),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 3000.0
    assert summary.applied_damage == 0.0
    assert summary.complete_damage_evidence is False
    assert summary.modeled_dps is None
    assert any(
        "matching Health transition is unavailable" in message
        for message in summary.damage_unresolved
    )


def test_damage_summary_withholds_dps_when_outgoing_health_has_no_raw_damage_event() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=5.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                1.0,
                0,
                "health_change",
                "Orphan Applied Hit",
                recipient="Boss",
                before=10000,
                applied_damage=3000.0,
                overkill=0.0,
                after=7000,
                origin_event_type="outgoing_damage",
            ),
        ),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.attempted_damage == 0.0
    assert summary.applied_damage == 3000.0
    assert summary.complete_damage_evidence is False
    assert summary.modeled_dps is None
    assert any(
        "matching raw outgoing damage is unavailable" in message
        for message in summary.damage_unresolved
    )


def test_damage_summary_withholds_dps_for_zero_duration_even_with_proven_damage() -> None:
    state = CombatSimulationTargetState(
        combatants=(
            CombatSimulationCombatant(
                "Boss",
                "enemy",
                current_health=10000,
                maximum_health=10000,
            ),
        )
    )
    result = CombatSimulationResult(
        duration_seconds=0.0,
        initial_bar="front",
        final_bar="front",
        events=(
            _event(
                0.0,
                0,
                "outgoing_damage",
                "Instant Hit",
                recipient="Boss",
                amount=3000.0,
            ),
            _event(
                0.0,
                0,
                "health_change",
                "Instant Hit",
                recipient="Boss",
                before=10000,
                applied_damage=3000.0,
                overkill=0.0,
                after=7000,
                origin_event_type="outgoing_damage",
            ),
        ),
        target_state=state,
    )

    summary = CombatSimulationDamageSummaryService().summarize(
        result,
        target_identity="Boss",
    )

    assert summary.complete_damage_evidence is True
    assert summary.applied_damage == 3000.0
    assert summary.modeled_dps is None
