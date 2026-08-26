from minmax.coverage_recommendation import RecommendationAction
from minmax.coverage_requirement import CoverageRequirement
from minmax.encounter_evaluation import EncounterEvaluator
from minmax.encounter_requirements import EncounterRequirementSet
from minmax.role import Role
from minmax.roster_coverage import RosterCapabilityProvider
from minmax.support_effect import SupportEffect
from minmax.support_effect_category import SupportEffectCategory
from minmax.support_target_type import SupportTargetType


def _provider(name: str, effect_name: str) -> RosterCapabilityProvider:
    return RosterCapabilityProvider(
        character_name=name,
        role=Role.HEALER,
        effect=SupportEffect(
            source="Test Source",
            name=effect_name,
            category=SupportEffectCategory.BUFF,
            effect_type=effect_name,
            target_type=SupportTargetType.GROUP,
        ),
    )


def _requirements(*names: str) -> EncounterRequirementSet:
    return EncounterRequirementSet(
        encounter_id="test-encounter",
        encounter_name="Test Encounter",
        requirements=tuple(
            CoverageRequirement(effect_name=name)
            for name in names
        ),
    )


def test_missing_requirement_produces_add_provider_intent():
    evaluation = EncounterEvaluator().evaluate(
        _requirements("major_courage"),
        {},
    )

    recommendation = evaluation.recommendation_for_effect("major_courage")

    assert recommendation is not None
    assert recommendation.action == RecommendationAction.ADD_PROVIDER
    assert recommendation.valid_provider_count == 0
    assert evaluation.actionable_recommendations == (recommendation,)


def test_covered_requirement_produces_no_action_intent():
    evaluation = EncounterEvaluator().evaluate(
        _requirements("major_courage"),
        {
            "major_courage": (
                _provider("Healer One", "major_courage"),
            ),
        },
    )

    recommendation = evaluation.recommendation_for_effect("major_courage")

    assert recommendation is not None
    assert recommendation.action == RecommendationAction.NO_ACTION
    assert evaluation.actionable_recommendations == ()


def test_insufficient_requirement_produces_follow_up_intent():
    requirements = EncounterRequirementSet(
        encounter_id="test-encounter",
        encounter_name="Test Encounter",
        requirements=(
            CoverageRequirement(
                effect_name="major_courage",
                required_provider_count=2,
            ),
        ),
    )

    evaluation = EncounterEvaluator().evaluate(
        requirements,
        {
            "major_courage": (
                _provider("Healer One", "major_courage"),
            ),
        },
    )

    recommendation = evaluation.recommendation_for_effect("major_courage")

    assert recommendation is not None
    assert recommendation.action == RecommendationAction.INCREASE_UPTIME
    assert recommendation.valid_provider_count == 1
