from minmax.build_candidate import BuildCandidate
from minmax.build_candidate_comparison import (
    BuildCandidateComparison,
    CandidateConstraint,
    ConstraintStatus,
)
from minmax.evaluation_objective import EvaluationObjective
from models.build_model import PlayerBuild
from services.named_buff_resolution_service import NamedBuffContribution
from services.team_prescription import (
    PrescribedRoster,
    PrescribedRosterAssignment,
    PrescriptionDimension,
    TeamPrescriptionScope,
)
from services.team_prescription_candidate_ranking import (
    PrescribedSlotCandidateEvidence,
    rank_prescribed_slot_candidates,
)
from services.team_prescription_optimizer import optimize_prescribed_roster_candidates
from services.team_provider_marginal_value_service import TeamProviderMarginalValueService


def _buff(key, objective, delta, source, kind="other"):
    return NamedBuffContribution(
        stacking_key=key,
        objective_key=objective,
        projected_delta=delta,
        source=source,
        source_kind=kind,
    )


def _evidence(candidate_id, *, value=130.0, effects=(), provider_ids=()):
    build = PlayerBuild(
        Name=candidate_id,
        BuildName=f"{candidate_id} Build",
        Role="DD",
        EsoClass="Arcanist",
    )
    candidate = BuildCandidate.from_build(
        character_id=f"candidate:{candidate_id}",
        baseline_build_id="provider-baseline",
        candidate_id=candidate_id,
        candidate_build=build,
        changes=(),
        candidate_source="phase13.2:test-team-provider-marginal",
    )
    comparison = BuildCandidateComparison(
        candidate=candidate,
        objective=EvaluationObjective.DAMAGE,
        baseline_value=100.0,
        candidate_value=value,
        constraints=(
            CandidateConstraint(
                name="hard constraint",
                status=ConstraintStatus.PRESERVED,
                explanation="provider marginal test",
            ),
        ),
    )
    return PrescribedSlotCandidateEvidence(
        comparison=comparison,
        provider_requirement_ids=provider_ids,
        provider_effects=effects,
    )


def _two_dd_roster():
    return PrescribedRoster(
        name="Marginal Provider Roster",
        goal="Optimization",
        scope=TeamPrescriptionScope(
            dimensions=(PrescriptionDimension.CLASS, PrescriptionDimension.BUILD)
        ),
        assignments=(
            PrescribedRosterAssignment(
                slot_name="DD 1",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 1 open",),
            ),
            PrescribedRosterAssignment(
                slot_name="DD 2",
                player_name=None,
                source_build_name=None,
                prescribed_role="DD",
                unresolved=("DD 2 open",),
            ),
        ),
        unresolved=("DD 1 open", "DD 2 open"),
    )


def test_duplicate_named_provider_has_zero_marginal_team_value():
    existing = (_buff("major_sorcery", "spell_damage", 600.0, "potion", "potion"),)
    candidate = (_buff("Major Sorcery", "spell_damage", 600.0, "skill", "skill"),)

    result = TeamProviderMarginalValueService.evaluate(
        existing_team_effects=existing,
        candidate_effects=candidate,
    )

    assert result.new_named_effect_count == 0
    assert result.delta_for("spell_damage") == 0.0
    assert result.suppressed


def test_stronger_same_named_provider_can_replace_weaker_existing_source():
    existing = (_buff("minor_resolve", "physical_resistance", 1000.0, "weak source"),)
    candidate = (_buff("minor_resolve", "physical_resistance", 2974.0, "Bound Aegis", "skill"),)

    result = TeamProviderMarginalValueService.evaluate(
        existing_team_effects=existing,
        candidate_effects=candidate,
    )

    assert result.new_named_effect_count == 1
    assert result.delta_for("physical_resistance") == 1974.0
    assert result.stacking_keys == ("minor_resolve",)


def test_distinct_major_and_minor_named_effects_both_remain_marginal():
    existing = (_buff("major_resolve", "physical_resistance", 5948.0, "major"),)
    candidate = (_buff("minor_resolve", "physical_resistance", 2974.0, "minor"),)

    result = TeamProviderMarginalValueService.evaluate(
        existing_team_effects=existing,
        candidate_effects=candidate,
    )

    assert result.new_named_effect_count == 1
    assert result.delta_for("physical_resistance") == 2974.0


def test_equal_objective_candidates_use_unique_missing_provider_as_tiebreak():
    existing = (_buff("major_sorcery", "spell_damage", 600.0, "potion", "potion"),)
    redundant = _evidence(
        "redundant",
        effects=(_buff("major_sorcery", "spell_damage", 600.0, "redundant skill", "skill"),),
    )
    useful = _evidence(
        "useful",
        effects=(_buff("minor_resolve", "physical_resistance", 2974.0, "useful skill", "skill"),),
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=(),
        candidates=(redundant, useful),
        existing_team_effects=existing,
    )

    assert ranking.recommended is useful
    values = dict(ranking.provider_marginal_values)
    assert values["redundant"].new_named_effect_count == 0
    assert values["useful"].new_named_effect_count == 1


def test_higher_canonical_objective_still_wins_over_provider_tiebreak_signal():
    high = _evidence("high", value=140.0)
    lower_with_provider = _evidence(
        "lower",
        value=130.0,
        effects=(_buff("minor_resolve", "physical_resistance", 2974.0, "provider", "skill"),),
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=(),
        candidates=(high, lower_with_provider),
    )

    assert ranking.recommended is high
    assert ranking.provider_marginal_values == ()


def test_hard_provider_requirement_still_blocks_candidate_with_better_marginal_effects():
    missing_required = _evidence(
        "missing-required",
        effects=(_buff("minor_resolve", "physical_resistance", 2974.0, "useful", "skill"),),
    )
    required = _evidence(
        "required",
        value=120.0,
        provider_ids=("trial:required-provider",),
    )

    ranking = rank_prescribed_slot_candidates(
        slot_name="DD 1",
        required_provider_requirement_ids=("trial:required-provider",),
        candidates=(missing_required, required),
    )

    assert ranking.recommended is required
    assert any(row.candidate_id == "missing-required" for row in ranking.rejected)


def test_team_optimizer_carries_selected_provider_into_next_open_slot_context():
    major = _buff("major_sorcery", "spell_damage", 600.0, "major provider", "skill")
    minor = _buff("minor_resolve", "physical_resistance", 2974.0, "minor provider", "skill")

    result = optimize_prescribed_roster_candidates(
        roster=_two_dd_roster(),
        candidate_pools={
            "DD 1": (
                _evidence("dd1-major", effects=(major,)),
                _evidence("dd1-none"),
            ),
            "DD 2": (
                _evidence("dd2-duplicate-major", effects=(major,)),
                _evidence("dd2-new-minor", effects=(minor,)),
            ),
        },
    )

    assert result.applied_count == 2
    assert result.final_roster.assignments[0].source_build_name == "dd1-major Build"
    assert result.final_roster.assignments[1].source_build_name == "dd2-new-minor Build"
    second_values = dict(result.slots[1].ranking.provider_marginal_values)
    assert second_values["dd2-duplicate-major"].new_named_effect_count == 0
    assert second_values["dd2-new-minor"].new_named_effect_count == 1
