from minmax.build_candidate_comparison import CandidateConstraint, ConstraintStatus
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import GearSlot, PlayerBuild
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_candidate_source import (
    PrescribedObjectiveMeasurement,
    PrescribedOpenSlotCandidate,
)
from services.team_prescription_pipeline import (
    run_automatic_team_prescription_candidate_pipeline,
)
from services.team_prescription_slot_constraints import (
    PrescribedSlotBuildConstraint,
    build_gear_set_names,
    parse_required_gear_sets,
    project_slot_build_constraints,
)


def _build(candidate_id: str, *, eso_class: str, gear_set: str) -> PlayerBuild:
    return PlayerBuild(
        Name=candidate_id,
        BuildName=f"{candidate_id} Healer",
        Role="Healer",
        EsoClass=eso_class,
        FrontBarWeapon=GearSlot(Set=gear_set),
    )


def _candidate(candidate_id: str, *, eso_class: str, gear_set: str):
    return PrescribedOpenSlotCandidate.from_build(
        candidate_id=candidate_id,
        candidate_build=_build(
            candidate_id,
            eso_class=eso_class,
            gear_set=gear_set,
        ),
        candidate_source="phase13:test-required-ingredients",
        player_name=candidate_id,
    )


def _measurement(candidate, _slot_name):
    return PrescribedObjectiveMeasurement(
        objective=EvaluationObjective.HEALING,
        value=200.0 if candidate.candidate_id == "raw-healing" else 150.0,
        metric_name="modeled healing-component potency",
        constraints=(
            CandidateConstraint(
                name="magicka sustain",
                status=ConstraintStatus.PRESERVED,
                explanation="test evidence",
            ),
        ),
    )


def _roster() -> PrescribedRoster:
    return PrescribedRoster(
        name="Brittle Team",
        goal="Custom Goal",
        scope=TeamPrescriptionScope(
            dimensions=(PrescriptionDimension.CLASS, PrescriptionDimension.GEAR)
        ),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="Healer 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="Healer",
                unresolved=("Healer 1: requires evidence",),
            ),
        ),
        unresolved=("Healer 1: requires evidence",),
    )


def test_required_gear_parser_is_exact_deduplicated_and_perfected_compatible() -> None:
    parsed = parse_required_gear_sets(
        " Serpent's Disdain; Pillager's Profit, Perfected Pillager's Profit "
    )

    assert parsed == ("Serpent's Disdain", "Pillager's Profit")
    build = _build(
        "keen",
        eso_class="Warden",
        gear_set="Perfected Serpent's Disdain",
    )
    assert build_gear_set_names(build) == ("Perfected Serpent's Disdain",)
    assert PrescribedSlotBuildConstraint(
        slot_name="Healer 1",
        required_gear_sets=("Serpent's Disdain",),
    ).matches(build)


def test_injected_class_and_gear_are_hard_gates_before_objective_ranking() -> None:
    result = run_automatic_team_prescription_candidate_pipeline(
        roster=_roster(),
        candidates=(
            _candidate(
                "raw-healing",
                eso_class="Arcanist",
                gear_set="Spell Power Cure",
            ),
            _candidate(
                "brittle-warden",
                eso_class="Warden",
                gear_set="Serpent's Disdain",
            ),
        ),
        evaluate_objective=_measurement,
        build_constraints_by_slot={
            "Healer 1": PrescribedSlotBuildConstraint(
                slot_name="Healer 1",
                required_class="Warden",
                required_gear_sets=("Serpent's Disdain",),
            )
        },
    )

    assignment = result.final_roster.assignments[0]
    assert assignment.player_name == "brittle-warden"
    assert assignment.source_build_name == "brittle-warden Healer"
    assert assignment.prescribed_build is not None
    assert assignment.prescribed_build.EsoClass == "Warden"


def test_missing_required_ingredients_remain_explicitly_unresolved() -> None:
    result = run_automatic_team_prescription_candidate_pipeline(
        roster=_roster(),
        candidates=(
            _candidate(
                "raw-healing",
                eso_class="Arcanist",
                gear_set="Spell Power Cure",
            ),
        ),
        evaluate_objective=_measurement,
        build_constraints_by_slot={
            "Healer 1": PrescribedSlotBuildConstraint(
                slot_name="Healer 1",
                required_class="Warden",
                required_gear_sets=("Serpent's Disdain",),
            )
        },
    )

    assert result.final_roster.assignments[0].source_build_name is None
    assert any(
        "Warden / Serpent's Disdain" in message for message in result.unresolved
    )


def test_user_ingredients_are_visible_without_fabricating_complete_build() -> None:
    projected = project_slot_build_constraints(
        roster=_roster(),
        constraints=(
            PrescribedSlotBuildConstraint(
                slot_name="Healer 1",
                required_class="Warden",
                required_gear_sets=("Serpent's Disdain",),
            ),
        ),
    )

    assignment = projected.assignments[0]
    assert assignment.change_for(PrescriptionDimension.CLASS).prescribed_value == "Warden"
    assert (
        assignment.change_for(PrescriptionDimension.GEAR).prescribed_value
        == "Serpent's Disdain"
    )
    assert assignment.prescribed_build is None
    assert assignment.unresolved == ("Healer 1: requires evidence",)
