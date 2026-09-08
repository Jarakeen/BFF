from __future__ import annotations

from models.build_model import PlayerBuild
from services.extreme_necromancer_living_death_slotted_healing_service import (
    ExtremeNecromancerLivingDeathSlottedHealingService,
)


class _SkillLines:
    def __init__(self, mapping=None):
        self.mapping = dict(mapping or {})

    def skill_line_for_ability_name(self, name: str):
        return self.mapping.get(name)


def _service(mapping=None):
    return ExtremeNecromancerLivingDeathSlottedHealingService(
        skill_line_repository=_SkillLines(mapping)
    )


def test_restoring_tether_family_grants_generic_healing_done_while_slotted():
    result = _service({"Mortal Coil": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            FrontBarSkills=["Mortal Coil", "", "", "", "", ""],
        ),
    )

    assert result.multiplier == 1.03
    assert result.qualifying_skill == "Mortal Coil"
    assert result.unresolved == ()


def test_living_death_slotted_healing_is_active_bar_only():
    service = _service({"Braided Tether": "Living Death"})
    build = PlayerBuild(
        EsoClass="Necromancer",
        FrontBarSkills=["Combat Prayer", "", "", "", "", ""],
        BackBarSkills=["Braided Tether", "", "", "", "", ""],
    )

    front = service.resolve(build=build, active_bar="front")
    back = service.resolve(build=build, active_bar="back")

    assert front.multiplier == 1.0
    assert front.qualifying_skill is None
    assert front.unresolved == ()
    assert back.multiplier == 1.03
    assert back.qualifying_skill == "Braided Tether"
    assert back.unresolved == ()


def test_explicit_route_removal_blocks_illegally_retained_tether_skill():
    result = _service({"Restoring Tether": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            ClassSkillLines=["Grave Lord", "Bone Tyrant", "Green Balance"],
            FrontBarSkills=["Restoring Tether", "", "", "", "", ""],
        ),
    )

    assert result.multiplier == 1.0
    assert result.qualifying_skill is None
    assert result.unresolved == (
        "Living Death slotted Healing Done: qualifying skill is present but Living Death "
        "is not equipped in the class route",
    )


def test_foreign_class_route_can_use_reviewed_tether_slot_bonus():
    result = _service({"Restoring Tether": "Living Death"}).resolve(
        build=PlayerBuild(
            EsoClass="Warden",
            ClassSkillLines=["Green Balance", "Winter's Embrace", "Living Death"],
            FrontBarSkills=["Restoring Tether", "", "", "", "", ""],
        ),
    )

    assert result.multiplier == 1.03
    assert result.qualifying_skill == "Restoring Tether"
    assert result.unresolved == ()


def test_unknown_canonical_line_preserves_lower_bound_and_blocks_bonus():
    result = _service({}).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            FrontBarSkills=["Mortal Coil", "", "", "", "", ""],
        ),
    )

    assert result.multiplier == 1.0
    assert result.qualifying_skill is None
    assert result.unresolved == (
        "Living Death slotted Healing Done: could not resolve canonical skill line for "
        "slotted ability 'Mortal Coil' on front bar",
    )


def test_multiple_tether_family_variants_do_not_stack_and_are_flagged_illegal():
    result = _service(
        {
            "Restoring Tether": "Living Death",
            "Mortal Coil": "Living Death",
        }
    ).resolve(
        build=PlayerBuild(
            EsoClass="Necromancer",
            FrontBarSkills=["Restoring Tether", "Mortal Coil", "", "", "", ""],
        ),
    )

    assert result.multiplier == 1.03
    assert result.qualifying_skill == "Restoring Tether"
    assert result.unresolved == (
        "Living Death slotted Healing Done: multiple Restoring Tether-family skills are "
        "slotted; legal morph/base duplication is unresolved",
    )
