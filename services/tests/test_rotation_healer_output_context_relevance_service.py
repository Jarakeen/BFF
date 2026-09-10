from services.rotation_healer_output_context_relevance_service import (
    RotationHealerOutputContextRelevanceService,
)


def test_known_non_healing_static_diagnostics_are_ambient():
    result = RotationHealerOutputContextRelevanceService().classify(
        (
            "Champion Point is dynamic or not yet stat-mapped: Master Gatherer",
            "Champion Point is dynamic or not yet stat-mapped: Celerity",
            "Passive rank is not recorded for character: Flourish",
            "Passive rank is not recorded for character: Advanced Species",
            "Passive rank is not recorded for character: Frozen Armor",
        )
    )

    assert result.relevant == ()
    assert len(result.ambient) == 5
    assert result.output_complete is True


def test_potion_and_charged_remain_healer_output_relevant():
    result = RotationHealerOutputContextRelevanceService().classify(
        (
            "Potion selected; activation/uptime is not part of static build state: spell power",
            "Back Bar Charged: requires status-effect chance model",
        )
    )

    assert result.relevant == (
        "Potion selected; activation/uptime is not part of static build state: spell power",
        "Back Bar Charged: requires status-effect chance model",
    )
    assert result.ambient == ()
    assert result.output_complete is False


def test_unknown_static_diagnostic_fails_closed_as_relevant():
    result = RotationHealerOutputContextRelevanceService().classify(
        ("Mystery healing modifier is unresolved",)
    )

    assert result.relevant == ("Mystery healing modifier is unresolved",)
    assert result.output_complete is False


def test_duplicate_diagnostics_are_deduplicated_case_insensitively():
    result = RotationHealerOutputContextRelevanceService().classify(
        (
            "movement_speed unresolved",
            "MOVEMENT_SPEED UNRESOLVED",
        )
    )

    assert result.relevant == ()
    assert result.ambient == ("movement_speed unresolved",)
