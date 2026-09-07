from __future__ import annotations

from services.extreme_passive_projection_service import (
    ExtremePassiveProjectionService,
    ExtremePassiveProjectionStatus,
)
from services.extreme_skill_universe_service import (
    ExtremePlayerSkillRecord,
    ExtremeSkillDomain,
)


def _passive(
    name: str,
    description: str,
    *,
    domain: ExtremeSkillDomain = ExtremeSkillDomain.CLASS,
    skill_line: str = "Test Line",
):
    return ExtremePlayerSkillRecord(
        skill_id=1,
        name=name,
        class_type="Test Class" if domain is ExtremeSkillDomain.CLASS else "",
        skill_line=skill_line,
        skill_type="Passive",
        is_passive=True,
        is_player=True,
        is_crafted=False,
        base_ability_id=100,
        max_rank=2,
        max_rank_ability_id=200,
        description=description,
        domain=domain,
    )


def test_simple_unconditional_flat_power_passive_is_projected():
    result = ExtremePassiveProjectionService.project(
        _passive("Static Power", "Increases your Weapon and Spell Damage by 258.")
    )

    assert result.status is ExtremePassiveProjectionStatus.REVIEWED_STATIC
    by_objective = {row.objective_key: row for row in result.contributions}
    assert by_objective["weapon_damage"].flat == 258.0
    assert by_objective["spell_damage"].flat == 258.0


def test_simple_unconditional_critical_damage_is_ratio_points():
    result = ExtremePassiveProjectionService.project(
        _passive("Static Crit", "Increases your Critical Damage and Critical Healing by 10%.")
    )

    row = next(row for row in result.contributions if row.objective_key == "critical_damage")
    assert row.ratio == 0.10
    assert row.projected_delta() == 0.10


def test_percentage_power_requires_reference_value():
    result = ExtremePassiveProjectionService.project(
        _passive("Percent Power", "Increases your Weapon and Spell Damage by 4%.")
    )
    row = next(row for row in result.contributions if row.objective_key == "weapon_damage")

    assert row.projected_delta() is None
    assert row.projected_delta(reference_value=2000.0) == 80.0


def test_conditional_tooltip_is_not_flattened_into_static_score():
    result = ExtremePassiveProjectionService.project(
        _passive(
            "Conditional Power",
            "While a Test ability is slotted, increases your Weapon and Spell Damage by 10%.",
        )
    )

    assert result.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED
    assert result.contributions == ()
    assert result.conditions


def test_known_contextual_formula_is_not_duplicated_as_static_tooltip_math():
    result = ExtremePassiveProjectionService.project(
        _passive(
            "Frozen Armor",
            "Increases your Physical and Spell Resistance while a Winter's Embrace ability is slotted.",
        )
    )

    assert result.status is ExtremePassiveProjectionStatus.CONTEXT_REQUIRED
    assert result.contributions == ()
    assert "context" in result.unresolved[0].casefold()


def test_crafting_passive_is_retained_as_known_noncombat():
    result = ExtremePassiveProjectionService.project(
        _passive(
            "Medicinal Use",
            "Potion effects last longer.",
            domain=ExtremeSkillDomain.CRAFT,
            skill_line="Alchemy",
        )
    )

    assert result.status is ExtremePassiveProjectionStatus.KNOWN_NONCOMBAT
    assert result.contributions == ()


def test_unknown_combat_passive_fails_closed_as_unresolved():
    result = ExtremePassiveProjectionService.project(
        _passive("Strange Mechanic", "Causes an unusual combat interaction.")
    )

    assert result.status is ExtremePassiveProjectionStatus.UNRESOLVED
    assert result.contributions == ()
    assert result.unresolved


def test_active_skill_is_rejected_by_passive_projector():
    row = _passive("Not Passive", "No matter.")
    row = ExtremePlayerSkillRecord(**{**row.__dict__, "is_passive": False})

    try:
        ExtremePassiveProjectionService.project(row)
    except ValueError as exc:
        assert "not a passive" in str(exc)
    else:
        raise AssertionError("active skill should not be projected as a passive")
