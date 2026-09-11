from __future__ import annotations

from minmax.effect_kinds import EffectKind
from minmax.effects import Effect, EffectOperation, EffectUnit
from minmax.stat_ids import StatId
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceService,
)
from services.extreme_gear_set_objective_service import (
    ExtremeGearSetObjectiveCandidate,
    ExtremeGearSetObjectiveService,
)


class _Set:
    id = 1
    name = "Armor Master"


class _Repository:
    def get_set_by_id(self, set_id):
        return _Set() if int(set_id) == 1 else None


def _catalog():
    return ExtremeGearSetBonusBreakpointCatalog(
        sets=(
            ExtremeGearSetBonusBreakpoints(
                set_id=1,
                name="Armor Master",
                max_equip_count=5,
                bonus_counts=(5,),
            ),
        )
    )


def _effect():
    return Effect(
        operation=EffectOperation.ADD_PERCENT,
        value=5.0,
        source="Armor Master (5)",
        stat=StatId.MAX_HEALTH,
        kind=EffectKind.STAT,
        unit=EffectUnit.PERCENT,
        condition="armor_ability_slotted",
    )


def test_positive_target_effect_is_relevant_even_when_exact_projection_is_deferred(monkeypatch):
    monkeypatch.setattr(
        ExtremeGearSetObjectiveService,
        "candidate_for_set",
        lambda *args, **kwargs: ExtremeGearSetObjectiveCandidate(
            set_id=1,
            set_name="Armor Master",
            category="Crafted",
            equipped_piece_count=5,
            objective_key="max_health",
            reviewed_delta=0.0,
            source_effects=(_effect(),),
            unresolved=(
                "Armor Master (5): relevant percentage set effect requires objective-specific stacking/reference review",
            ),
        ),
    )

    result = ExtremeGearSetObjectiveRelevanceService(_Repository()).build(
        "max_health",
        _catalog(),
    )

    assert result.denominator_proven is True
    assert result.unresolved == ()
    assert result.evidence[0].status is ExtremeGearSetObjectiveRelevance.RELEVANT
    assert result.evidence[0].candidate.unresolved


def test_unknown_active_bonus_still_blocks_even_with_positive_target_effect(monkeypatch):
    monkeypatch.setattr(
        ExtremeGearSetObjectiveService,
        "candidate_for_set",
        lambda *args, **kwargs: ExtremeGearSetObjectiveCandidate(
            set_id=1,
            set_name="Armor Master",
            category="Crafted",
            equipped_piece_count=5,
            objective_key="max_health",
            reviewed_delta=0.0,
            source_effects=(_effect(),),
            unresolved=(
                "Armor Master (5): relevant percentage set effect requires objective-specific stacking/reference review",
                "Armor Master (5): active set bonus is not yet mechanic-mapped: mystery mechanic",
            ),
        ),
    )

    result = ExtremeGearSetObjectiveRelevanceService(_Repository()).build(
        "max_health",
        _catalog(),
    )

    assert result.denominator_proven is False
    assert result.evidence[0].status is ExtremeGearSetObjectiveRelevance.UNRESOLVED
    assert any("mystery mechanic" in item for item in result.unresolved)
