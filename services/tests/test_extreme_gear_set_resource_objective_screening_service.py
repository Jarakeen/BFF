from services.extreme_gear_set_resource_objective_screening_service import (
    ExtremeGearSetResourceObjectiveScreeningService,
)


def test_unrelated_damage_proc_is_proven_irrelevant_to_max_magicka():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(5 items) When you deal damage, summon a creature that deals Shock Damage every 2 seconds.",
        "max_magicka",
    )

    assert result.proven_irrelevant is True
    assert result.blockers == ()


def test_scaling_from_target_max_resource_does_not_modify_the_resource():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(2 items) The heal scales off the higher of your Max Magicka or Stamina.",
        "max_magicka",
    )

    assert result.proven_irrelevant is True
    assert result.target_resource_mentioned is False
    assert result.blockers == ()


def test_target_max_health_damage_scaling_is_irrelevant_to_max_health():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(5 items) Deal 717 Physical damage to the attacker. This effect scales off your Max Health.",
        "max_health",
    )

    assert result.proven_irrelevant is True
    assert result.target_resource_mentioned is False


def test_restore_based_on_higher_maximum_does_not_modify_maximum():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(2 items) Restore 700 Magicka or Stamina, whichever maximum is higher.",
        "max_magicka",
    )

    assert result.proven_irrelevant is True
    assert result.target_resource_mentioned is False


def test_alessian_style_cap_is_not_a_max_health_modifier():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "Increase your Health Recovery by 2% of your resistances, up to a maximum of 1320.",
        "max_health",
    )

    assert result.proven_irrelevant is True
    assert result.target_resource_mentioned is False


def test_bahsei_style_maximum_damage_at_magicka_threshold_is_not_max_magicka():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "Increases your damage done by up to 15% based on your missing Magicka, reaching the maximum at 50% Magicka.",
        "max_magicka",
    )

    assert result.proven_irrelevant is True
    assert result.target_resource_mentioned is False


def test_corral_style_maximum_damage_at_stamina_threshold_is_not_max_stamina():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "Increases your Weapon and Spell Damage by up to 600, based on your missing Stamina, reaching the maximum at 50% Stamina.",
        "max_stamina",
    )

    assert result.proven_irrelevant is True
    assert result.target_resource_mentioned is False


def test_max_stack_recovery_penalty_is_not_max_resource_mutation():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "At max stacks you gain Major Force. When max Skirmish ends, your Stamina, Magicka, and Health Recovery are reduced by 422.",
        "max_stamina",
    )

    assert result.proven_irrelevant is True
    assert result.target_resource_mentioned is False


def test_list_wording_catches_shapeshifter_style_maximum_resource_modifier():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(1 item) While transformed, increase your Maximum Health, Stamina, and Magicka by 1707.",
        "max_magicka",
    )

    assert result.proven_irrelevant is False
    assert result.target_resource_mentioned is True


def test_inverse_wording_catches_necropotence_style_modifier():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(5 items) While you have a pet active, your Max Magicka is increased by 3132.",
        "max_magicka",
    )

    assert result.proven_irrelevant is False
    assert result.target_resource_mentioned is True


def test_reduction_catches_thrassian_style_modifier():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(1 item) Each stack reduces your Maximum Health by 120.",
        "max_health",
    )

    assert result.proven_irrelevant is False
    assert result.target_resource_mentioned is True


def test_max_health_toughness_reference_stays_open():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(5 items) You gain Minor Toughness while the effect is active.",
        "max_health",
    )

    assert result.proven_irrelevant is False
    assert result.named_resource_hazards == ("Toughness resource modifier reference",)


def test_global_equipment_state_mechanics_stay_open_for_all_max_resources():
    descriptions = (
        "(1 item) Disable all other item set bonuses.",
        "(1 item) While equipped, you are unable to swap between your Primary and Backup Weapon Sets.",
        "(5 items) You can have two Mundus Stone boons at the same time.",
    )

    for description in descriptions:
        for objective in ("max_health", "max_magicka", "max_stamina"):
            result = ExtremeGearSetResourceObjectiveScreeningService.review(
                description,
                objective,
            )
            assert result.proven_irrelevant is False
            assert result.global_equipment_hazards


def test_other_resource_reference_does_not_block_unrelated_resource_objective():
    result = ExtremeGearSetResourceObjectiveScreeningService.review(
        "(5 items) Increase your Max Stamina by 2000.",
        "max_magicka",
    )

    assert result.proven_irrelevant is True


def test_unreviewed_objective_fails_closed():
    try:
        ExtremeGearSetResourceObjectiveScreeningService.review(
            "Adds damage.",
            "spell_damage",
        )
    except KeyError as exc:
        assert "unreviewed Extreme gear resource screening objective" in str(exc)
    else:
        raise AssertionError("expected unreviewed objective to fail closed")
