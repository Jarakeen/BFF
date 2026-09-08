from minmax.character_progression import CharacterProgression
from models.build_model import GearSlot, PlayerBuild
from services.extreme_restoration_heavy_combat_state_service import (
    ExtremeRestorationHeavyCombatStateService,
)


class _SkillLines:
    def __init__(self, max_rank=2):
        self.max_rank = max_rank

    def passive_max_rank(self, name):
        return self.max_rank if name == "Essence Drain" else None


def _service(max_rank=2):
    return ExtremeRestorationHeavyCombatStateService(
        skill_line_repository=_SkillLines(max_rank=max_rank)
    )


def _resto_build():
    return PlayerBuild(
        BuildName="Resto Heavy",
        FrontBarWeapon=GearSlot(WeaponType="Restoration Staff"),
    )


def test_restoration_heavy_state_requires_explicit_completed_trigger():
    result = _service().resolve(
        build=_resto_build(),
        progression=CharacterProgression(
            owned_skill_lines=("Restoration Staff",),
            passive_ranks={"Essence Drain": 2},
        ),
    )

    assert not result.major_mending_active
    assert result.combat_state.active_buffs == ()
    assert result.unresolved == ()


def test_maxed_essence_drain_routes_major_mending_through_combat_state():
    result = _service().resolve(
        build=_resto_build(),
        progression=CharacterProgression(
            owned_skill_lines=("Restoration Staff",),
            passive_ranks={"Essence Drain": 2},
        ),
        fully_charged_heavy_attack_completed=True,
    )

    assert result.major_mending_active
    assert result.combat_state.in_combat
    assert result.combat_state.has_buff("Major Mending")
    assert result.unresolved == ()


def test_missing_essence_drain_rank_preserves_unbuffed_state_and_blocker():
    result = _service().resolve(
        build=_resto_build(),
        progression=CharacterProgression(
            owned_skill_lines=("Restoration Staff",),
            passive_ranks={},
        ),
        fully_charged_heavy_attack_completed=True,
    )

    assert not result.major_mending_active
    assert result.combat_state.active_buffs == ()
    assert result.unresolved == (
        "Passive rank is not recorded for character: Essence Drain",
    )


def test_essence_drain_trigger_fails_closed_without_active_restoration_staff():
    build = PlayerBuild(
        BuildName="Wrong Weapon",
        FrontBarWeapon=GearSlot(WeaponType="Lightning Staff"),
    )
    result = _service().resolve(
        build=build,
        progression=CharacterProgression(
            owned_skill_lines=("Restoration Staff",),
            passive_ranks={"Essence Drain": 2},
        ),
        fully_charged_heavy_attack_completed=True,
    )

    assert not result.major_mending_active
    assert result.combat_state.active_buffs == ()
    assert result.unresolved == (
        "Essence Drain scenario requires an active Restoration Staff",
    )


def test_partial_essence_drain_rank_remains_explicit_blocker():
    result = _service(max_rank=2).resolve(
        build=_resto_build(),
        progression=CharacterProgression(
            owned_skill_lines=("Restoration Staff",),
            passive_ranks={"Essence Drain": 1},
        ),
        fully_charged_heavy_attack_completed=True,
    )

    assert not result.major_mending_active
    assert result.unresolved == (
        "Partial passive rank is not yet modeled: Essence Drain 1/2",
    )
