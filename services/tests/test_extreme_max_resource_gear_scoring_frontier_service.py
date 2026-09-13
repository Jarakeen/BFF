from types import SimpleNamespace

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_max_resource_gear_scoring_frontier_service import (
    ExtremeMaxResourceGearScoringFrontierService,
)
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)


def _candidate(*, unresolved=(), condition=None):
    return SimpleNamespace(
        unresolved=tuple(unresolved),
        source_effects=(
            Effect(
                operation=EffectOperation.ADD,
                value=1000.0,
                source="test",
                stat=StatId.MAX_MAGICKA,
                condition=condition,
            ),
        ),
    )


def _evidence(set_id: int, *, unresolved=(), search_state_rule=None):
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=f"Set {set_id}",
        piece_count=5,
        objective_key="max_magicka",
        status=ExtremeGearSetObjectiveRelevance.RELEVANT,
        reviewed_delta=1000.0,
        candidate=_candidate(unresolved=unresolved),
        search_state_rule=search_state_rule,
    )


def _realization(set_id: int, *, slot="Chest", weapon_type=""):
    assignments = (
        ExtremeNamedGearSlotAssignment(
            slot=slot,
            set_id=set_id,
            set_name=f"Set {set_id}",
            weapon_type=weapon_type,
        ),
    )
    return ExtremeNamedGearSetRealization(
        topology_signature="5",
        set_ids=(set_id,),
        set_names=(f"Set {set_id}",),
        counts=(5,),
        weapon_shape=(
            ExtremeWeaponSlotShape.TWO_HANDED
            if weapon_type
            else ExtremeWeaponSlotShape.NONE
        ),
        assignments=assignments,
    )


def test_collapses_identity_distinct_ordinary_witnesses_with_same_objective_semantics():
    first = _realization(10, slot="Chest")
    second = _realization(20, slot="Ring1")
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_magicka",
        evidence=(_evidence(10), _evidence(20)),
    )

    result = ExtremeMaxResourceGearScoringFrontierService.reduce_with_relevance(
        "max_magicka", (second, first), relevance
    )

    assert result.reduction_proven is True
    assert result.semantic_classes == 1
    assert result.duplicate_witnesses_pruned == 1
    assert result.representatives == (first,)


def test_keeps_unresolved_identity_distinct():
    first = _realization(10)
    second = _realization(20)
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_magicka",
        evidence=(
            _evidence(10, unresolved=("conditional",)),
            _evidence(20, unresolved=("conditional",)),
        ),
    )

    result = ExtremeMaxResourceGearScoringFrontierService.reduce_with_relevance(
        "max_magicka", (first, second), relevance
    )

    assert result.semantic_classes == 2
    assert result.duplicate_witnesses_pruned == 0
    assert result.representatives == (first, second)


def test_keeps_weapon_type_semantics_distinct():
    inferno = _realization(10, slot="Main Hand", weapon_type="Inferno Staff")
    ice = _realization(20, slot="Main Hand", weapon_type="Ice Staff")
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_magicka",
        evidence=(_evidence(10), _evidence(20)),
    )

    result = ExtremeMaxResourceGearScoringFrontierService.reduce_with_relevance(
        "max_magicka", (inferno, ice), relevance
    )

    assert result.semantic_classes == 2
    assert result.duplicate_witnesses_pruned == 0
