from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_objective32_blocker_service import (
    ExtremeSustainedDPSObjective32BlockerService,
)


def test_closed_objective_has_no_blockers() -> None:
    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=SimpleNamespace(
            global_maximum_proven=True,
            unresolved=(),
        ),
        axis_inventory=SimpleNamespace(
            missing_canonical_axes=(),
            duplicate_canonical_axes=(),
            unresolved=(),
        ),
        axis_coverage=SimpleNamespace(
            missing_axes=(),
            unresolved=(),
        ),
        closure=SimpleNamespace(
            omitted_scope=(),
        ),
    )

    assert result.closed is True
    assert result.blockers == ()


def test_reports_missing_axis_and_theoretical_omission_structurally() -> None:
    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=SimpleNamespace(
            global_maximum_proven=True,
            unresolved=(),
        ),
        axis_inventory=SimpleNamespace(
            missing_canonical_axes=("runtime_state",),
            duplicate_canonical_axes=(),
            unresolved=(),
        ),
        axis_coverage=SimpleNamespace(
            missing_axes=("runtime_state",),
            unresolved=(),
        ),
        closure=SimpleNamespace(
            omitted_scope=(
                "continuous potion first-use offset remains open",
            ),
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
        search_result=SimpleNamespace(
            global_maximum_proven=False,
            unresolved=("leaf damage unresolved",),
        ),
        axis_inventory=SimpleNamespace(
            missing_canonical_axes=(),
            duplicate_canonical_axes=("mundus",),
            unresolved=("tree metadata conflict",),
        ),
        axis_coverage=SimpleNamespace(
            missing_axes=(),
            unresolved=("coverage contributor open",),
        ),
        closure=SimpleNamespace(
            omitted_scope=(),
        ),
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
    gap = SimpleNamespace(
        key="weapon_enchantments:runtime_cadence",
        needed_evidence="prove enchantment trigger and base cooldown",
    )
    advisory = SimpleNamespace(
        key="skills:runtime_topology",
        needed_evidence="complete per-skill runtime topology",
    )
    inventory = SimpleNamespace(
        source_data_blockers=("scaled debuff magnitude unresolved",),
        math_review_blockers=("unique proc has no reviewed DPS router",),
        mechanics_blockers=(gap,),
        mechanics_advisories=(advisory,),
    )

    result = ExtremeSustainedDPSObjective32BlockerService.assess(
        search_result=SimpleNamespace(
            global_maximum_proven=True,
            unresolved=(),
        ),
        axis_inventory=SimpleNamespace(
            missing_canonical_axes=(),
            duplicate_canonical_axes=(),
            unresolved=(),
        ),
        axis_coverage=SimpleNamespace(
            missing_axes=(),
            unresolved=(),
        ),
        closure=SimpleNamespace(
            omitted_scope=(),
        ),
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
        search_result=SimpleNamespace(
            global_maximum_proven=True,
            unresolved=(),
        ),
        axis_inventory=SimpleNamespace(
            missing_canonical_axes=(),
            duplicate_canonical_axes=(),
            unresolved=(),
        ),
        axis_coverage=SimpleNamespace(
            missing_axes=(),
            unresolved=(),
        ),
        closure=SimpleNamespace(
            omitted_scope=(),
        ),
    )

    assert result.closed is True
    assert result.blockers == ()
    assert any("Runtime source-data blockers: 0" in row for row in result.evidence)
