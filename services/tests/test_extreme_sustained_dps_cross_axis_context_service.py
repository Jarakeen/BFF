from __future__ import annotations

from minmax.character_progression import CharacterProgression
from models.build_model import PlayerBuild
from services.extreme_gear_physical_slot_realization_service import ExtremeWeaponSlotShape
from services.extreme_named_gear_set_realization_service import (
    ExtremeNamedGearSetRealization,
    ExtremeNamedGearSlotAssignment,
)
from services.extreme_sustained_dps_cross_axis_context_service import (
    ExtremeSustainedDPSCrossAxisContextService,
)
from services.extreme_dual_bar_gear_state_service import ExtremeDualBarGearState


def _realization(
    *,
    weapon_set: int,
    weapon_name: str,
    weapon_type: str,
    extra_sets=(),
):
    set_ids = (10, weapon_set, *(set_id for set_id, _name, _count in extra_sets))
    set_names = ("Body", weapon_name, *(name for _set_id, name, _count in extra_sets))
    counts = (5, 2, *(count for _set_id, _name, count in extra_sets))
    return ExtremeNamedGearSetRealization(
        topology_signature="5+2|unused:5",
        set_ids=set_ids,
        set_names=set_names,
        counts=counts,
        weapon_shape=ExtremeWeaponSlotShape.TWO_HANDED,
        assignments=(
            ExtremeNamedGearSlotAssignment("Head", 10, "Body"),
            ExtremeNamedGearSlotAssignment("Shoulders", 10, "Body"),
            ExtremeNamedGearSlotAssignment("Chest", 10, "Body"),
            ExtremeNamedGearSlotAssignment("Hands", 10, "Body"),
            ExtremeNamedGearSlotAssignment("Waist", 10, "Body"),
            ExtremeNamedGearSlotAssignment(
                "Main Hand",
                weapon_set,
                weapon_name,
                weapon_type,
            ),
        ),
    )


def _build():
    build = PlayerBuild(
        EsoClass="Warden",
        Role="DD",
        ClassSkillLines=["animal_companions", "green_balance", "winters_embrace"],
    )
    for slot, weight in (
        ("Head", "Medium"),
        ("Shoulders", "Medium"),
        ("Chest", "Light"),
        ("Hands", "Medium"),
        ("Waist", "Medium"),
    ):
        build.Armor[slot]["Weight"] = weight
    return build


def test_cross_axis_context_binds_equipment_and_explicit_ownership_separately() -> None:
    state = ExtremeDualBarGearState(
        front=_realization(
            weapon_set=20,
            weapon_name="Front Weapon",
            weapon_type="Inferno Staff",
        ),
        back=_realization(
            weapon_set=30,
            weapon_name="Back Weapon",
            weapon_type="Bow",
        ),
    )
    progression = CharacterProgression(
        owned_skill_lines=("Fighters Guild",),
        passive_ranks={},
    )

    result = ExtremeSustainedDPSCrossAxisContextService.compose(
        _build(),
        progression,
        gear_state=state,
    )

    assert result.resolved is True
    assert result.front_weapon_lines == ("Destruction Staff",)
    assert result.back_weapon_lines == ("Bow",)
    assert result.equipped_armor_lines == ("Light Armor", "Medium Armor")
    assert result.explicit_owned_skill_lines == ("Fighters Guild",)
    assert result.front_skill_context.weapon_skill_lines == ("Destruction Staff",)
    assert result.front_skill_context.class_skill_lines == result.class_skill_lines
    assert result.front_skill_context.owned_skill_lines == ("Fighters Guild",)
    assert result.one_bar_only is False


def test_oakensoul_collapses_back_skill_context_without_guessing_from_skill_bar() -> None:
    oak = ((99, "Oakensoul Ring", 1),)
    state = ExtremeDualBarGearState(
        front=_realization(
            weapon_set=20,
            weapon_name="Front Weapon",
            weapon_type="Inferno Staff",
            extra_sets=oak,
        ),
        back=_realization(
            weapon_set=30,
            weapon_name="Back Weapon",
            weapon_type="Bow",
            extra_sets=oak,
        ),
    )

    result = ExtremeSustainedDPSCrossAxisContextService.compose(
        _build(),
        CharacterProgression(),
        gear_state=state,
    )

    assert result.resolved is True
    assert result.one_bar_only is True
    assert result.bar_access.activatable_bars == ("front",)
    assert result.back_weapon_lines == ()
    assert result.back_skill_context.weapon_skill_lines == ()


def test_unresolved_weapon_identity_fails_closed() -> None:
    state = ExtremeDualBarGearState(
        front=_realization(
            weapon_set=20,
            weapon_name="Front Weapon",
            weapon_type="Mystery Stick",
        ),
        back=_realization(
            weapon_set=30,
            weapon_name="Back Weapon",
            weapon_type="Bow",
        ),
    )

    result = ExtremeSustainedDPSCrossAxisContextService.compose(
        _build(),
        CharacterProgression(),
        gear_state=state,
    )

    assert result.resolved is False
    assert any("weapon type is unresolved" in row for row in result.unresolved)
