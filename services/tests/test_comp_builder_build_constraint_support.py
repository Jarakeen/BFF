from services.comp_builder_build_candidates import CompBuildCandidate
from services.team_prescription_slot_constraints import PrescribedSlotBuildConstraint
from ui.comp_builder_build_constraint_support import candidate_matches_constraint


def _candidate(*, eso_class: str = "Warden", gear_sets: tuple[str, ...] = ()) -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id="saved:0:DF Healer",
        name="DF Healer",
        source_kind="saved_build",
        source_name="Magrat",
        source_url="",
        eso_class=eso_class,
        role="Healer",
        gear_sets=gear_sets,
        skills=("Combat Prayer",),
        mundus="The Ritual",
        complete_build=True,
        unresolved=(),
        score=100.0,
        score_reasons=("test",),
    )


def test_build_around_constraint_requires_exact_class_and_gear_evidence() -> None:
    constraint = PrescribedSlotBuildConstraint(
        slot_name="Healer 1",
        required_class="Warden",
        required_gear_sets=("Serpent's Disdain",),
    )

    assert candidate_matches_constraint(
        _candidate(gear_sets=("Serpent's Disdain", "Spell Power Cure")),
        constraint,
    )
    assert not candidate_matches_constraint(
        _candidate(gear_sets=("Spell Power Cure",)),
        constraint,
    )
    assert not candidate_matches_constraint(
        _candidate(eso_class="Arcanist", gear_sets=("Serpent's Disdain",)),
        constraint,
    )


def test_build_around_constraint_uses_existing_perfected_set_identity_rule() -> None:
    constraint = PrescribedSlotBuildConstraint(
        slot_name="Healer 1",
        required_gear_sets=("Pillager's Profit",),
    )

    assert candidate_matches_constraint(
        _candidate(gear_sets=("Perfected Pillager's Profit",)),
        constraint,
    )


def test_build_around_support_filters_candidates_and_revalidates_before_transfer() -> None:
    from pathlib import Path

    source = Path("ui/comp_builder_build_constraint_support.py").read_text(encoding="utf-8")
    installer = Path("ui/team_optimization_hybrid_anchor_support.py").read_text(encoding="utf-8")

    assert "BUILD AROUND • REQUIRED GEAR SETS" in source
    assert "parse_required_gear_sets(text)" in source
    assert "support._chair_candidates = _chair_candidates_with_build_constraints" in source
    assert "candidate.candidate_id not in current_ids" in source
    assert "Re-optimize the team first" in source
    assert "install_comp_builder_build_constraints" in installer
