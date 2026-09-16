from services.rotation_saved_build_weapon_attack_evaluation_service import (
    _weapon_attack_relevant_static_unresolved,
)


def test_swift_jewelry_trait_does_not_block_saved_weapon_attack_evidence() -> None:
    messages = (
        "front static context: Ring 1 jewelry trait not yet resolved: Swift",
        "back static context: Ring 1 jewelry trait not yet resolved: Swift",
    )

    assert _weapon_attack_relevant_static_unresolved(messages) == ()


def test_unrelated_static_context_gap_remains_fail_closed() -> None:
    messages = (
        "front static context: Ring 1 jewelry trait not yet resolved: Swift",
        "front static context: Ring 2 jewelry trait not yet resolved: Harmony",
    )

    assert _weapon_attack_relevant_static_unresolved(messages) == (
        "front static context: Ring 2 jewelry trait not yet resolved: Harmony",
    )
