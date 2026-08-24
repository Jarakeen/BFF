from __future__ import annotations

from minmax.coverage_classification import CoverageClassification
from minmax.coverage_requirement import CoverageRequirement
from minmax.encounter_evaluation import EncounterEvaluator
from minmax.encounter_requirements import EncounterRequirementSet
from minmax.role import Role
from minmax.roster_coverage import RosterCapabilityProvider
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_stacking import StackingBehavior
from minmax.support_target_type import SupportTargetType


def _effect(
    name: str,
    *,
    uptime: float = 1.0,
    exclusivity_group: str | None = None,
) -> SupportEffect:
    return SupportEffect(
        source="Test Source",
        name=name,
        category=SupportEffectCategory.BUFF,
        effect_type=name,
        target_type=SupportTargetType.GROUP,
        uptime=uptime,
        stacking=StackingBehavior.UNIQUE,
        exclusivity_group=exclusivity_group,
    )


def _provider(
    character_name: str,
    effect: SupportEffect,
) -> RosterCapabilityProvider:
    return RosterCapabilityProvider(
        character_name=character_name,
        role=Role.HEALER,
        effect=effect,
    )


def _requirement_set(
    *requirements: CoverageRequirement,
) -> EncounterRequirementSet:
    return EncounterRequirementSet(
        encounter_id="test_encounter",
        encounter_name="Test Encounter",
        requirements=requirements,
    )


def test_all_active_requirements_are_covered():
    requirements = _requirement_set(
        CoverageRequirement(effect_name="major_courage"),
        CoverageRequirement(effect_name="major_force"),
    )

    capabilities = {
        "major_courage": (
            _provider("Healer One", _effect("major_courage")),
        ),
        "major_force": (
            _provider("Healer Two", _effect("major_force")),
        ),
    }

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        capabilities,
    )

    assert len(evaluation.classifications) == 2
    assert evaluation.inactive_requirements == ()
    assert evaluation.problems == ()
    assert evaluation.is_fully_covered

    assert (
        evaluation.classification_for_effect("major_courage").classification
        == CoverageClassification.COVERED
    )
    assert (
        evaluation.classification_for_effect("major_force").classification
        == CoverageClassification.COVERED
    )


def test_missing_requirement_is_reported():
    requirements = _requirement_set(
        CoverageRequirement(effect_name="major_slayer"),
    )

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        {},
    )

    result = evaluation.classification_for_effect("major_slayer")

    assert result is not None
    assert result.classification == CoverageClassification.MISSING
    assert evaluation.is_fully_covered is False
    assert evaluation.problems == (result,)


def test_insufficient_requirement_is_reported():
    requirements = _requirement_set(
        CoverageRequirement(
            effect_name="major_courage",
            required_provider_count=2,
        ),
    )

    capabilities = {
        "major_courage": (
            _provider("Healer One", _effect("major_courage")),
        ),
    }

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        capabilities,
    )

    result = evaluation.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.INSUFFICIENT
    assert result.required_provider_count == 2
    assert result.valid_provider_count == 1
    assert evaluation.is_fully_covered is False


def test_redundant_provider_is_preserved():
    requirements = _requirement_set(
        CoverageRequirement(effect_name="major_courage"),
    )

    capabilities = {
        "major_courage": (
            _provider("Healer One", _effect("major_courage")),
            _provider("Healer Two", _effect("major_courage")),
        ),
    }

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        capabilities,
    )

    result = evaluation.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.REDUNDANT
    assert result.redundant_providers == ("Healer Two",)
    assert evaluation.is_fully_covered


def test_exclusivity_is_promoted_to_conflict():
    requirements = _requirement_set(
        CoverageRequirement(effect_name="major_courage"),
    )

    capabilities = {
        "major_courage": (
            _provider(
                "Healer One",
                _effect(
                    "major_courage",
                    exclusivity_group="major_courage",
                ),
            ),
            _provider(
                "Healer Two",
                _effect(
                    "major_courage",
                    exclusivity_group="major_courage",
                ),
            ),
        ),
    }

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        capabilities,
    )

    result = evaluation.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.CONFLICT
    assert result.conflicting_providers == (
        "Healer One",
        "Healer Two",
    )
    assert evaluation.is_fully_covered is False


def test_unmet_requirement_condition_makes_requirement_inactive():
    requirements = _requirement_set(
        CoverageRequirement(
            effect_name="major_force",
            condition="execute_phase",
        ),
    )

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        {},
        condition_context=frozenset({"portal_phase"}),
    )

    assert evaluation.classifications == ()
    assert evaluation.inactive_requirements == requirements.all()
    assert evaluation.problems == ()
    assert evaluation.is_fully_covered


def test_satisfied_requirement_condition_activates_requirement():
    requirements = _requirement_set(
        CoverageRequirement(
            effect_name="major_force",
            condition="execute_phase",
        ),
    )

    capabilities = {
        "major_force": (
            _provider("Healer One", _effect("major_force")),
        ),
    }

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        capabilities,
        condition_context=frozenset({"execute_phase"}),
    )

    result = evaluation.classification_for_effect("major_force")

    assert result is not None
    assert result.classification == CoverageClassification.COVERED
    assert evaluation.inactive_requirements == ()
    assert evaluation.is_fully_covered


def test_none_condition_context_preserves_default_no_gating_behavior():
    requirements = _requirement_set(
        CoverageRequirement(
            effect_name="major_force",
            condition="execute_phase",
        ),
    )

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        {},
        condition_context=None,
    )

    result = evaluation.classification_for_effect("major_force")

    assert result is not None
    assert result.classification == CoverageClassification.MISSING
    assert evaluation.inactive_requirements == ()


def test_unconditional_requirement_is_always_active():
    requirements = _requirement_set(
        CoverageRequirement(effect_name="major_courage"),
    )

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        {},
        condition_context=frozenset({"execute_phase"}),
    )

    result = evaluation.classification_for_effect("major_courage")

    assert result is not None
    assert result.classification == CoverageClassification.MISSING
    assert evaluation.inactive_requirements == ()


def test_multiple_requirement_conditions_are_independently_gated():
    requirements = _requirement_set(
        CoverageRequirement(
            effect_name="major_force",
            condition="execute_phase",
        ),
        CoverageRequirement(
            effect_name="major_slayer",
            condition="execute_phase",
        ),
        CoverageRequirement(
            effect_name="major_courage",
            condition="burn_phase",
        ),
    )

    capabilities = {
        "major_force": (
            _provider("Healer One", _effect("major_force")),
        ),
        "major_slayer": (
            _provider("Healer Two", _effect("major_slayer")),
        ),
        "major_courage": (
            _provider("Healer Three", _effect("major_courage")),
        ),
    }

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        capabilities,
        condition_context=frozenset({"execute_phase"}),
    )

    assert evaluation.classification_for_effect("major_force") is not None
    assert evaluation.classification_for_effect("major_slayer") is not None
    assert evaluation.classification_for_effect("major_courage") is None

    assert evaluation.inactive_requirements == (
        requirements.for_effect("major_courage"),
    )

    assert evaluation.is_fully_covered


def test_intermediate_coverage_evidence_is_preserved():
    requirements = _requirement_set(
        CoverageRequirement(effect_name="major_courage"),
    )

    provider = _provider(
        "Healer One",
        _effect("major_courage"),
    )

    capabilities = {
        "major_courage": (provider,),
    }

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        capabilities,
    )

    gap = evaluation.coverage_analysis.for_effect("major_courage")

    assert gap is not None
    assert gap.provider_evidence == (
        evaluation.coverage_analysis.for_effect(
            "major_courage"
        ).provider_evidence
    )
    assert gap.provider_evidence[0].character_name == "Healer One"
    assert gap.provider_evidence[0].effect == provider.effect


def test_evaluation_preserves_encounter_identity():
    requirements = _requirement_set(
        CoverageRequirement(effect_name="major_courage"),
    )

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        {},
    )

    assert evaluation.requirement_set.encounter_id == "test_encounter"
    assert evaluation.requirement_set.encounter_name == "Test Encounter"


def test_minimum_uptime_flows_through_encounter_evaluation():
    requirements = _requirement_set(
        CoverageRequirement(
            effect_name="major_force",
            minimum_uptime=0.80,
        ),
    )

    capabilities = {
        "major_force": (
            _provider(
                "Healer One",
                _effect(
                    "major_force",
                    uptime=0.79,
                ),
            ),
        ),
    }

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        capabilities,
    )

    result = evaluation.classification_for_effect("major_force")

    assert result is not None
    assert result.classification == CoverageClassification.INSUFFICIENT
    assert evaluation.is_fully_covered is False