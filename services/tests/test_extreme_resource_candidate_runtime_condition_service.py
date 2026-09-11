from models.build_model import GearSlot, PlayerBuild
from services.extreme_resource_candidate_runtime_condition_service import (
    ExtremeResourceCandidateRuntimeConditionService,
)
from services.extreme_resource_runtime_condition_state_service import (
    ExtremeResourceRuntimeConditionState,
)
from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeConditionEvidence,
    ExtremeResourceRuntimeCoverageAudit,
)


class _AuditService:
    def __init__(self, *, denominator_proven=True):
        self.denominator_proven = denominator_proven

    def build(self, objective_key):
        return ExtremeResourceRuntimeCoverageAudit(
            objective_key=objective_key,
            contextual_passives_reviewed=("reviewed",),
            conditional_gear_effects=(
                ExtremeResourceRuntimeConditionEvidence(
                    set_id=1,
                    set_name="Green Pact",
                    piece_count=5,
                    condition="food_buff_active",
                    stat="max_health",
                    value=2500.0,
                    source="Green Pact (5)",
                ),
                ExtremeResourceRuntimeConditionEvidence(
                    set_id=2,
                    set_name="Death Dealer's Fete",
                    piece_count=1,
                    condition="escalating_fete_stacks:30",
                    stat="max_health",
                    value=2640.0,
                    source="Death Dealer's Fete (1)",
                ),
            ),
            condition_markers=("escalating_fete_stacks:30", "food_buff_active"),
            denominator_proven=self.denominator_proven,
            unresolved=(),
        )


class _ConditionService:
    def __init__(self):
        self.required = ()

    def build(self, objective_key, *, required_conditions, build, active_bar="front", food=""):
        self.required = tuple(required_conditions)
        return ExtremeResourceRuntimeConditionState(
            objective_key=objective_key,
            required_conditions=tuple(required_conditions),
            active_conditions=tuple(required_conditions),
        )


def _five_piece(name):
    return {
        "Head": {"Set": name},
        "Chest": {"Set": name},
        "Shoulders": {"Set": name},
        "Hands": {"Set": name},
        "Waist": {"Set": name},
    }


def test_candidate_only_requires_conditions_from_equipped_active_sets():
    condition_service = _ConditionService()
    service = ExtremeResourceCandidateRuntimeConditionService(
        coverage_audit_service=_AuditService(),
        condition_state_service=condition_service,
    )
    build = PlayerBuild(Armor=_five_piece("Green Pact"))

    result = service.build("max_health", build=build, food="some food")

    assert result.required_conditions == ("food_buff_active",)
    assert condition_service.required == ("food_buff_active",)
    assert [row.set_name for row in result.candidate_effects] == ["Green Pact"]
    assert result.projection_complete is True


def test_one_piece_mythic_condition_is_projected_when_equipped():
    condition_service = _ConditionService()
    service = ExtremeResourceCandidateRuntimeConditionService(
        coverage_audit_service=_AuditService(),
        condition_state_service=condition_service,
    )
    build = PlayerBuild(Ring1=GearSlot(Set="Death Dealer's Fete"))

    result = service.build("max_health", build=build)

    assert result.required_conditions == ("escalating_fete_stacks:30",)
    assert [row.set_name for row in result.candidate_effects] == ["Death Dealer's Fete"]
    assert result.projection_complete is True


def test_unrelated_runtime_conditions_do_not_block_candidate():
    condition_service = _ConditionService()
    service = ExtremeResourceCandidateRuntimeConditionService(
        coverage_audit_service=_AuditService(),
        condition_state_service=condition_service,
    )

    result = service.build("max_health", build=PlayerBuild())

    assert result.required_conditions == ()
    assert result.candidate_effects == ()
    assert result.projection_complete is True


def test_global_runtime_denominator_still_fails_closed():
    service = ExtremeResourceCandidateRuntimeConditionService(
        coverage_audit_service=_AuditService(denominator_proven=False),
        condition_state_service=_ConditionService(),
    )

    result = service.build("max_health", build=PlayerBuild())

    assert result.projection_complete is False
    assert any("denominator is not proven" in item for item in result.unresolved)
