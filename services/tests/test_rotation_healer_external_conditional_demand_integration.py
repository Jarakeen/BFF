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
    assert evidence.magnitude_unit == "health_per_second"
    assert evidence.trigger_condition == "damage_affected_enemy"


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
        "Overflowing Altar at 10s: reviewed external healing condition damage_affected_enemy is not yet modeled for demand coverage",
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
