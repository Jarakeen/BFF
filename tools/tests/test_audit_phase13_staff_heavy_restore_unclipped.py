from types import SimpleNamespace

from tools.audit_phase13_staff_heavy_restore_unclipped import _is_unclipped_weapon_restore


def _restore(*, ability_game_id, current, maximum):
    return SimpleNamespace(
        ability_game_id=ability_game_id,
        max_resource_amount=maximum,
        raw_event={
            "maxResourceAmount": maximum,
            "sourceResources": {
                "magicka": current,
                "maxMagicka": maximum,
                "stamina": 12000,
                "maxStamina": 15894,
            },
        },
    )


def test_unclipped_weapon_restore_accepts_reviewed_alias_below_cap():
    restore = _restore(ability_game_id=32760, current=25212, maximum=34643)
    assert _is_unclipped_weapon_restore("restoration_staff_heavy", restore) is True


def test_unclipped_weapon_restore_rejects_reviewed_alias_at_cap():
    restore = _restore(ability_game_id=32760, current=34643, maximum=34643)
    assert _is_unclipped_weapon_restore("restoration_staff_heavy", restore) is False


def test_unclipped_weapon_restore_rejects_incidental_resource_alias():
    restore = _restore(ability_game_id=93072, current=25212, maximum=34643)
    assert _is_unclipped_weapon_restore("restoration_staff_heavy", restore) is False
