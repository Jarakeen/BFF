from services.extreme_gear_set_bonus_breakpoint_service import ExtremeGearSetBonusBreakpointCatalog
from services.extreme_gear_set_objective_relevance_service import ExtremeGearSetObjectiveRelevanceCatalog
from services.extreme_max_resource_joint_feasibility_search_service import ExtremeMaxResourceJointFeasibilitySearchService
from services.extreme_max_resource_named_gear_candidate_search_service import ExtremeMaxResourceNamedGearCandidateSearchService
from services.extreme_max_resource_semantic_memo_search_service import ExtremeMaxResourceSemanticMemoSearchService
from services.extreme_named_gear_set_slot_eligibility_service import ExtremeNamedGearSetSlotEligibilityCatalog


def _ordinary(objective: str) -> ExtremeMaxResourceJointFeasibilitySearchService:
    return ExtremeMaxResourceJointFeasibilitySearchService(
        breakpoints=ExtremeGearSetBonusBreakpointCatalog(sets=()),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(sets=()),
        relevance=ExtremeGearSetObjectiveRelevanceCatalog(objective_key=objective, evidence=()),
    )


def test_magicka_candidate_search_promotes_joint_search_to_semantic_memo() -> None:
    service = ExtremeMaxResourceNamedGearCandidateSearchService(
        ordinary_service=_ordinary("max_magicka"),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(sets=()),
    )
    assert isinstance(service.ordinary_service, ExtremeMaxResourceSemanticMemoSearchService)


def test_stamina_candidate_search_promotes_joint_search_to_semantic_memo() -> None:
    service = ExtremeMaxResourceNamedGearCandidateSearchService(
        ordinary_service=_ordinary("max_stamina"),
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(sets=()),
    )
    assert isinstance(service.ordinary_service, ExtremeMaxResourceSemanticMemoSearchService)


def test_health_candidate_search_keeps_existing_joint_search() -> None:
    ordinary = _ordinary("max_health")
    service = ExtremeMaxResourceNamedGearCandidateSearchService(
        ordinary_service=ordinary,
        eligibility=ExtremeNamedGearSetSlotEligibilityCatalog(sets=()),
    )
    assert service.ordinary_service is ordinary
    assert not isinstance(service.ordinary_service, ExtremeMaxResourceSemanticMemoSearchService)
