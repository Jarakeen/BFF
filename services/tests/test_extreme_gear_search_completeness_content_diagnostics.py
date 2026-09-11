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


def _evidence():
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=1,
        set_name="Canonical Set",
        piece_count=5,
        objective_key="max_health",
        status=ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT,
        reviewed_delta=0.0,
        candidate=None,
    )


def _build(eligibility_unresolved):
    return ExtremeGearSearchCompletenessAuditService.build(
        topology=ExtremeGearSetTopologyCatalog(
            sets=(ExtremeGearSetDescriptor(1, "Canonical Set", "Trial", 5),),
            topologies=(),
        ),
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(
            sets=(ExtremeGearSetBonusBreakpoints(1, "Canonical Set", 5, (5,)),),
        ),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(
            sets=(
                ExtremeNamedGearSetSlotEligibility(
                    1,
                    "Canonical Set",
                    "Trial",
                    5,
                    armor_slots=("Chest",),
                ),
            ),
            unresolved=tuple(eligibility_unresolved),
        ),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(
            objective_key="max_health",
            evidence=(_evidence(),),
        ),
    )


def test_content_only_identity_without_canonical_gear_row_is_diagnostic_not_blocker():
    message = "Content set identity 'crushing_wall' has no canonical gear_set name match"

    result = _build((message,))

    assert result.denominator_proven is True
    assert result.unresolved == ()
    assert result.diagnostics == (message,)


def test_actual_slot_eligibility_gap_still_blocks_denominator():
    message = "Gear set Canonical Set has no canonical gear_set_piece slot evidence"

    result = _build((message,))

    assert result.denominator_proven is False
    assert result.diagnostics == ()
    assert result.unresolved == (message,)
