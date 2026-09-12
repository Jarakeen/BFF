from services.rotation_dd_output_context_relevance_service import (
    RotationDDOutputContextRelevanceService,
)


def test_known_non_damage_static_diagnostics_are_ambient():
    result = RotationDDOutputContextRelevanceService().classify(
        (
            "Champion Point effect not yet modeled: Master Gatherer: Reduces harvest time.",
            "Champion Point effect not yet modeled: Celerity: Increases Movement Speed.",
            "Passive rank is not recorded for character: Last Gasp",
            "Passive rank is not recorded for character: Health Avarice",
        )
    )

    assert result.relevant == ()
    assert len(result.ambient) == 4
    assert result.output_complete is True


def test_bar_prefixed_non_damage_diagnostics_remain_ambient():
    messages = (
        "front static context: Passive rank is not recorded for character: Last Gasp",
        "back static context: Passive rank is not recorded for character: Health Avarice",
        "front static context: Champion Point effect not yet modeled: Celerity: speed",
    )

    result = RotationDDOutputContextRelevanceService().classify(messages)

    assert result.relevant == ()
    assert result.ambient == messages


def test_offensive_and_runtime_damage_gaps_remain_relevant():
    messages = (
        "front static context: Necklace jewelry trait not yet resolved: Bloodthirsty",
        "front static context: Champion Point effect not yet modeled: Master-at-Arms: direct damage",
        "front static context: Champion Point effect not yet modeled: Thaumaturge: damage over time",
        "front static context: Champion Point effect not yet modeled: Biting Aura: area damage",
        "front static context: Champion Point effect not yet modeled: Exploiter: Off Balance damage",
        "front static context: Front Bar Off Hand Charged: requires status-effect chance model",
        "front static context: Potion selected; activation/uptime is not part of static build state: Alliance Battle Draught",
    )

    result = RotationDDOutputContextRelevanceService().classify(messages)

    assert result.relevant == messages
    assert result.ambient == ()
    assert result.output_complete is False


def test_unknown_static_diagnostic_fails_closed_as_relevant():
    result = RotationDDOutputContextRelevanceService().classify(
        ("Mystery offensive modifier is unresolved",)
    )

    assert result.relevant == ("Mystery offensive modifier is unresolved",)
    assert result.output_complete is False


def test_duplicate_diagnostics_are_deduplicated_case_insensitively():
    result = RotationDDOutputContextRelevanceService().classify(
        (
            "movement_speed unresolved",
            "MOVEMENT_SPEED UNRESOLVED",
        )
    )

    assert result.relevant == ()
    assert result.ambient == ("movement_speed unresolved",)
