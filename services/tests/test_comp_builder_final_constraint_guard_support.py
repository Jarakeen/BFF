from pathlib import Path


def test_final_constraint_guard_filters_every_merged_candidate_source() -> None:
    source = Path("ui/comp_builder_final_constraint_guard_support.py").read_text(
        encoding="utf-8"
    )

    assert "candidates = tuple(_ORIGINAL_CHAIR_CANDIDATES(page, row))" in source
    assert "constraint_support._constraint_for_row(page, row)" in source
    assert "constraint_support.candidate_matches_constraint(candidate, constraint)" in source
    assert "candidate_support._chair_candidates = _chair_candidates_with_final_constraints" in source


def test_final_constraint_guard_installs_after_trial_and_esologs_candidate_wrappers() -> None:
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(
        encoding="utf-8"
    )

    trial = installer.index("install_comp_builder_trial_flow()")
    esologs = installer.index("install_comp_builder_esologs_snapshot_candidates()")
    guard = installer.index("install_comp_builder_final_constraint_guard()")
    assert trial < guard
    assert esologs < guard


def test_final_constraint_guard_reuses_existing_hard_constraint_model() -> None:
    guard = Path("ui/comp_builder_final_constraint_guard_support.py").read_text(
        encoding="utf-8"
    )
    constraint = Path("ui/comp_builder_build_constraint_support.py").read_text(
        encoding="utf-8"
    )

    assert "comp_builder_build_constraint_support as constraint_support" in guard
    assert "PrescribedSlotBuildConstraint" in constraint
    assert "constraint.matches(_candidate_fact_build(candidate))" in constraint
    assert "required_gear_sets=gear_sets" in constraint
    assert "required_class=required_class" in constraint


def test_send_validation_reads_the_final_guarded_candidate_path() -> None:
    constraint = Path("ui/comp_builder_build_constraint_support.py").read_text(
        encoding="utf-8"
    )

    assert "for item in support._chair_candidates(self, row)" in constraint
    assert "candidate.candidate_id not in current_ids" in constraint
    assert "no longer satisfies" in constraint
