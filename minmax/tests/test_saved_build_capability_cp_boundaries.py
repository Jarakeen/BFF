from services.saved_build_capability_service import SavedBuildCapabilityService


def test_deferred_combat_cp_is_boundary_not_genuine_unresolved():
    service = SavedBuildCapabilityService.__new__(SavedBuildCapabilityService)
    service._cp_discipline = lambda _name: 1

    unresolved, boundaries = service._partition_context_messages_with_cp(
        (
            "Champion Point is dynamic or not yet stat-mapped: Battle Mastery",
            "Champion Point is dynamic or not yet stat-mapped: Tumbling",
            "Racial aggregate stats are not applied because individual racial passive ownership cannot be resolved from canonical data: Breton",
        )
    )

    assert unresolved == [
        "Racial aggregate stats are not applied because individual racial passive ownership cannot be resolved from canonical data: Breton"
    ]
    assert boundaries == [
        "Deferred Champion Point capability (status-effect chance model): Battle Mastery",
        "Deferred Champion Point capability (Roll Dodge cost combat utility channel): Tumbling",
    ]


def test_craft_tree_cp_remains_noncombat_boundary():
    service = SavedBuildCapabilityService.__new__(SavedBuildCapabilityService)
    service._cp_discipline = lambda _name: 3

    unresolved, boundaries = service._partition_context_messages_with_cp(
        ("Champion Point is dynamic or not yet stat-mapped: Rationer",)
    )

    assert unresolved == []
    assert boundaries == [
        "Non-combat Champion Point outside combat capability audit: Rationer"
    ]
