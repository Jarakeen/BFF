from services.saved_build_capability_service import SavedBuildCapabilityService


def test_deferred_racial_passive_messages_are_boundaries():
    unresolved, boundaries = SavedBuildCapabilityService._partition_context_messages(
        (
            "Conditional racial passive bonus requires combat-state model: Spell Attunement",
            "Racial ability-cost reduction requires cost-stat model: Magicka Mastery",
            "Non-combat racial passive outside combat capability audit: Opportunist",
            "Racial passive tooltip is not yet stat-mapped: Mystery Heritage",
        )
    )

    assert unresolved == [
        "Racial passive tooltip is not yet stat-mapped: Mystery Heritage"
    ]
    assert boundaries == [
        "Conditional racial passive bonus requires combat-state model: Spell Attunement",
        "Racial ability-cost reduction requires cost-stat model: Magicka Mastery",
        "Non-combat racial passive outside combat capability audit: Opportunist",
    ]
