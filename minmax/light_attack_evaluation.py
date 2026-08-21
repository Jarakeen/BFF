from __future__ import annotations

from minmax.build_evaluation import BuildEvaluation
from minmax.resolvers.light_attack_resolver import resolve_light_attack_state
from minmax.combat_state import LightAttackState
from minmax.stat_ids import StatId


def _sum_contributions(
    evaluation: BuildEvaluation,
    *effect_types: str,
) -> float:
    """Sum effective combat contributions matching the requested types."""
    wanted = set(effect_types)

    return sum(
        contribution.effective_value
        for contribution in evaluation.combat_contributions
        if contribution.effect_type in wanted
    )


def resolve_light_attack_from_evaluation(
    *,
    evaluation: BuildEvaluation,
    la_flame_spell_damage: float | None = None,
    la_flame_weapon_damage: float | None = None,
    la_frost_spell_damage: float | None = None,
    la_frost_weapon_damage: float | None = None,
    la_shock_spell_damage: float | None = None,
    la_shock_weapon_damage: float | None = None,
) -> LightAttackState:
    """Resolve a LightAttackState from an already evaluated build.

    Stat values come from BuildEvaluation.stats.
    Combat modifiers come from evaluated combat contributions.

    Explicit LA damage values may be supplied when the weapon/attack
    calculation has not yet been connected to the equipment model.
    """

    stats = evaluation.stats

    magicka = stats.value(StatId.MAX_MAGICKA)
    stamina = stats.value(StatId.MAX_STAMINA)
    spell_damage = stats.value(StatId.SPELL_DAMAGE)
    weapon_damage = stats.value(StatId.WEAPON_DAMAGE)

    return resolve_light_attack_state(
        magicka=magicka,
        stamina=stamina,

        la_flame_spell_damage=(
            spell_damage
            if la_flame_spell_damage is None
            else la_flame_spell_damage
        ),
        la_flame_weapon_damage=(
            weapon_damage
            if la_flame_weapon_damage is None
            else la_flame_weapon_damage
        ),

        la_frost_spell_damage=(
            spell_damage
            if la_frost_spell_damage is None
            else la_frost_spell_damage
        ),
        la_frost_weapon_damage=(
            weapon_damage
            if la_frost_weapon_damage is None
            else la_frost_weapon_damage
        ),

        la_shock_spell_damage=(
            spell_damage
            if la_shock_spell_damage is None
            else la_shock_spell_damage
        ),
        la_shock_weapon_damage=(
            weapon_damage
            if la_shock_weapon_damage is None
            else la_shock_weapon_damage
        ),

        skill2_la_damage=_sum_contributions(
            evaluation,
            "skill2_la_damage",
        ),
        cp_la_damage=_sum_contributions(
            evaluation,
            "cp_la_damage",
        ),
        skill_la_damage=_sum_contributions(
            evaluation,
            "skill_la_damage",
        ),
        set_la_damage=_sum_contributions(
            evaluation,
            "set_la_damage",
        ),

        skill_ha_damage=_sum_contributions(
            evaluation,
            "skill_ha_damage",
        ),
        set_ha_damage=_sum_contributions(
            evaluation,
            "set_ha_damage",
        ),
        buff_empower=_sum_contributions(
            evaluation,
            "empower",
        ),

        flame_damage_done=_sum_contributions(
            evaluation,
            "flame_damage_done",
        ),
        frost_damage_done=_sum_contributions(
            evaluation,
            "frost_damage_done",
        ),
        shock_damage_done=_sum_contributions(
            evaluation,
            "shock_damage_done",
        ),
        direct_damage_done=_sum_contributions(
            evaluation,
            "direct_damage_done",
        ),
        single_target_damage_done=_sum_contributions(
            evaluation,
            "single_target_damage_done",
        ),
        dot_damage_done=_sum_contributions(
            evaluation,
            "dot_damage_done",
        ),
        damage_done=_sum_contributions(
            evaluation,
            "damage_done",
        ),
    )