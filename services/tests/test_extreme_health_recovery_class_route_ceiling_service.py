from services.extreme_health_recovery_class_route_ceiling_service import (
    ExtremeHealthRecoveryClassRouteCeilingService,
)
from services.extreme_health_recovery_class_route_signature_service import (
    ExtremeHealthRecoveryClassRouteSignature,
)


def _signature(*lines: str, mastery: str | None = None):
    return ExtremeHealthRecoveryClassRouteSignature(
        relevant_skill_lines=tuple(lines),
        class_mastery=mastery,
    )


def test_scores_mastery_free_class_line_ceiling():
    row = ExtremeHealthRecoveryClassRouteCeilingService.score_signature(
        _signature("draconic_power", "living_death", "soldier_of_apocrypha"),
        wellspring_slot_ceiling=6,
    )

    assert row.class_flat_ceiling == 700.0 + 155.0 + 6 * 81.0
    assert row.wellspring_slots == 6
    assert row.score_complete is True


def test_scores_sorcerer_mastery_when_semantics_are_exact():
    row = ExtremeHealthRecoveryClassRouteCeilingService.score_signature(
        _signature("storm_calling", mastery="sphere_of_influence"),
        wellspring_slot_ceiling=6,
    )

    assert row.class_flat_ceiling == 366.0
    assert row.score_complete is True


def test_booming_voice_stays_unresolved_until_ultimate_bound_is_proven():
    row = ExtremeHealthRecoveryClassRouteCeilingService.score_signature(
        _signature("draconic_power", mastery="booming_voice"),
        wellspring_slot_ceiling=6,
    )

    assert row.class_flat_ceiling is None
    assert row.score_complete is False
    assert "Ultimate-spend" in row.unresolved[0]
