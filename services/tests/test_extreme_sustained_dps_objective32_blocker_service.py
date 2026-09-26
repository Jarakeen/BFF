from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_objective32_blocker_service import (
    ExtremeSustainedDPSObjective32Blocker,
    ExtremeSustainedDPSObjective32BlockerReport,
    ExtremeSustainedDPSObjective32BlockerService,
)
from services.extreme_sustained_dps_generated_branch_and_bound_search_service import (
    ExtremeSustainedDPSExactLeafEvaluation,
    ExtremeSustainedDPSGeneratedSearchResult,
)
from services.extreme_sustained_dps_generated_axis_inventory_service import (
    ExtremeSustainedDPSGeneratedAxisInventory,
)
from services.extreme_sustained_dps_axis_dominance_composition_service import (
    CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
    ExtremeSustainedDPSAxisCoverageProof,
    ExtremeSustainedDPSAxisDominanceCompositionService,
)
from services.extreme_sustained_dps_theoretical_maximum_closure_service import (
    ExtremeSustainedDPSTheoreticalMaximumClosure,
)
from services.extreme_sustained_dps_closure_inventory_service import (
    ExtremeSustainedDPSClosureInventory,
)
from services.canonical_knowledge_gap import (
    CanonicalKnowledgeDomain,
    CanonicalKnowledgeGap,
)



def _canonical_search(*, proven=True, unresolved=()):
    unresolved = tuple(unresolved)
    leaf = ExtremeSustainedDPSExactLeafEvaluation(
        candidate_key="objective32-blocker-test",
        modeled_dps=150.0,
        duration_seconds=20.0,
        mechanic_complete=True,
    )
    retained = (leaf,) if proven else ()
    return ExtremeSustainedDPSGeneratedSearchResult(
        best_modeled_dps=150.0 if proven else None,
        best_candidates=retained,
        unique_leader=leaf if proven else None,
        evaluated_leaves=retained,
        visited_branch_count=1 if proven else 0,
        expanded_branch_count=0,
        evaluated_leaf_count=len(retained),
        pruned_branch_count=0,
        forced_open_branch_count=0,
        global_maximum_proven=proven,
        unique_leader_proven=proven,
        evidence=(),
        unresolved=unresolved,
    )


def _canonical_inventory(*, missing=(), duplicate=(), unresolved=()):
    searched = tuple(
        axis for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        if axis not in set(missing)
    )
    return ExtremeSustainedDPSGeneratedAxisInventory(
        axis_names=searched,
        searched_canonical_axes=searched,
        missing_canonical_axes=tuple(missing),
        untagged_axis_names=(),
        duplicate_canonical_axes=tuple(duplicate),
        omitted_scope=(),
        evidence=(),
        unresolved=tuple(unresolved),
    )


def _canonical_coverage(*, missing=(), unresolved=()):
    dominated = tuple(
        axis for axis in CANONICAL_SUSTAINED_DPS_MUTATION_AXES
        if axis not in set(missing)
    )
    proof = ExtremeSustainedDPSAxisCoverageProof(
        source="canonical blocker test coverage",
        dominated_axes=dominated,
        unresolved=tuple(unresolved),
    )
    return ExtremeSustainedDPSAxisDominanceCompositionService.compose(
        candidate_key="objective32-test",
        required_axes=CANONICAL_SUSTAINED_DPS_MUTATION_AXES,
        proofs=(proof,),
    )

def _canonical_closure(*, omitted=(), unresolved=()):
    return ExtremeSustainedDPSTheoreticalMaximumClosure(
        finite_denominator_maximum_proven=False,
        canonical_axis_coverage_complete=False,
        mechanics_closure_complete=False,
        omitted_scope=tuple(omitted),
        theoretical_maximum_proven=False,
        best_modeled_dps=None,
        evidence=(),
        unresolved=tuple(unresolved),
    )


def test_closed_objective_has_no_blockers() -> None:
    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=_canonical_search(),
        axis_inventory=_canonical_inventory(),
        axis_coverage=_canonical_coverage(),
        closure=_canonical_closure(),
    )

    assert result.closed is True
    assert result.blockers == ()


def test_reports_missing_axis_and_theoretical_omission_structurally() -> None:
    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=_canonical_search(),
        axis_inventory=_canonical_inventory(missing=("runtime_state",)),
        axis_coverage=_canonical_coverage(missing=("runtime_state",)),
        closure=_canonical_closure(
            omitted=("continuous potion first-use offset remains open",)
        ),
    )

    assert result.closed is False
    assert tuple(row.code for row in result.blockers) == (
        "physical_axis_missing",
        "axis_coverage_missing",
        "theoretical_scope_omitted",
    )
    assert result.blockers[0].axis == "runtime_state"


def test_reports_search_and_inventory_unresolved_evidence() -> None:
    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=_canonical_search(
            proven=False,
            unresolved=("leaf damage unresolved",),
        ),
        axis_inventory=_canonical_inventory(
            duplicate=("mundus",),
            unresolved=("tree metadata conflict",),
        ),
        axis_coverage=_canonical_coverage(
            unresolved=("coverage contributor open",)
        ),
        closure=_canonical_closure(),
    )

    codes = tuple(row.code for row in result.blockers)
    assert codes == (
        "finite_denominator_open",
        "search_evidence_unresolved",
        "physical_axis_duplicate",
        "tree_inventory_unresolved",
        "axis_coverage_unresolved",
    )


def test_integrates_typed_runtime_and_mechanics_closure_inventory() -> None:
    gap = CanonicalKnowledgeGap(
        domain=CanonicalKnowledgeDomain.COOLDOWN,
        key="weapon_enchantments:runtime_cadence",
        summary="Weapon enchantment runtime cadence remains open",
        needed_evidence="prove enchantment trigger and base cooldown",
        consumers=("optimizer",),
        source_context="Objective #32 regression fixture",
        blocking=True,
    )
    advisory = CanonicalKnowledgeGap(
        domain=CanonicalKnowledgeDomain.SKILL_MECHANIC,
        key="skills:runtime_topology",
        summary="Skill runtime topology remains partially reviewed",
        needed_evidence="complete per-skill runtime topology",
        consumers=("optimizer",),
        source_context="Objective #32 regression fixture",
        blocking=False,
    )
    inventory = ExtremeSustainedDPSClosureInventory(
        source_data_blockers=("scaled debuff magnitude unresolved",),
        math_review_blockers=("unique proc has no reviewed DPS router",),
        mechanics_blockers=(gap,),
        mechanics_advisories=(advisory,),
        evidence=(),
    )

    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=_canonical_search(),
        axis_inventory=_canonical_inventory(),
        axis_coverage=_canonical_coverage(),
        closure=_canonical_closure(),
        closure_inventory=inventory,
    )

    assert result.closed is False
    assert tuple(row.code for row in result.blockers) == (
        "runtime_source_data_unresolved",
        "runtime_math_review_unresolved",
        "mechanics_coverage_missing_critical",
        "mechanics_coverage_partial",
    )
    assert any(
        "Runtime source-data blockers: 1" in row
        for row in result.evidence
    )
    assert any(
        "Runtime math/review blockers: 1" in row
        for row in result.evidence
    )
    assert any(
        "Mechanics-coverage blockers: 2" in row
        for row in result.evidence
    )


def test_legacy_blocker_assessment_remains_closed_without_inventory() -> None:
    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=_canonical_search(),
        axis_inventory=_canonical_inventory(),
        axis_coverage=_canonical_coverage(),
        closure=_canonical_closure(),
    )

    assert result.closed is True
    assert result.blockers == ()
    assert any("Runtime source-data blockers: 0" in row for row in result.evidence)


def test_theoretical_gate_unresolved_is_visible_without_inventory() -> None:
    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=_canonical_search(),
        axis_inventory=_canonical_inventory(),
        axis_coverage=_canonical_coverage(),
        closure=_canonical_closure(
            unresolved=("Objective #32 mechanics closure remains open",)
        ),
    )

    assert result.closed is False
    assert tuple(row.code for row in result.blockers) == (
        "theoretical_closure_unresolved",
    )


def test_blocker_assessment_rejects_noncanonical_search_before_inner_flags() -> None:
    with pytest.raises(TypeError, match="canonical generated search result"):
        ExtremeSustainedDPSObjective32BlockerService.assess(
            search_result=SimpleNamespace(
                global_maximum_proven="false",
                unresolved=(),
            ),
            axis_inventory=_canonical_inventory(),
            axis_coverage=_canonical_coverage(),
            closure=_canonical_closure(),
        )

def test_blocker_report_requires_canonical_blocker_records() -> None:
    with pytest.raises(TypeError, match="canonical blocker records"):
        ExtremeSustainedDPSObjective32BlockerReport(
            blockers=(object(),),
            evidence=(),
        )


def test_blocker_assessment_rejects_duck_typed_mutable_search_record() -> None:
    with pytest.raises(TypeError, match="canonical generated search result"):
        ExtremeSustainedDPSObjective32BlockerService.assess(
            search_result=SimpleNamespace(
                global_maximum_proven=True,
                unresolved=[],
            ),
            axis_inventory=_canonical_inventory(),
            axis_coverage=_canonical_coverage(),
            closure=_canonical_closure(),
        )

def test_blocker_report_rejects_mutable_proof_collections() -> None:
    with pytest.raises(TypeError, match="blockers must be a tuple"):
        ExtremeSustainedDPSObjective32BlockerReport(
            blockers=[],
            evidence=(),
        )



def test_blocker_report_rejects_duplicate_blocker_identity() -> None:
    blocker = ExtremeSustainedDPSObjective32Blocker(
        code="same",
        category="coverage",
        detail="same debt",
        axis="runtime_state",
    )
    with pytest.raises(ValueError, match="duplicate blockers"):
        ExtremeSustainedDPSObjective32BlockerReport(
            blockers=(blocker, blocker),
            evidence=(),
        )


def test_blocker_assessment_rejects_duck_typed_proof_records() -> None:
    with pytest.raises(TypeError, match="canonical generated search result"):
        ExtremeSustainedDPSObjective32BlockerService.assess(
            search_result=SimpleNamespace(
                global_maximum_proven=True,
                unresolved=(),
            ),
            axis_inventory=SimpleNamespace(),
            axis_coverage=SimpleNamespace(),
            closure=SimpleNamespace(),
        )
