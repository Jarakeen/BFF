from __future__ import annotations

from minmax.effect_kinds import EffectKind
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_gear_search_state_rule_service import ExtremeGearSearchStateRule
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_max_health_special_named_gear_branch_service import (
    ExtremeMaxHealthSpecialBranchKind,
    ExtremeMaxHealthSpecialNamedGearBranchService,
)


def _evidence(
    *,
    set_id: int,
    name: str,
    piece_count: int,
    effect: Effect | None = None,
    effects: tuple[Effect, ...] | None = None,
    search_state_rule: ExtremeGearSearchStateRule | None = None,
) -> ExtremeGearSetObjectiveBreakpointEvidence:
    source_effects = tuple(effects) if effects is not None else (() if effect is None else (effect,))
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=name,
        category="Test",
        equipped_piece_count=piece_count,
        objective_key="max_health",
        reviewed_delta=0.0,
        source_effects=source_effects,
        unresolved=("special runtime/search-state review",),
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=name,
        piece_count=piece_count,
        objective_key="max_health",
        status=ExtremeGearSetObjectiveRelevance.RELEVANT,
        reviewed_delta=0.0,
        candidate=candidate,
        search_state_rule=search_state_rule,
    )


def _effect(
    *,
    value: float,
    condition: str = "",
    operation: EffectOperation = EffectOperation.ADD,
    unit: EffectUnit = EffectUnit.FLAT,
) -> Effect:
    return Effect(
        operation=operation,
        value=value,
        source="synthetic",
        stat=StatId.MAX_HEALTH,
        kind=EffectKind.STAT,
        unit=unit,
        condition=(condition or None),
    )


def test_classifies_conditional_flat_percent_and_search_state_branches() -> None:
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=(
            _evidence(
                set_id=596,
                name="Death Dealer's Fete",
                piece_count=1,
                effect=_effect(value=2640.0, condition="escalating_fete_stacks:30"),
            ),
            _evidence(
                set_id=287,
                name="Green Pact",
                piece_count=5,
                effect=_effect(value=2500.0, condition="food_buff_active"),
            ),
            _evidence(
                set_id=178,
                name="Armor Master",
                piece_count=5,
                effect=_effect(
                    value=5.0,
                    condition="armor_ability_slotted",
                    operation=EffectOperation.ADD_PERCENT,
                    unit=EffectUnit.PERCENT,
                ),
            ),
            _evidence(
                set_id=161,
                name="Twice-Born Star",
                piece_count=5,
                search_state_rule=ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS,
            ),
        ),
    )
    requested = (
        (596, "Death Dealer's Fete", 1),
        (287, "Green Pact", 5),
        (178, "Armor Master", 5),
        (161, "Twice-Born Star", 5),
    )

    result = ExtremeMaxHealthSpecialNamedGearBranchService(relevance).build(requested)

    assert result.denominator_classified is True
    assert not result.unresolved
    by_name = {row.set_name: row for row in result.branches}
    assert by_name["Death Dealer's Fete"].kind is ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_FLAT
    assert by_name["Death Dealer's Fete"].condition == "escalating_fete_stacks:30"
    assert by_name["Green Pact"].kind is ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_FLAT
    assert by_name["Green Pact"].condition == "food_buff_active"
    assert by_name["Armor Master"].kind is ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_PERCENT
    assert by_name["Armor Master"].unit is EffectUnit.PERCENT
    assert by_name["Twice-Born Star"].kind is ExtremeMaxHealthSpecialBranchKind.SEARCH_STATE_MUTATION
    assert (
        by_name["Twice-Born Star"].search_state_rule
        is ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS
    )


def test_cumulative_breakpoint_bundle_keeps_baseline_and_runtime_obligation() -> None:
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=(
            _evidence(
                set_id=287,
                name="Green Pact",
                piece_count=5,
                effects=(
                    _effect(value=1206.0),
                    _effect(value=1206.0),
                    _effect(value=2500.0, condition="food_buff_active"),
                ),
            ),
            _evidence(
                set_id=178,
                name="Armor Master",
                piece_count=5,
                effects=(
                    _effect(value=1206.0),
                    _effect(
                        value=5.0,
                        condition="armor_ability_slotted",
                        operation=EffectOperation.ADD_PERCENT,
                        unit=EffectUnit.PERCENT,
                    ),
                ),
            ),
        ),
    )

    result = ExtremeMaxHealthSpecialNamedGearBranchService(relevance).build(
        ((287, "Green Pact", 5), (178, "Armor Master", 5))
    )

    assert result.denominator_classified is True
    assert not result.unresolved
    by_name = {row.set_name: row for row in result.branches}
    assert by_name["Green Pact"].kind is ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_BUNDLE
    assert len(by_name["Green Pact"].target_effects) == 3
    assert by_name["Green Pact"].required_conditions == ("food_buff_active",)
    assert by_name["Armor Master"].kind is ExtremeMaxHealthSpecialBranchKind.CONDITIONAL_BUNDLE
    assert len(by_name["Armor Master"].target_effects) == 2
    assert by_name["Armor Master"].required_conditions == ("armor_ability_slotted",)


def test_missing_requested_pair_keeps_denominator_open() -> None:
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=(),
    )

    result = ExtremeMaxHealthSpecialNamedGearBranchService(relevance).build(
        ((999, "Unknown Set", 5),)
    )

    assert result.denominator_classified is False
    assert not result.branches
    assert result.unresolved == (
        "Unknown Set (5) has no canonical Max Health relevance evidence",
    )


def test_unconditioned_non_search_state_effect_fails_closed() -> None:
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=(
            _evidence(
                set_id=1,
                name="Odd Set",
                piece_count=5,
                effect=Effect(
                    operation=EffectOperation.ADD,
                    value=1000.0,
                    source="synthetic",
                    stat=StatId.MAX_HEALTH,
                    kind=EffectKind.STAT,
                    unit=EffectUnit.FLAT,
                ),
            ),
        ),
    )

    result = ExtremeMaxHealthSpecialNamedGearBranchService(relevance).build(
        ((1, "Odd Set", 5),)
    )

    assert result.denominator_classified is False
    assert "contains no conditional or percentage effect" in result.unresolved[0]


def test_wrong_objective_is_rejected() -> None:
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_magicka",
        evidence=(),
    )

    try:
        ExtremeMaxHealthSpecialNamedGearBranchService(relevance)
    except ValueError as exc:
        assert "max_health only" in str(exc)
    else:
        raise AssertionError("expected max_health-only guard")
