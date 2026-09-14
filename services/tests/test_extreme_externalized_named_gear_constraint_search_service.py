from __future__ import annotations

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from services.extreme_constrained_named_gear_exact_flat_search_service import (
    ExtremeNamedGearRequirement,
)
from services.extreme_externalized_named_gear_constraint_search_service import (
    ExtremeExternalizedNamedGearConstraintSearchService,
    ExtremeExternalizedNamedGearSemantic,
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
from services.extreme_gear_set_objective_service import ExtremeGearSetObjectiveCandidate
from services.extreme_gear_set_topology_catalog_service import (
    ExtremeGearSetCountTopology,
    ExtremeGearSetTopologyCatalog,
)
from services.extreme_named_gear_set_slot_eligibility_service import (
    ExtremeNamedGearSetSlotEligibility,
    ExtremeNamedGearSetSlotEligibilityCatalog,
)


_BODY = ("Head", "Shoulders", "Chest", "Hands", "Waist", "Legs", "Feet")


def _eligibility(set_id: int, name: str) -> ExtremeNamedGearSetSlotEligibility:
    return ExtremeNamedGearSetSlotEligibility(
        set_id=set_id,
        name=name,
        category="Dungeon",
        max_equip_count=5,
        armor_slots=_BODY,
        jewelry_slots=("Necklace", "Ring"),
        weapon_types=("Two-Handed Sword",),
    )


def _candidate(
    set_id: int,
    name: str,
    *,
    delta: float,
    unresolved: tuple[str, ...] = (),
) -> ExtremeGearSetObjectiveCandidate:
    effects = ()
    if not unresolved:
        effects = (
            Effect(
                operation=EffectOperation.ADD,
                value=delta,
                source=f"{name} (5)",
                stat=StatId.HEALTH_RECOVERY,
            ),
        )
    return ExtremeGearSetObjectiveCandidate(
        set_id=set_id,
        set_name=name,
        category="Dungeon",
        equipped_piece_count=5,
        objective_key="health_recovery",
        reviewed_delta=delta,
        source_effects=effects,
        unresolved=unresolved,
    )


def test_externalized_special_set_is_structural_zero_delta_and_keeps_ordinary_score() -> None:
    special = _candidate(10, "Special Set", delta=0.0, unresolved=("runtime special semantic",))
    ordinary = _candidate(20, "Ordinary Set", delta=100.0)
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="health_recovery",
        evidence=(
            ExtremeGearSetObjectiveBreakpointEvidence(
                set_id=10,
                set_name="Special Set",
                piece_count=5,
                objective_key="health_recovery",
                status=ExtremeGearSetObjectiveRelevance.UNRESOLVED,
                reviewed_delta=0.0,
                candidate=special,
            ),
            ExtremeGearSetObjectiveBreakpointEvidence(
                set_id=20,
                set_name="Ordinary Set",
                piece_count=5,
                objective_key="health_recovery",
                status=ExtremeGearSetObjectiveRelevance.RELEVANT,
                reviewed_delta=100.0,
                candidate=ordinary,
            ),
        ),
        unresolved=(
            "Special Set (5): active set bonus is not yet mechanic-mapped: runtime special semantic",
        ),
    )
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=(
            ExtremeGearSetBonusBreakpoints(10, "Special Set", 5, (5,)),
            ExtremeGearSetBonusBreakpoints(20, "Ordinary Set", 5, (5,)),
        )
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(_eligibility(10, "Special Set"), _eligibility(20, "Ordinary Set"))
    )
    topology = ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(ExtremeGearSetCountTopology(counts=(5, 5), unused_units=2),),
    )

    result = ExtremeExternalizedNamedGearConstraintSearchService.search(
        topology_catalog=topology,
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
        requirements=(ExtremeNamedGearRequirement("Special Set", 5),),
        externalized=(ExtremeExternalizedNamedGearSemantic("Special Set", 5),),
    )

    assert result.unresolved == ()
    assert result.upstream_unresolved == relevance.unresolved
    assert result.winner_found is True
    assert result.search is not None
    assert result.search.best_exact_flat_delta == 100.0
    assert any(
        set(witness.set_names) == {"Special Set", "Ordinary Set"}
        for witness in result.search.realizations
    )


def test_externalization_keeps_unrelated_diagnostics_out_of_local_structural_gate() -> None:
    special = _candidate(10, "Special Set", delta=0.0, unresolved=("runtime special semantic",))
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="health_recovery",
        evidence=(
            ExtremeGearSetObjectiveBreakpointEvidence(
                set_id=10,
                set_name="Special Set",
                piece_count=5,
                objective_key="health_recovery",
                status=ExtremeGearSetObjectiveRelevance.UNRESOLVED,
                reviewed_delta=0.0,
                candidate=special,
            ),
        ),
        unresolved=(
            "Special Set (5): active set bonus is not yet mechanic-mapped: runtime special semantic",
            "Different Set (5): active set bonus is not yet mechanic-mapped: still pending",
        ),
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(sets=(_eligibility(10, "Special Set"),))

    derived, unresolved = ExtremeExternalizedNamedGearConstraintSearchService._derived_relevance(
        relevance,
        eligibility,
        (ExtremeExternalizedNamedGearSemantic("Special Set", 5),),
    )

    assert unresolved == ()
    assert derived is not None
    assert derived.unresolved == ()
    assert derived.evidence[0].status is ExtremeGearSetObjectiveRelevance.PROVEN_IRRELEVANT
    assert derived.evidence[0].candidate.source_effects == ()


def test_search_preserves_upstream_diagnostics_without_blocking_local_structure() -> None:
    special = _candidate(10, "Special Set", delta=0.0, unresolved=("runtime special semantic",))
    ordinary = _candidate(20, "Ordinary Set", delta=100.0)
    upstream = (
        "Special Set (5): active set bonus is not yet mechanic-mapped: runtime special semantic",
        "Different Set (5): active set bonus is not yet mechanic-mapped: still pending",
    )
    relevance = ExtremeGearSetObjectiveRelevanceCatalog(
        objective_key="health_recovery",
        evidence=(
            ExtremeGearSetObjectiveBreakpointEvidence(
                set_id=10,
                set_name="Special Set",
                piece_count=5,
                objective_key="health_recovery",
                status=ExtremeGearSetObjectiveRelevance.UNRESOLVED,
                reviewed_delta=0.0,
                candidate=special,
            ),
            ExtremeGearSetObjectiveBreakpointEvidence(
                set_id=20,
                set_name="Ordinary Set",
                piece_count=5,
                objective_key="health_recovery",
                status=ExtremeGearSetObjectiveRelevance.RELEVANT,
                reviewed_delta=100.0,
                candidate=ordinary,
            ),
        ),
        unresolved=upstream,
    )
    breakpoints = ExtremeGearSetBonusBreakpointCatalog(
        sets=(
            ExtremeGearSetBonusBreakpoints(10, "Special Set", 5, (5,)),
            ExtremeGearSetBonusBreakpoints(20, "Ordinary Set", 5, (5,)),
        )
    )
    eligibility = ExtremeNamedGearSetSlotEligibilityCatalog(
        sets=(_eligibility(10, "Special Set"), _eligibility(20, "Ordinary Set"))
    )
    topology = ExtremeGearSetTopologyCatalog(
        sets=(),
        topologies=(ExtremeGearSetCountTopology(counts=(5, 5), unused_units=2),),
    )

    result = ExtremeExternalizedNamedGearConstraintSearchService.search(
        topology_catalog=topology,
        breakpoints=breakpoints,
        eligibility=eligibility,
        relevance=relevance,
        requirements=(ExtremeNamedGearRequirement("Special Set", 5),),
        externalized=(ExtremeExternalizedNamedGearSemantic("Special Set", 5),),
    )

    assert result.unresolved == ()
    assert result.upstream_unresolved == upstream
    assert result.winner_found is True
    assert result.search is not None
    assert result.search.best_exact_flat_delta == 100.0
