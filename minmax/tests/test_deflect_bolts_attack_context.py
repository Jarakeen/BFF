from __future__ import annotations

import pytest

from minmax.character_progression import CharacterProgression
from minmax.combat_state import IncomingAttackState
from minmax.context_factory import BuildCalculationContextFactory
from minmax.stat_ids import StatId
from models.build_model import GearSlot, PlayerBuild


def _sword_and_shield() -> PlayerBuild:
    return PlayerBuild(
        FrontBarWeapon=GearSlot(WeaponType="Sword"),
        FrontBarOffHand=GearSlot(WeaponType="Shield"),
    )


def _context(*, incoming_attack=IncomingAttackState(), owned=True, build=None):
    return BuildCalculationContextFactory().build(
        character_id="character",
        build_id="tank",
        build=build or _sword_and_shield(),
        progression=CharacterProgression(
            owned_skill_lines=("One Hand and Shield",) if owned else (),
        ),
        active_bar="front",
        incoming_attack=incoming_attack,
    )


def test_deflect_bolts_does_not_enter_generic_melee_block_mitigation():
    context = _context()
    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.60)


def test_deflect_bolts_applies_to_ranged_attack_context():
    context = _context(incoming_attack=IncomingAttackState(is_ranged=True))
    trace = context.core_state.derived[StatId.BLOCK_MITIGATION]

    # Sword and Board +20% and Deflect Bolts +14% both modify the base blocked half:
    # 50% + (50% * 34%) = 67%.
    assert trace.final_value == pytest.approx(0.67)
    assert context.incoming_attack.is_ranged is True
    assert any(
        (getattr(step, "label", step[0] if isinstance(step, tuple) else None) == "One Hand and Shield: Deflect Bolts")
        and (getattr(step, "value", step[2] if isinstance(step, tuple) else None) == pytest.approx(0.14))
        for step in trace.steps
    )


def test_deflect_bolts_applies_to_projectile_attack_context():
    context = _context(incoming_attack=IncomingAttackState(is_projectile=True))
    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.67)
    assert context.incoming_attack.is_projectile is True


def test_deflect_bolts_requires_explicit_one_hand_shield_passive_ownership():
    context = _context(
        incoming_attack=IncomingAttackState(is_ranged=True),
        owned=False,
    )
    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.50)


def test_deflect_bolts_requires_one_hand_and_shield_on_active_bar():
    build = PlayerBuild(FrontBarWeapon=GearSlot(WeaponType="Sword"))
    context = _context(
        incoming_attack=IncomingAttackState(is_projectile=True),
        build=build,
    )
    assert context.core_state.derived[StatId.BLOCK_MITIGATION].final_value == pytest.approx(0.50)
