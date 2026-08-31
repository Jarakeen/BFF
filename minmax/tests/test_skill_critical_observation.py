import pytest

from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_critical_observation import (
    CriticalComponentCandidate,
    CriticalEventFamily,
    RuntimeCriticalObservation,
    resolve_observed_critical_eligibility,
)


def _candidate(
    *,
    rank=10,
    coef=1,
    ability=100,
    kind=SkillEffectKind.DAMAGE,
    is_dot=False,
    can_crit=None,
):
    return CriticalComponentCandidate(
        skill_rank_id=rank,
        coefficient_number=coef,
        ability_id=ability,
        effect_kind=kind,
        is_dot=is_dot,
        can_crit=can_crit,
    )


def test_direct_damage_critical_observation_resolves_unique_component_true():
    resolved, summary = resolve_observed_critical_eligibility(
        (_candidate(),),
        (
            RuntimeCriticalObservation(
                ability_id=100,
                event_family=CriticalEventFamily.DAMAGE_DIRECT,
                source="ESO API ACTION_RESULT_CRITICAL_DAMAGE",
                observed_count=3,
            ),
        ),
    )

    assert len(resolved) == 1
    assert resolved[0].skill_rank_id == 10
    assert resolved[0].coefficient_number == 1
    assert resolved[0].can_crit is True
    assert resolved[0].observed_count == 3
    assert summary.resolved_components == 1
    assert summary.ambiguous_observations == 0


def test_periodic_damage_critical_observation_maps_only_to_dot_component():
    candidates = (
        _candidate(coef=1, is_dot=False),
        _candidate(coef=2, is_dot=True),
    )
    observations = (
        RuntimeCriticalObservation(
            ability_id=100,
            event_family=CriticalEventFamily.DAMAGE_PERIODIC,
            source="ESO API ACTION_RESULT_DOT_TICK_CRITICAL",
        ),
    )

    resolved, summary = resolve_observed_critical_eligibility(candidates, observations)

    assert [(row.coefficient_number, row.can_crit) for row in resolved] == [(2, True)]
    assert summary.resolved_components == 1


def test_heal_direct_and_periodic_families_are_distinct():
    candidates = (
        _candidate(coef=1, kind=SkillEffectKind.HEAL, is_dot=False),
        _candidate(coef=2, kind=SkillEffectKind.HEAL, is_dot=True),
    )
    observations = (
        RuntimeCriticalObservation(
            ability_id=100,
            event_family=CriticalEventFamily.HEAL_DIRECT,
            source="ESO Logs isCritical=true isTick=false",
        ),
        RuntimeCriticalObservation(
            ability_id=100,
            event_family=CriticalEventFamily.HEAL_PERIODIC,
            source="ESO Logs isCritical=true isTick=true",
        ),
    )

    resolved, summary = resolve_observed_critical_eligibility(candidates, observations)

    assert {row.coefficient_number for row in resolved} == {1, 2}
    assert summary.resolved_components == 2


def test_two_same_family_components_are_ambiguous_and_not_resolved():
    candidates = (
        _candidate(coef=1, is_dot=False),
        _candidate(coef=2, is_dot=False),
    )
    observations = (
        RuntimeCriticalObservation(
            ability_id=100,
            event_family=CriticalEventFamily.DAMAGE_DIRECT,
            source="ESO Logs isCritical=true",
        ),
    )

    resolved, summary = resolve_observed_critical_eligibility(candidates, observations)

    assert resolved == ()
    assert summary.ambiguous_observations == 1
    assert summary.resolved_components == 0


def test_nonmatching_observation_family_is_unmatched():
    resolved, summary = resolve_observed_critical_eligibility(
        (_candidate(is_dot=False),),
        (
            RuntimeCriticalObservation(
                ability_id=100,
                event_family=CriticalEventFamily.DAMAGE_PERIODIC,
                source="runtime fixture",
            ),
        ),
    )

    assert resolved == ()
    assert summary.unmatched_observations == 1


def test_already_classified_component_is_never_overwritten():
    resolved, summary = resolve_observed_critical_eligibility(
        (_candidate(can_crit=False),),
        (
            RuntimeCriticalObservation(
                ability_id=100,
                event_family=CriticalEventFamily.DAMAGE_DIRECT,
                source="runtime fixture",
            ),
        ),
    )

    assert resolved == ()
    assert summary.already_classified_observations == 1


def test_multiple_sources_and_observations_are_merged_for_same_mapping():
    observations = (
        RuntimeCriticalObservation(
            ability_id=100,
            event_family=CriticalEventFamily.DAMAGE_DIRECT,
            source="LibCombat",
            observed_count=2,
        ),
        RuntimeCriticalObservation(
            ability_id=100,
            event_family=CriticalEventFamily.DAMAGE_DIRECT,
            source="ESO Logs",
            observed_count=5,
        ),
    )

    resolved, summary = resolve_observed_critical_eligibility((_candidate(),), observations)

    assert len(resolved) == 1
    assert resolved[0].observed_count == 7
    assert resolved[0].source == "ESO Logs; LibCombat"
    assert summary.observations == 1
    assert summary.observation_events == 7


def test_non_damage_heal_components_have_no_runtime_crit_family():
    shield = _candidate(kind=SkillEffectKind.SHIELD, is_dot=None)
    utility = _candidate(coef=2, kind=SkillEffectKind.UTILITY, is_dot=None)

    assert shield.event_family is None
    assert utility.event_family is None


def test_runtime_observation_requires_positive_count_and_source():
    with pytest.raises(ValueError):
        RuntimeCriticalObservation(
            ability_id=100,
            event_family=CriticalEventFamily.DAMAGE_DIRECT,
            source="fixture",
            observed_count=0,
        )

    with pytest.raises(ValueError):
        RuntimeCriticalObservation(
            ability_id=100,
            event_family=CriticalEventFamily.DAMAGE_DIRECT,
            source="   ",
        )


def test_absence_of_observations_never_creates_false_evidence():
    resolved, summary = resolve_observed_critical_eligibility((_candidate(),), ())

    assert resolved == ()
    assert summary.observations == 0
    assert summary.resolved_components == 0
