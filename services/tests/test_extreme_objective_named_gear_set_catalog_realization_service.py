from __future__ import annotations

from types import SimpleNamespace

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
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)
from services.extreme_objective_named_gear_set_catalog_realization_service import (
    ExtremeObjectiveNamedGearSetCatalogRealizationService,
)


_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")
_WEAPONS = (
    "Axe", "Mace", "Sword", "Dagger", "Shield",
    "Two-Handed Sword", "Two-Handed Axe", "Two-Handed Mace",
    "Bow", "Restoration Staff", "Inferno Staff", "Ice Staff", "Lightning Staff",
)


def _ordinary(set_id: int, name: str) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Trial",
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=_WEAPONS,
    )


def _evidence(set_id: int, name: str, count: int, status: ExtremeGearSetObjectiveRelevance):
    return ExtremeGearSetObjectiveBreakpointEvidence(
        set_id=set_id,
        set_name=name,
        piece_count=count,
        objective_key="max_health",
        status=status,
        reviewed_delta=100.0 if status is ExtremeGearSetObjectiveRelevance.RELEVANT else 0.0,
        candidate=SimpleNamespace(unresolved=()),
    )


def _topology(*counts: int) -> ExtremeGearSetTopologyCatalog:
    return ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(
            ExtremeGearSetCountTopology(
                counts=tuple(counts),
                unused_units=12 - sum(counts),
            ),
        ),
    )


def _service(*, evidence, breakpoint_counts=(2, 5), relevance_unresolved=()):
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=(
            ExtremeGearSetBonusBreakpoints(10, "Relevant", 5, tuple(breakpoint_counts)),
            ExtremeGearSetBonusBreakpoints(20, "Other", 5, tuple(breakpoint_counts)),
        ),
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(_ordinary(10, "Relevant"), _ordinary(20, "Other")),
    )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="max_health",
        evidence=tuple(evidence),
        unresolved=tuple(relevance_unresolved),
    )
    return ExtremeObjectiveNamedGearSetCatalogRealizationService(
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
    )


def test_proven_irrelevant_breakpoint_is_pruned_before_named_assignment_enumeration():
    service = _service(
        evidence=(
            _evidence(10, "Relevant", 2, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(10, "Relevant", 5, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(20, "Other", 2, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            _evidence(20, "Other", 5, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
        )
    )

    result = service.build(_topology(5))

    assert result.breakpoints_reviewed == 4
    assert result.breakpoints_retained_relevant == 2
    assert result.breakpoints_pruned_irrelevant == 2
    assert result.breakpoints_retained_unresolved == 0
    assert result.assignments_considered == 1
    assert result.assignments_realized == 1
    assert result.realization.topologies[0].realizations[0].set_ids == (10,)
    assert result.denominator_proven is True


def test_unresolved_breakpoint_is_retained_and_blocks_denominator_proof():
    service = _service(
        evidence=(
            _evidence(10, "Relevant", 5, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(20, "Other", 5, ExtremeGearSetObjectiveRelevance.UNRESOLVED),
            _evidence(10, "Relevant", 2, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            _evidence(20, "Other", 2, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
        ),
        relevance_unresolved=("Other (5): active set bonus is not yet mechanic-mapped",),
    )

    result = service.build(_topology(5))

    assert result.breakpoints_retained_unresolved == 1
    assert result.assignments_considered == 2
    assert {row.set_ids for row in result.realization.topologies[0].realizations} == {(10,), (20,)}
    assert result.denominator_proven is False
    assert any("not yet mechanic-mapped" in item for item in result.unresolved)


def test_missing_relevance_evidence_is_retained_and_fails_closed():
    service = _service(
        evidence=(
            _evidence(10, "Relevant", 5, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(10, "Relevant", 2, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            _evidence(20, "Other", 2, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            # Deliberately no set 20 / count 5 relevance row.
        )
    )

    result = service.build(_topology(5))

    assert result.assignments_considered == 2
    assert {row.set_ids for row in result.realization.topologies[0].realizations} == {(10,), (20,)}
    assert result.denominator_proven is False
    assert any("Other breakpoint 5 has no objective relevance evidence" in item for item in result.unresolved)


def test_equal_count_topology_uses_only_retained_candidate_sets():
    service = _service(
        evidence=(
            _evidence(10, "Relevant", 2, ExtremeGearSetObjectiveRelevance.RELEVANT),
            _evidence(20, "Other", 2, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            _evidence(10, "Relevant", 5, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
            _evidence(20, "Other", 5, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT),
        )
    )

    result = service.build(_topology(2, 2))

    # Only one set survives at count two, so a two-distinct-set topology has no
    # legal named assignment after proof-safe pruning.
    assert result.assignments_considered == 0
    assert result.assignments_realized == 0
    assert result.denominator_proven is True


def test_assignment_limit_still_blocks_proof_after_objective_filtering():
    evidence = tuple(
        _evidence(set_id, name, 2, ExtremeGearSetObjectiveRelevance.RELEVANT)
        for set_id, name in ((10, "Relevant"), (20, "Other"))
    ) + tuple(
        _evidence(set_id, name, 5, ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT)
        for set_id, name in ((10, "Relevant"), (20, "Other"))
    )
    service = _service(evidence=evidence)

    result = service.build(_topology(2), max_assignments_per_topology=1)

    assert result.assignments_considered == 1
    assert result.truncated is True
    assert result.denominator_proven is False
