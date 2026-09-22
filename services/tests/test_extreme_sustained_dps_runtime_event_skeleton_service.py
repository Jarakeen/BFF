from __future__ import annotations

from types import SimpleNamespace

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.runtime_event import RuntimeEvent
from services.extreme_sustained_dps_runtime_event_skeleton_service import (
    ExtremeSustainedDPSRuntimeEventSkeletonService,
)
from services.rotation_candidate_dd_role_output_service import (
    RotationActionDamageOccurrence,
    RotationActionDamageOccurrenceEvidence,
)
from services.rotation_candidate_generation_service import GeneratedRotationCandidate


def _effect(name, trigger):
    return EffectVariant(
        name=name,
        layer=EffectLayer.PROC,
        source=name,
        trigger=trigger,
        duration=5.0,
    )


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="candidate",
        plan=RotationPlan(
            character_name="Generated",
            build_name="Candidate",
            duration_seconds=10.0,
            actions=(
                RotationAction(1.0, 0, RotationActionKind.SKILL, "Skill A", "front"),
                RotationAction(2.0, 0, RotationActionKind.LIGHT_ATTACK, "LA", "front"),
                RotationAction(3.0, 0, RotationActionKind.ULTIMATE, "Ultimate A", "front"),
            ),
        ),
        refresh_leads=(),
        action_claims=(),
    )


class _Occurrences:
    def evaluate_action_occurrences(self, *, candidate, action):
        if action.kind is RotationActionKind.SKILL:
            rows = (
                RotationActionDamageOccurrence(
                    time_seconds=1.0,
                    sequence=0,
                    damage_value=100.0,
                    source_name="Skill A direct",
                ),
                RotationActionDamageOccurrence(
                    time_seconds=4.0,
                    sequence=0,
                    damage_value=50.0,
                    source_name="Skill A tick",
                ),
            )
        else:
            rows = ()
        return RotationActionDamageOccurrenceEvidence(
            action_time_seconds=action.time_seconds,
            action_sequence=action.sequence,
            occurrences=rows,
        )


def test_plan_owned_cast_ultimate_and_light_attack_triggers_are_derived() -> None:
    result = ExtremeSustainedDPSRuntimeEventSkeletonService.build(
        candidate=_candidate(),
        effects=(
            _effect("cast-proc", "cast"),
            _effect("ultimate-proc", "ultimate_activation_in_combat"),
            _effect("la-proc", "light_attack"),
        ),
    )

    assert result.denominator_proven is True
    assert tuple((row.time_seconds, row.trigger) for row in result.events) == (
        (1.0, "cast"),
        (2.0, "light_attack"),
        (3.0, "ultimate_activation_in_combat"),
    )


def test_damage_dealt_uses_exact_occurrence_evidence() -> None:
    result = ExtremeSustainedDPSRuntimeEventSkeletonService.build(
        candidate=_candidate(),
        effects=(_effect("damage-proc", "damage_dealt"),),
        occurrence_provider=_Occurrences(),
        target_identity="Boss",
    )

    assert result.denominator_proven is True
    assert tuple((row.time_seconds, row.source, row.target) for row in result.events) == (
        (1.0, "Skill A direct", "Boss"),
        (4.0, "Skill A tick", "Boss"),
    )


def test_potion_use_is_excluded_from_runtime_state_skeletons() -> None:
    result = ExtremeSustainedDPSRuntimeEventSkeletonService.build(
        candidate=_candidate(),
        effects=(_effect("potion-proc", "potion_use"),),
    )

    assert result.denominator_proven is True
    assert result.events == ()
    assert result.excluded_plan_owned_triggers == ("potion_use",)


def test_scenario_owned_trigger_requires_proven_supplemental_family() -> None:
    result = ExtremeSustainedDPSRuntimeEventSkeletonService.build(
        candidate=_candidate(),
        effects=(_effect("truth-proc", "damage_off_balance_target"),),
        supplemental_events=(
            RuntimeEvent(
                time_seconds=5.0,
                trigger="damage_off_balance_target",
                source="Reviewed off-balance hit",
                target="Boss",
            ),
        ),
        supplemental_denominator_proven=False,
        source="partial encounter review",
    )

    assert result.denominator_proven is False
    assert any("not proven complete" in row for row in result.unresolved)


def test_proven_scenario_trigger_family_closes_event_skeleton_denominator() -> None:
    result = ExtremeSustainedDPSRuntimeEventSkeletonService.build(
        candidate=_candidate(),
        effects=(_effect("truth-proc", "damage_off_balance_target"),),
        supplemental_events=(
            RuntimeEvent(
                time_seconds=5.0,
                trigger="damage_off_balance_target",
                source="Reviewed off-balance hit",
                target="Boss",
            ),
        ),
        supplemental_denominator_proven=True,
        source="reviewed encounter family",
    )

    assert result.denominator_proven is True
    assert result.scenario_triggers == ("damage_off_balance_target",)
    assert len(result.events) == 1


def test_expected_value_damage_does_not_invent_critical_damage_events() -> None:
    result = ExtremeSustainedDPSRuntimeEventSkeletonService.build(
        candidate=_candidate(),
        effects=(_effect("crit-proc", "critical_damage"),),
        supplemental_denominator_proven=True,
        source="reviewed no-critical-event scenario",
    )

    assert result.denominator_proven is False
    assert any(
        "critical_damage" in row
        for row in result.unresolved
    )
