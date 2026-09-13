from __future__ import annotations

from types import SimpleNamespace

from minmax.combat_state_snapshot import CombatStateSnapshot, CombatantSnapshot
from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequenceType,
)
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteComponentEvidence,
)
from services.rotation_execute_filler_opportunity_service import (
    RotationExecuteFillerOpportunityService,
)


class _Evidence:
    def __init__(self, by_name):
        self.by_name = by_name

    def resolve(self, skill_name: str):
        return self.by_name.get(
            skill_name,
            RotationExecuteCandidateEvidence(
                requested_skill_name=skill_name,
                resolved_skill_name=skill_name,
                entity_id=skill_name.casefold().replace(" ", "_"),
            ),
        )


def _candidate(name="Execute", threshold=0.25):
    return RotationExecuteCandidateEvidence(
        requested_skill_name=name,
        resolved_skill_name=name,
        entity_id=name.casefold().replace(" ", "_"),
        components=(
            RotationExecuteComponentEvidence(
                skill_name=name,
                entity_id=name.casefold().replace(" ", "_"),
                skill_rank_id=10,
                coefficient_number=1,
                threshold=threshold,
                consequence_type=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
                maximum_bonus_fraction=3.0,
                condition_evidence="below 25% target Health",
                consequence_evidence="up to 300% more damage",
            ),
        ),
    )


def _priorities():
    return AbilityPriorityList(
        character_name="Test",
        build_name="DD",
        role="DD",
        entries=(
            AbilityPriorityEntry("front", 1, "Filler", 1),
            AbilityPriorityEntry("front", 2, "Execute", 10),
            AbilityPriorityEntry("front", 3, "Dot", 2),
        ),
    )


def _plan(skill="Filler"):
    return RotationPlan(
        character_name="Test",
        build_name="DD",
        duration_seconds=10.0,
        actions=(
            RotationAction(
                time_seconds=5.0,
                sequence=1,
                kind=RotationActionKind.SKILL,
                name=skill,
                bar="front",
            ),
        ),
    )


def _snapshot(health):
    return CombatStateSnapshot(
        time_seconds=5.0,
        player=CombatantSnapshot("player", 100, 100),
        targets=(CombatantSnapshot("boss", health, 100),),
    )


def test_active_same_bar_no_duration_execute_is_exposed_as_comparison_opportunity() -> None:
    service = RotationExecuteFillerOpportunityService(
        evidence_service=_Evidence({"Execute": _candidate()}),
    )

    result = service.find(
        _plan(),
        priorities=_priorities(),
        snapshot_resolver=lambda _: _snapshot(20),
        target_identity="boss",
    )

    assert len(result.opportunities) == 1
    row = result.opportunities[0]
    assert row.time_seconds == 5.0
    assert row.current_skill_name == "Filler"
    assert row.execute_skill_name == "Execute"
    assert row.current_priority == 1
    assert row.execute_priority == 10
    assert row.active_thresholds == (0.25,)


def test_inactive_execute_produces_no_opportunity() -> None:
    service = RotationExecuteFillerOpportunityService(
        evidence_service=_Evidence({"Execute": _candidate()}),
    )

    result = service.find(
        _plan(),
        priorities=_priorities(),
        snapshot_resolver=lambda _: _snapshot(40),
        target_identity="boss",
    )

    assert result.opportunities == ()


def test_duration_bearing_current_skill_is_not_treated_as_filler() -> None:
    service = RotationExecuteFillerOpportunityService(
        evidence_service=_Evidence({"Execute": _candidate()}),
    )

    result = service.find(
        _plan("Dot"),
        priorities=_priorities(),
        duration_rules=(RotationRecastRule("Dot", 10.0, bar="front"),),
        snapshot_resolver=lambda _: _snapshot(20),
        target_identity="boss",
    )

    assert result.opportunities == ()


def test_duration_bearing_execute_candidate_is_excluded_from_first_policy_slice() -> None:
    service = RotationExecuteFillerOpportunityService(
        evidence_service=_Evidence({"Execute": _candidate()}),
    )

    result = service.find(
        _plan(),
        priorities=_priorities(),
        duration_rules=(RotationRecastRule("Execute", 10.0, bar="front"),),
        snapshot_resolver=lambda _: _snapshot(20),
        target_identity="boss",
    )

    assert result.opportunities == ()


def test_missing_runtime_snapshot_fails_closed_without_opportunity() -> None:
    service = RotationExecuteFillerOpportunityService(
        evidence_service=_Evidence({"Execute": _candidate()}),
    )

    result = service.find(
        _plan(),
        priorities=_priorities(),
        snapshot_resolver=lambda _: None,
        target_identity="boss",
    )

    assert result.opportunities == ()
    assert result.unresolved == ("execute runtime snapshot is unavailable at 5s",)


def test_no_positive_execute_evidence_leaves_plan_without_execute_opportunity() -> None:
    service = RotationExecuteFillerOpportunityService(evidence_service=_Evidence({}))

    result = service.find(
        _plan(),
        priorities=_priorities(),
        snapshot_resolver=lambda _: _snapshot(20),
        target_identity="boss",
    )

    assert result.opportunities == ()
