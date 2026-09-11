import pytest

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from services.rotation_healer_action_healing_service import (
    RotationHealerActionHealingProjection,
    RotationHealerExternalConditionalHealSeed,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidenceService,
    RotationHealerExternalConditionalDemandAssumption,
)
from services.rotation_healer_external_conditional_healing_service import (
    RotationHealerExternalConditionalHealingService,
)


def _demand():
    return RotationDemandWindow(
        name="Xalvakka Phase 2 healing prep",
        start_seconds=29.13,
        end_seconds=34.13,
        kind=RotationDemandKind.HEALING,
        pattern=RotationDemandPattern.BURST,
        target_count=12,
    )


def _seed(time_seconds):
    evidence = RotationHealerExternalConditionalHealingService().resolve(
        "overflowing_altar"
    )
    assert evidence is not None
    return RotationHealerExternalConditionalHealSeed(
        time_seconds=float(time_seconds),
        sequence=1,
        source_name="Overflowing Altar",
        skill_id=evidence.skill_id,
        effect_name=evidence.effect_name,
        duration_seconds=evidence.duration_seconds,
        reviewed_magnitude=evidence.reviewed_magnitude,
        magnitude_unit=evidence.magnitude_unit,
        trigger_condition=evidence.trigger_condition,
        provenance=evidence.provenance,
        game_version=evidence.game_version,
    )


def test_reviewed_overflowing_altar_evidence_keeps_trigger_semantics_structured():
    evidence = RotationHealerExternalConditionalHealingService().resolve(
        "overflowing_altar"
    )

    assert evidence is not None
    assert evidence.effect_name == "minor_lifesteal"
    assert evidence.duration_seconds == 30.0
    assert evidence.reviewed_magnitude == 600.0
    assert evidence.magnitude_unit == "health_per_trigger"
    assert evidence.trigger_condition == "damage_affected_enemy"
    assert evidence.trigger_actor == "damaging_actor"
    assert evidence.heal_recipient == "trigger_actor"
    assert evidence.logged_heal_owner == "effect_provider"
    assert evidence.maximum_trigger_rate_per_actor_per_second == 1.0


def test_only_external_conditional_effects_overlapping_demand_remain_blockers():
    projection = RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=(),
        delayed_seeds=(),
        external_conditional_seeds=(
            _seed(10.0),
            _seed(44.0),
        ),
        unresolved=(),
    )

    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=projection,
    )

    assert result.unresolved == (
        "Overflowing Altar at 10s: reviewed external healing condition damage_affected_enemy requires an explicit active-attacker count for demand coverage",
    )
    assert not any("44s" in item for item in result.unresolved)
    assert result.modeled_total_healing == 0.0


def test_expired_external_conditional_effect_does_not_block_later_demand():
    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=RotationHealerActionHealingProjection(
            direct_events=(),
            periodic_seeds=(),
            delayed_seeds=(),
            external_conditional_seeds=(_seed(-5.0),),
            unresolved=(),
        ),
    )

    assert result.unresolved == ()


def test_explicit_active_attackers_model_minor_lifesteal_without_fake_ticks():
    projection = RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=(),
        delayed_seeds=(),
        external_conditional_seeds=(_seed(10.0),),
        unresolved=(),
    )

    result = RotationHealerDemandHealingEvidenceService().assess(
        demand=_demand(),
        projection=projection,
        external_conditional_assumptions=(
            RotationHealerExternalConditionalDemandAssumption(
                effect_name="minor_lifesteal",
                active_attacker_count=4,
            ),
        ),
    )

    assert result.unresolved == ()
    assert result.modeled_external_conditional_healing == pytest.approx(12_000.0)
    assert result.modeled_total_healing == pytest.approx(12_000.0)


def test_active_attacker_count_cannot_exceed_demand_targets():
    projection = RotationHealerActionHealingProjection(
        direct_events=(),
        periodic_seeds=(),
        delayed_seeds=(),
        external_conditional_seeds=(_seed(10.0),),
        unresolved=(),
    )

    try:
        RotationHealerDemandHealingEvidenceService().assess(
            demand=_demand(),
            projection=projection,
            external_conditional_assumptions=(
                RotationHealerExternalConditionalDemandAssumption(
                    effect_name="minor_lifesteal",
                    active_attacker_count=13,
                ),
            ),
        )
    except ValueError as exc:
        assert "cannot exceed demand target count 12" in str(exc)
    else:
        raise AssertionError("expected an invalid active-attacker count to fail closed")
