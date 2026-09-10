from types import SimpleNamespace

import pytest

from minmax.build_evaluation import BuildEvaluation
from minmax.calculation import CalculationResult, StatBreakdown
from minmax.character_build.bar import Bar
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.character_class import CharacterClass
from minmax.character_build.effect_layer import BarId
from minmax.character_build.slotted_skill import SlottedSkill
from minmax.character_build.weapon import Weapon
from minmax.character_build.weapon_type import WeaponType
from minmax.resource_costs import ResourceType
from minmax.role import Role
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.stat_ids import StatId
from services.rotation_candidate_action_damage_evidence_service import (
    RotationCandidateActionDamageEvidenceService,
)
from services.rotation_candidate_canonical_plan_evidence_service import (
    RotationCandidateCanonicalPlanEvidenceService,
)
from services.rotation_candidate_dd_role_output_service import RotationCandidateDDRoleOutputService
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_heavy_attack_damage_evidence_service import (
    RotationCandidateHeavyAttackDamageEvidenceService,
)
from services.rotation_candidate_heavy_attack_restoration_plan_evidence_service import (
    RotationCandidateHeavyAttackRestorationPlanEvidenceService,
)
from services.rotation_candidate_recommendation_evidence_service import (
    RotationCandidateRecommendationEvidenceService,
)
from services.rotation_candidate_recommendation_service import RotationCandidateRecommendationService
from services.rotation_candidate_scorecard_service import RotationCandidateScorecard
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)
from services.rotation_plan_consequence_service import (
    RotationPlanConsequence,
    RotationResourceConsequenceKind,
)


def _slots() -> tuple[SlottedSkill, ...]:
    return tuple(
        SlottedSkill(
            skill_id=f"dummy_{index}",
            skill_line_id="fighters_guild",
            is_ultimate=index == 5,
        )
        for index in range(6)
    )


def _canonical_build() -> CharacterBuild:
    return CharacterBuild(
        name="HA DD",
        character_class=CharacterClass.WARDEN,
        role=Role.DD,
        front_bar=Bar(
            bar_id=BarId.FRONT,
            main_hand=Weapon(WeaponType.FLAME_STAFF),
            off_hand=None,
            slots=_slots(),
        ),
        back_bar=None,
    )


def _evaluation() -> BuildEvaluation:
    return BuildEvaluation(
        stats=CalculationResult(
            stats={
                StatId.MAX_MAGICKA: StatBreakdown(base=30000.0),
                StatId.MAX_STAMINA: StatBreakdown(base=15000.0),
                StatId.SPELL_DAMAGE: StatBreakdown(base=5000.0),
                StatId.WEAPON_DAMAGE: StatBreakdown(base=4000.0),
                StatId.PHYSICAL_PENETRATION: StatBreakdown(base=0.0),
                StatId.SPELL_PENETRATION: StatBreakdown(base=0.0),
                StatId.CRITICAL_CHANCE: StatBreakdown(base=0.0),
                StatId.CRITICAL_DAMAGE: StatBreakdown(base=0.0),
            }
        ),
        combat_effects=(),
        combat_contributions=(),
    )


def _candidate(candidate_id: str, actions=()) -> GeneratedRotationCandidate:
    return GeneratedRotationCandidate(
        candidate_id=candidate_id,
        plan=RotationPlan(
            character_name="Damage Tester",
            build_name="HA DD",
            duration_seconds=10.0,
            actions=tuple(actions),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _SustainService:
    """Deterministic harness proving candidate restoration reaches sustain input."""

    def __init__(self):
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        restored = sum(float(event.amount) for event in kwargs["restoration_events"])
        minimum = 1000.0 + restored
        return SimpleNamespace(
            run=SimpleNamespace(
                sustain=SimpleNamespace(
                    minimum_amount=minimum,
                    ending_margin=minimum,
                    sustains=True,
                )
            ),
            unresolved=(),
        )


class _DurationService:
    def analyze(self, plan, **kwargs):
        return object()


class _WorkloadProvider:
    def evaluate_plan(self, candidate):
        return SimpleNamespace(
            alternative_id=candidate.candidate_id,
            viable=True,
            primary_role_displacement_seconds=0.0,
        )


class _ScorecardService:
    """Keep this integration focused on evidence composition and role ranking."""

    def compare(self, **kwargs):
        return RotationCandidateScorecard(
            consequence=RotationPlanConsequence(
                resource_kind=RotationResourceConsequenceKind.NEUTRAL,
                cast_deltas=(),
                cost_deltas=(),
                total_cost_delta=0,
                minimum_resource_delta=0,
                ending_resource_delta=0,
                shortfall_delta=0,
                wait_delta=0,
            ),
            demand_coverage=(),
            missing_required_effects=(),
            candidate_shortfall=0,
            inherited_unresolved=(),
            candidate_specific_unresolved=(),
        )


def test_same_heavy_attack_contributes_damage_and_restoration_to_recommendation() -> None:
    heavy_action = RotationAction(
        0.0,
        0,
        RotationActionKind.HEAVY_ATTACK,
        bar="front",
    )
    baseline = _candidate("baseline")
    heavy = _candidate("heavy", (heavy_action,))
    completion = RotationHeavyAttackCompletionEvidence(
        action_time_seconds=0.0,
        action_sequence=0,
        completion_time_seconds=2.0,
        fully_charged=True,
        verified_base_restore=3000.0,
        source="integration verified HA completion",
    )
    canonical_build = _canonical_build()

    heavy_damage = RotationCandidateHeavyAttackDamageEvidenceService(
        build=canonical_build,
        evaluation=_evaluation(),
        initial_bar="front",
        completion_evidence=(completion,),
    )
    role_output = RotationCandidateDDRoleOutputService(
        action_damage_evidence_provider=RotationCandidateActionDamageEvidenceService(
            heavy_attack_provider=heavy_damage,
        )
    )

    def completion_for(candidate):
        return (completion,) if candidate.candidate_id == "heavy" else ()

    restoration = RotationCandidateHeavyAttackRestorationPlanEvidenceService(
        build=canonical_build,
        initial_bar="front",
        completion_evidence_resolver=completion_for,
    )
    sustain = _SustainService()
    plan_evidence = RotationCandidateCanonicalPlanEvidenceService(
        build=object(),
        sustain_service=sustain,
        duration_service=_DurationService(),
        role_output_evidence_provider=role_output,
        restoration_evidence_provider=restoration,
        provider_workload_evidence_provider=_WorkloadProvider(),
        resource=ResourceType.MAGICKA,
    )
    recommendation_evidence = RotationCandidateRecommendationEvidenceService(
        plan_evidence_provider=plan_evidence,
        scorecard_service=_ScorecardService(),
    )

    result = RotationCandidateRecommendationService().recommend(
        candidates=(baseline, heavy),
        evidence_provider=recommendation_evidence,
        role_key="dd",
        role_output_label="effective damage",
        assigned_support_label="assigned support",
    )

    assert result.recommended is not None
    assert result.recommended.candidate.candidate_id == "heavy"

    entries = {entry.candidate.candidate_id: entry for entry in result.entries}
    assert entries["baseline"].evidence.role_output_value == 0.0
    assert entries["baseline"].evidence.sustain_margin == 1000.0
    assert entries["heavy"].evidence.role_output_value == pytest.approx(589.2)
    assert entries["heavy"].evidence.sustain_margin == 4000.0

    assert sustain.calls[0]["restoration_events"] == ()
    assert len(sustain.calls[1]["restoration_events"]) == 1
    restored = sustain.calls[1]["restoration_events"][0]
    assert restored.time_seconds == 2.0
    assert restored.resource is ResourceType.MAGICKA
    assert restored.amount == pytest.approx(3000.0)
