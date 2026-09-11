from types import SimpleNamespace

from minmax.effects import Effect, EffectOperation
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_resource_candidate_runtime_condition_service import (
    ExtremeResourceCandidateRuntimeConditionService,
)
from services.extreme_resource_conditioned_context_factory import (
    ExtremeResourceConditionedGearStatInputResolver,
)
from services.extreme_resource_runtime_condition_state_service import (
    ExtremeResourceRuntimeConditionState,
)
from services.extreme_resource_runtime_coverage_audit_service import (
    ExtremeResourceRuntimeConditionEvidence,
    ExtremeResourceRuntimeCoverageAudit,
)
from services.extreme_resource_runtime_skill_witness_materialization_service import (
    ExtremeResourceRuntimeSkillWitnessMaterialization,
)


class _UnusedRepository:
    pass


class _ConditionalEffects:
    def active_static_effects(self, counts, *, condition_context=None, use_max_value=True):
        if "food_buff_active" not in (condition_context or frozenset()):
            return []
        return [
            Effect(
                stat=StatId.MAX_HEALTH,
                operation=EffectOperation.ADD,
                value=2500.0,
                source="Green Pact (5)",
                condition="food_buff_active",
            )
        ]


def _green_pact_build():
    return PlayerBuild(
        Armor={
            "Head": {"Set": "Green Pact"},
            "Chest": {"Set": "Green Pact"},
            "Shoulders": {"Set": "Green Pact"},
            "Hands": {"Set": "Green Pact"},
            "Waist": {"Set": "Green Pact"},
        }
    )


def test_conditioned_gear_resolver_requires_exact_semantic_condition_marker():
    resolver = ExtremeResourceConditionedGearStatInputResolver(_UnusedRepository())
    resolver.service = _ConditionalEffects()
    build = _green_pact_build()

    inactive = resolver.resolve(build, condition_context=frozenset())
    active = resolver.resolve(
        build,
        condition_context=frozenset({"food_buff_active"}),
    )

    assert inactive.health.set_flat == 0.0
    assert active.health.set_flat == 2500.0


class _Audit:
    def build(self, objective_key):
        return ExtremeResourceRuntimeCoverageAudit(
            objective_key=objective_key,
            contextual_passives_reviewed=("reviewed",),
            conditional_gear_effects=(
                ExtremeResourceRuntimeConditionEvidence(
                    set_id=1,
                    set_name="Armor Master",
                    piece_count=5,
                    condition="armor_ability_slotted",
                    stat="max_health",
                    value=5.0,
                    source="Armor Master (5)",
                ),
            ),
            condition_markers=("armor_ability_slotted",),
            denominator_proven=True,
            unresolved=(),
        )


class _OrdinaryConditions:
    def build(self, objective_key, *, required_conditions, build, active_bar="front", food=""):
        assert required_conditions == ()
        return ExtremeResourceRuntimeConditionState(
            objective_key=objective_key,
            required_conditions=(),
            active_conditions=(),
        )


class _SkillWitnesses:
    def materialize(self, *, build, route, required_conditions, active_bar="front"):
        assert required_conditions == ("armor_ability_slotted",)
        result = PlayerBuild.from_dict(build.to_dict())
        result.FrontBarSkills = ["Annulment"]
        return ExtremeResourceRuntimeSkillWitnessMaterialization(
            build=result,
            requested_conditions=required_conditions,
            active_conditions=required_conditions,
            witnesses=(("armor_ability_slotted", "Annulment"),),
        )


def test_candidate_projection_merges_materialized_skill_witness_into_condition_context():
    service = ExtremeResourceCandidateRuntimeConditionService(
        coverage_audit_service=_Audit(),
        condition_state_service=_OrdinaryConditions(),
        skill_witness_materialization_service=_SkillWitnesses(),
    )
    build = PlayerBuild(
        Armor={
            "Head": {"Set": "Armor Master"},
            "Chest": {"Set": "Armor Master"},
            "Shoulders": {"Set": "Armor Master"},
            "Hands": {"Set": "Armor Master"},
            "Waist": {"Set": "Armor Master"},
        }
    )

    result = service.build(
        "max_health",
        build=build,
        route=SimpleNamespace(equipped_skill_lines=("Green Balance",)),
    )

    assert result.projection_complete is True
    assert result.condition_context == frozenset({"armor_ability_slotted"})
    assert result.build.FrontBarSkills == ["Annulment"]
    assert result.state.evidence == (
        "armor_ability_slotted: canonical skill witness Annulment",
    )
