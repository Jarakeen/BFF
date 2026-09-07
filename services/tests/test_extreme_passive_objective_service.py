from __future__ import annotations

from services.extreme_passive_objective_service import (
    ExtremePassiveLegalityContext,
    ExtremePassiveObjectiveService,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(
    name: str,
    line: str,
    domain: ExtremeSkillDomain,
    description: str,
    *,
    class_type: str = "",
    skill_id: int = 1,
):
    return ExtremePlayerSkillRecord(
        skill_id=skill_id,
        name=name,
        class_type=class_type,
        skill_line=line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=1000 + skill_id,
        max_rank=2,
        max_rank_ability_id=2000 + skill_id,
        description=description,
        domain=domain,
    )


def test_only_passives_legal_for_route_contribute():
    rows = (
        _passive(
            "Warden Power",
            "Winter's Embrace",
            ExtremeSkillDomain.CLASS,
            "Increases your Weapon and Spell Damage by 100.",
            class_type="Warden",
            skill_id=1,
        ),
        _passive(
            "DK Power",
            "Ardent Flame",
            ExtremeSkillDomain.CLASS,
            "Increases your Weapon and Spell Damage by 999.",
            class_type="Dragonknight",
            skill_id=2,
        ),
        _passive(
            "Resto Power",
            "Restoration Staff",
            ExtremeSkillDomain.WEAPON,
            "Increases your Spell Damage by 50.",
            skill_id=3,
        ),
        _passive(
            "Bow Power",
            "Bow",
            ExtremeSkillDomain.WEAPON,
            "Increases your Spell Damage by 500.",
            skill_id=4,
        ),
    )
    context = ExtremePassiveLegalityContext(
        equipped_class_lines=("Winter's Embrace", "Green Balance", "Daedric Summoning"),
        equipped_weapon_lines=("Restoration Staff",),
    )

    result = ExtremePassiveObjectiveService.score(rows, "spell_damage", context)

    assert result.projected_delta == 150.0
    assert {row.source.split(":", 1)[0] for row in result.contributions} == {
        "Warden Power [Winter's Embrace]",
        "Resto Power [Restoration Staff]",
    }


def test_selected_racial_line_gates_racial_passives():
    rows = (
        _passive(
            "Khajiit Power",
            "Khajiit Skills",
            ExtremeSkillDomain.RACIAL,
            "Increases your Weapon and Spell Damage by 90.",
            skill_id=5,
        ),
        _passive(
            "Nord Power",
            "Nord Skills",
            ExtremeSkillDomain.RACIAL,
            "Increases your Weapon and Spell Damage by 900.",
            skill_id=6,
        ),
    )
    context = ExtremePassiveLegalityContext(
        equipped_class_lines=("Green Balance",),
        selected_racial_line="Khajiit Skills",
    )

    result = ExtremePassiveObjectiveService.score(rows, "weapon_damage", context)

    assert result.projected_delta == 90.0


def test_vampire_passive_requires_vampire_route():
    vampire = _passive(
        "Vamp Power",
        "Vampire",
        ExtremeSkillDomain.WORLD,
        "Increases your Spell Damage by 80.",
        skill_id=7,
    )
    mortal = ExtremePassiveLegalityContext(equipped_class_lines=("Green Balance",))
    vamp = ExtremePassiveLegalityContext(
        equipped_class_lines=("Green Balance",),
        vampire=True,
    )

    assert ExtremePassiveObjectiveService.score((vampire,), "spell_damage", mortal).projected_delta == 0.0
    assert ExtremePassiveObjectiveService.score((vampire,), "spell_damage", vamp).projected_delta == 80.0


def test_contextual_and_unresolved_passives_remain_explicit_blockers():
    rows = (
        _passive(
            "Conditional",
            "Fighters Guild",
            ExtremeSkillDomain.GUILD,
            "While a Fighters Guild ability is slotted, increases your Weapon and Spell Damage by 10%.",
            skill_id=8,
        ),
        _passive(
            "Mystery",
            "Fighters Guild",
            ExtremeSkillDomain.GUILD,
            "Causes a strange combat interaction.",
            skill_id=9,
        ),
    )
    context = ExtremePassiveLegalityContext(equipped_class_lines=("Green Balance",))

    result = ExtremePassiveObjectiveService.score(rows, "spell_damage", context, reference_value=2000.0)

    assert result.projected_delta == 0.0
    assert result.fully_resolved is False
    assert result.context_required_passives == ("Fighters Guild: Conditional",)
    assert result.unresolved_passives == ("Fighters Guild: Mystery",)


def test_crafting_passive_is_known_but_never_becomes_combat_score():
    craft = _passive(
        "Medicinal Use",
        "Alchemy",
        ExtremeSkillDomain.CRAFT,
        "Potion effects last longer.",
        skill_id=10,
    )
    context = ExtremePassiveLegalityContext(equipped_class_lines=("Green Balance",))

    result = ExtremePassiveObjectiveService.score((craft,), "spell_damage", context)

    assert result.projected_delta == 0.0
    assert result.fully_resolved is True
