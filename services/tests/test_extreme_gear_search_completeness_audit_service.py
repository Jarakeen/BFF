from types import SimpleNamespace

from services.extreme_gear_search_completeness_audit_service import (
    ExtremeGearSearchCompletenessAuditService,
)
from services.extreme_gear_set_bonus_breakpoint_service import (
    ExtremeGearSetBonusBreakpointCatalog,
    ExtremeGearSetBonusBreakpoints,
)
from services.extreme_gear_set_objective_relevance_service import (
    ExtremeGearSetObjectiveBreakpointEvidence,
    ExtremeGearSetObjectiveRelevance,
    ExtremeGearSetObjectiveRelevanceCatalog,
)
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetDescriptor,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


def _topology(*ids):
    return ExtremeGearSetTopologyCatalog(
        sets=tuple(
            ExtremeGearSetDescriptor(set_id=value, name=f"Set {value}", category="Trial", max_equip_count=5)
            for value in ids
        ),
        topologies=(),
    )


def _breakpoints(*rows):
    return ExtremeGearSetBonusBreakpointCatalog(
        sets=tuple(
            ExtremeGearSetBonusBreakpoints(
                set_id=set_id,
                name=f"Set {set_id}",
                max_equip_count=5,
                bonus_counts=tuple(counts),
            )
            for set_id, counts in rows
        )
    )


def _eligibility(*ids):
    return ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=tuple(
            ExtremeNamedGearSetSlotEligibility(
                set_id=value,
                name=f"Set {value}",
                category="Trial",
                max_equip_count=5,
                armor_slots=("Chest",),
            )
            for value in ids
        )
    )


def _evidence(set_id, count, status):
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=f"Set {set_id}",
        piece_count=count,
        objective_key="max_health",
        status=status,
        reviewed_delta=100.0 if status is ExtremeGearSetObjectiveRelevance.RELEVANT else 0.0,
        candidate=SimpleNamespace(),
    )


def test_complete_denominator_is_proven():
    result = ExtremeGearSearchCompletenessAuditService.build(
        topology=_topology(1, 2),
        breakpoints=_breakpoints((1, (2, 5)), (2, (1,))),
        eligibility=_eligibility(1, 2),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_health",
            evidence=(
                _evidence(1, 2, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
                _evidence(1, 5, ExtremeGearSetObjectiveRelevance.RELEVANT),
                _evidence(2, 1, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            ),
        ),
    )

    assert result.denominator_proven is True
    assert result.canonical_sets_reviewed == 2
    assert result.mechanically_relevant_breakpoints == 3
    assert result.relevance_breakpoints_reviewed == 3


def test_missing_set_layer_and_missing_relevance_breakpoint_fail_closed():
    result = ExtremeGearSearchCompletenessAuditService.build(
        topology=_topology(1, 2),
        breakpoints=_breakpoints((1, (2, 5)),),
        eligibility=_eligibility(1),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_health",
            evidence=(
                _evidence(1, 2, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            ),
        ),
    )

    assert result.denominator_proven is False
    assert result.missing_from_breakpoints == (2,)
    assert result.missing_from_slot_eligibility == (2,)
    assert result.missing_relevance_breakpoints == ((1, 5),)


def test_extra_rows_and_candidate_without_slot_evidence_fail_closed():
    topology = _topology(1)
    breakpoints = _breakpoints((1, (5,)), (9, (5,)))
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(
            ExtremeNamedGearSetSlotEligibility(
                set_id=1,
                name="Set 1",
                category="Trial",
                max_equip_count=5,
            ),
            ExtremeNamedGearSetSlotEligibility(
                set_id=9,
                name="Set 9",
                category="Trial",
                max_equip_count=5,
                armor_slots=("Chest",),
            ),
        )
    )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=(
            _evidence(1, 5, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(9, 5, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
        ),
    )

    result = ExtremeGearSearchCompletenessAuditService.build(
        topology=topology,
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )

    assert result.denominator_proven is False
    assert result.extra_breakpoint_sets == (9,)
    assert result.extra_slot_eligibility_sets == (9,)
    assert result.candidate_sets_without_slot_evidence == (1,)


def test_underlying_catalog_unresolved_is_preserved():
    result = ExtremeGearSearchCompletenessAuditService.build(
        topology=ExtremeGearSetTopologyCatalog(
            sets=(ExtremeGearSetDescriptor(1, "Set 1", "Trial", 5),),
            topologies=(),
            unresolved=("topology gap",),
        ),
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(
            sets=(ExtremeGearSetBonusBreakpoints(1, "Set 1", 5, (5,)),),
            unresolved=("breakpoint gap",),
        ),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=(ExtremeNamedGearSetSlotEligibility(1, "Set 1", "Trial", 5, armor_slots=("Chest",)),),
            unresolved=("slot gap",),
        ),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_health",
            evidence=(_evidence(1, 5, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),),
            unresolved=("relevance gap",),
        ),
    )

    assert result.denominator_proven is False
    assert result.unresolved == (
        "topology gap",
        "breakpoint gap",
        "slot gap",
        "relevance gap",
    )
