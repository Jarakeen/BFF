from services.rotation_tank_encounter_add_taunt_handling_service import (
    RotationTankEncounterAddTauntHandlingService,
)


def test_xalvakka_reviewed_add_taunt_handling_is_actor_specific_and_soft():
    reviewed = RotationTankEncounterAddTauntHandlingService().reviewed_for("xalvakka_hm")

    assert reviewed is not None
    iron = reviewed.actor("Iron Atronach")
    daedroth = reviewed.actor("Daedroth")

    assert iron is not None
    assert iron.handling_class == "strong_taunt_maintenance_target"
    assert iron.ranking_context is True
    assert iron.hard_maintenance_policy is False
    assert iron.median_coverage_fraction == 0.717
    assert iron.untaunted_instances == 2

    assert daedroth is not None
    assert daedroth.handling_class == "selective_contextual_taunt_target"
    assert daedroth.ranking_context is True
    assert daedroth.hard_maintenance_policy is False
    assert daedroth.median_coverage_fraction == 0.282
    assert daedroth.untaunted_instances == 7


def test_xalvakka_reviewed_add_taunt_handling_does_not_invent_hard_uptime_floor():
    reviewed = RotationTankEncounterAddTauntHandlingService().reviewed_for("xalvakka_hm")

    assert reviewed is not None
    assert all(actor.hard_maintenance_policy is False for actor in reviewed.actors)
    assert "single_report" in reviewed.evidence_scope
