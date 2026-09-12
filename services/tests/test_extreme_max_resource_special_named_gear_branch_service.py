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
from services.extreme_max_resource_special_named_gear_branch_service import (
    ExtremeMaxResourceSpecialBranchKind,
    ExtremeMaxResourceSpecialNamedGearBranchService,
)


def _effect(
    stat: StatId,
    value: float,
    *,
    condition: str = "",
    operation: EffectOperation = EffectOperation.ADD,
    unit: EffectUnit = EffectUnit.FLAT,
) -> Effect:
    return Effect(
        operation=operation,
        value=value,
        source="synthetic",
        stat=stat,
        kind=EffectKind.STAT,
        unit=unit,
        condition=(condition or None),
    )


def _evidence(
    objective: str,
    *,
    set_id: int,
    name: str,
    piece_count: int,
    effects: tuple[Effect, ...] = (),
    search_state_rule: ExtremeGearSearchStateRule | None = None,
) -> ExtremeGearSetObjectiveBreakpointEvidence:
    candidate = ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=name,
        category="Test",
        equipped_piece_count=piece_count,
        objective_key=objective,
        reviewed_delta=0.0,
        source_effects=effects,
        unresolved=("special runtime/search-state review",),
    )
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=name,
        piece_count=piece_count,
        objective_key=objective,
        status=ExtremeGearSetObjectiveRelevance.RELEVANT,
        reviewed_delta=0.0,
        candidate=candidate,
        search_state_rule=search_state_rule,
    )


def test_magicka_specials_classify_from_canonical_effect_conditions() -> None:
    objective = "max_magicka"
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key=objective,
        evidence=(
            _evidence(
                objective,
                set_id=596,
                name="Death Dealer's Fete",
                piece_count=1,
                effects=(
                    _effect(StatId.MAX_MAGICKA, 2640.0, condition="escalating_fete_stacks:30"),
                ),
            ),
            _evidence(
                objective,
                set_id=597,
                name="Shapeshifter's Chain",
                piece_count=1,
                effects=(
                    _effect(StatId.MAX_MAGICKA, 1707.0, condition="transformed"),
                ),
            ),
            _evidence(
                objective,
                set_id=854,
                name="Prowler's Talisman",
                piece_count=1,
                effects=(
                    _effect(
                        StatId.MAX_MAGICKA,
                        1900.0,
                        condition="prowlers_talisman_critical_stacks:10",
                    ),
                ),
            ),
            _evidence(
                objective,
                set_id=98,
                name="Necropotence",
                piece_count=5,
                effects=(
                    _effect(StatId.MAX_MAGICKA, 1096.0),
                    _effect(StatId.MAX_MAGICKA, 3132.0, condition="pet_active"),
                ),
            ),
            _evidence(
                objective,
                set_id=405,
                name="Bright-Throat's Boast",
                piece_count=5,
                effects=(
                    _effect(StatId.MAX_MAGICKA, 1096.0),
                    _effect(StatId.MAX_MAGICKA, 2000.0, condition="drink_buff_active"),
                ),
            ),
            _evidence(
                objective,
                set_id=161,
                name="Twice-Born Star",
                piece_count=5,
                search_state_rule=ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS,
            ),
        ),
    )
    requested = tuple(
        (row.set_id, row.set_name, row.piece_count)
        for row in relevance.evidence
    )

    result = ExtremeMaxResourceSpecialNamedGearBranchService(relevance).build(requested)

    assert result.denominator_classified is True
    assert not result.unresolved
    by_name = {row.set_name: row for row in result.branches}
    assert by_name["Death Dealer's Fete"].condition == "escalating_fete_stacks:30"
    assert by_name["Shapeshifter's Chain"].condition == "transformed"
    assert by_name["Prowler's Talisman"].condition == "prowlers_talisman_critical_stacks:10"
    assert by_name["Necropotence"].kind is ExtremeMaxResourceSpecialBranchKind.CONDITIONAL_BUNDLE
    assert by_name["Necropotence"].required_conditions == ("pet_active",)
    assert by_name["Bright-Throat's Boast"].kind is ExtremeMaxResourceSpecialBranchKind.CONDITIONAL_BUNDLE
    assert by_name["Bright-Throat's Boast"].required_conditions == ("drink_buff_active",)
    assert by_name["Twice-Born Star"].kind is ExtremeMaxResourceSpecialBranchKind.SEARCH_STATE_MUTATION


def test_stamina_specials_classify_from_canonical_effect_conditions() -> None:
    objective = "max_stamina"
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key=objective,
        evidence=(
            _evidence(
                objective,
                set_id=596,
                name="Death Dealer's Fete",
                piece_count=1,
                effects=(
                    _effect(StatId.MAX_STAMINA, 2640.0, condition="escalating_fete_stacks:30"),
                ),
            ),
            _evidence(
                objective,
                set_id=597,
                name="Shapeshifter's Chain",
                piece_count=1,
                effects=(
                    _effect(StatId.MAX_STAMINA, 1707.0, condition="transformed"),
                ),
            ),
            _evidence(
                objective,
                set_id=854,
                name="Prowler's Talisman",
                piece_count=1,
                effects=(
                    _effect(
                        StatId.MAX_STAMINA,
                        1900.0,
                        condition="prowlers_talisman_critical_stacks:10",
                    ),
                ),
            ),
            _evidence(
                objective,
                set_id=308,
                name="Bone Pirate's Tatters",
                piece_count=5,
                effects=(
                    _effect(StatId.MAX_STAMINA, 1096.0),
                    _effect(StatId.MAX_STAMINA, 2000.0, condition="drink_buff_active"),
                ),
            ),
            _evidence(
                objective,
                set_id=161,
                name="Twice-Born Star",
                piece_count=5,
                search_state_rule=ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS,
            ),
        ),
    )
    requested = tuple(
        (row.set_id, row.set_name, row.piece_count)
        for row in relevance.evidence
    )

    result = ExtremeMaxResourceSpecialNamedGearBranchService(relevance).build(requested)

    assert result.denominator_classified is True
    assert not result.unresolved
    by_name = {row.set_name: row for row in result.branches}
    assert by_name["Bone Pirate's Tatters"].kind is ExtremeMaxResourceSpecialBranchKind.CONDITIONAL_BUNDLE
    assert by_name["Bone Pirate's Tatters"].required_conditions == ("drink_buff_active",)
    assert by_name["Twice-Born Star"].search_state_rule is ExtremeGearSearchStateRule.ALLOWS_TWO_MUNDUS


def test_target_resource_filter_does_not_leak_other_resource_effects() -> None:
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_magicka",
        evidence=(
            _evidence(
                "max_magicka",
                set_id=854,
                name="Prowler's Talisman",
                piece_count=1,
                effects=(
                    _effect(StatId.MAX_MAGICKA, 1900.0, condition="prowlers_talisman_critical_stacks:10"),
                    _effect(StatId.MAX_STAMINA, 1900.0, condition="prowlers_talisman_critical_stacks:10"),
                ),
            ),
        ),
    )

    result = ExtremeMaxResourceSpecialNamedGearBranchService(relevance).build(
        ((854, "Prowler's Talisman", 1),)
    )

    assert result.denominator_classified is True
    assert len(result.branches[0].target_effects) == 1
    assert result.branches[0].target_effects[0].stat is StatId.MAX_MAGICKA
