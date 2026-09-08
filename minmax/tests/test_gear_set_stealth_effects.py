from minmax.effects import EffectOperation, EffectUnit
from minmax.gear_set_effect_resolver import GearSetEffectResolver
from minmax.gear_sets import GearSetBonus
from minmax.stat_ids import StatId


def _bonus(description: str) -> GearSetBonus:
    return GearSetBonus(
        id=1,
        set_id=1,
        piece_count=3,
        description=description,
    )


def test_night_terror_projects_detection_and_sneak_cost_reduction():
    effects = GearSetEffectResolver().resolve(
        _bonus(
            "(3 items) Reduces the radius you can be detected while Sneaking by 2 meters. "
            "Reduces the cost of Sneak by 0-10%."
        )
    )

    assert [(effect.stat, effect.value) for effect in effects] == [
        (StatId.DETECTION_RADIUS_REDUCTION, 2.0),
        (StatId.SNEAK_COST_REDUCTION, 10.0),
    ]
    assert effects[0].operation is EffectOperation.ADD
    assert effects[0].unit is EffectUnit.FLAT
    assert effects[1].operation is EffectOperation.ADD_PERCENT
    assert effects[1].unit is EffectUnit.PERCENT
    assert all(effect.condition is None for effect in effects)


def test_night_terror_can_project_minimum_range_value_for_data_audit():
    effects = GearSetEffectResolver().resolve(
        _bonus(
            "(3 items) Reduces the radius you can be detected while Sneaking by 2 meters. "
            "Reduces the cost of Sneak by 0-10%."
        ),
        use_max_value=False,
    )

    assert [(effect.stat, effect.value) for effect in effects] == [
        (StatId.DETECTION_RADIUS_REDUCTION, 2.0),
        (StatId.SNEAK_COST_REDUCTION, 0.0),
    ]
