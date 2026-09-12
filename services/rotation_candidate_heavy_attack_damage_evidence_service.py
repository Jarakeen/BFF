from __future__ import annotations

from minmax.build_evaluation import BuildEvaluation
from minmax.character_build.character_build import CharacterBuild
from minmax.combat_damage_modifiers import (
    damage_done_from_combat_state,
    damage_taken_from_target_state,
)
from minmax.combat_state import CombatState
from minmax.dd_damage import DDDamageEvent, calculate_dd_damage
from minmax.dd_mitigation import calculate_dd_mitigation
from minmax.dd_stat_evaluation import evaluate_dd_stats
from minmax.evaluation_context import EvaluationContext
from minmax.formulas.heavy_attack import (
    calculate_ha_dual_wield,
    calculate_ha_flame_spell_damage,
    calculate_ha_flame_staff,
    calculate_ha_flame_weapon_damage,
    calculate_ha_frost_spell_damage,
    calculate_ha_frost_staff,
    calculate_ha_frost_weapon_damage,
    calculate_ha_magic_spell_damage,
    calculate_ha_magic_weapon_damage,
    calculate_ha_one_hand,
    calculate_ha_physical_spell_damage,
    calculate_ha_physical_weapon_damage,
    calculate_ha_restoration,
    calculate_ha_restoration_final,
    calculate_ha_shock_spell_damage,
    calculate_ha_shock_staff,
    calculate_ha_shock_staff_final,
    calculate_ha_shock_weapon_damage,
    calculate_ha_two_hand,
)
from minmax.heavy_attack_restoration import HeavyAttackWeaponType
from minmax.rotation_plan import RotationAction, RotationActionKind
from minmax.stat_ids import StatId
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_heavy_attack_restoration_evidence_service import (
    RotationHeavyAttackCompletionEvidence,
)
from services.rotation_heavy_attack_weapon_projection_service import (
    RotationHeavyAttackWeaponProjectionService,
)
from services.rotation_saved_build_dd_conditional_damage_done_service import (
    exploiter_damage_done_bonus,
)


def _sum_contributions(evaluation: BuildEvaluation, *effect_types: str) -> float:
    wanted = set(effect_types)
    return sum(
        contribution.effective_value
        for contribution in evaluation.combat_contributions
        if contribution.effect_type in wanted
    )


class RotationCandidateHeavyAttackDamageEvidenceService:
    """Resolve fully charged heavy attacks through canonical UESP-translated math.

    Weapon identity and active-bar reconstruction remain owned by
    ``RotationHeavyAttackWeaponProjectionService``. Full-charge/completion proof is
    reused from the existing heavy-attack restoration evidence contract, but damage
    does not depend on a known restoration amount. UESP-translated heavy-attack
    formulas own the attacker-side HA/typed/direct/single-target/Damage Done math;
    the existing DD pipeline adds expected crit, mitigation, and target Damage Taken.

    Runtime attacker combat state contributes reviewed named generic Damage Done
    effects. Target-state-dependent Exploiter is carried as a magnitude in the
    canonical weapon evaluation and joins the same additive Damage Done bucket only
    when the exact HA completion target state is Off Balance. Target-side Damage Taken
    remains a separate later combat stage.

    Flame, frost, shock, restoration staff, two-handed, dual-wield, and one-hand-and-
    shield heavies are routed here. Bow remains unresolved because the canonical
    heavy-attack formula module does not currently expose a reviewed bow damage
    formula. Unarmed/Werewolf/Overload remain transformation-specific concerns.
    """

    _EPSILON = 1e-9

    def __init__(
        self,
        *,
        build: CharacterBuild,
        evaluation: BuildEvaluation,
        initial_bar: str,
        completion_evidence: tuple[RotationHeavyAttackCompletionEvidence, ...],
        evaluation_context: EvaluationContext = EvaluationContext(),
        weapon_projection_service: RotationHeavyAttackWeaponProjectionService | None = None,
        attacker_combat_state: CombatState | None = None,
        target_combat_state: CombatState | None = None,
        target_critical_resistance: float = 0.0,
    ) -> None:
        self.build = build
        self.evaluation = evaluation
        self.initial_bar = str(initial_bar or "").strip().casefold()
        if self.initial_bar not in {"front", "back"}:
            raise ValueError("rotation heavy-attack initial_bar must be front or back")
        self.completion_evidence = tuple(completion_evidence)
        self.evaluation_context = evaluation_context
        self.weapon_projection_service = (
            weapon_projection_service or RotationHeavyAttackWeaponProjectionService()
        )
        self.attacker_combat_state = attacker_combat_state
        self.target_combat_state = target_combat_state
        self.target_critical_resistance = float(target_critical_resistance)

    def evaluate_action(
        self,
        *,
        candidate: GeneratedRotationCandidate,
        action: RotationAction,
    ) -> RotationActionDamageEvidence:
        if action.kind is not RotationActionKind.HEAVY_ATTACK:
            return self._unresolved(
                action,
                f"{action.kind.value} damage requires its dedicated canonical action evaluator",
            )

        evidence = self._completion_for(action)
        if evidence is None:
            return self._unresolved(
                action,
                f"scheduled heavy attack at {action.time_seconds:.3f}s sequence {action.sequence} lacks completion/full-charge evidence",
            )
        if evidence.completion_time_seconds > candidate.plan.duration_seconds + self._EPSILON:
            return self._unresolved(
                action,
                f"heavy attack at {action.time_seconds:.3f}s completes after the rotation plan horizon at {evidence.completion_time_seconds:.3f}s",
            )
        if not evidence.fully_charged:
            return self._unresolved(
                action,
                "partial/interrupted heavy-attack damage is unresolved; canonical full-charge formula cannot be reused",
            )

        projection = self.weapon_projection_service.project(
            build=self.build,
            plan=candidate.plan,
            initial_bar=self.initial_bar,
        )
        for violation in projection.violations:
            if violation.action == action:
                return self._unresolved(action, violation.reason)
        resolution = next(
            (item for item in projection.resolutions if item.action == action),
            None,
        )
        if resolution is None:
            if projection.unresolved:
                return self._unresolved(action, *projection.unresolved)
            return self._unresolved(
                action,
                "scheduled heavy attack has no resolved active-bar weapon identity",
            )

        formula_damage = self._formula_damage(resolution.weapon)
        if formula_damage is None:
            return self._unresolved(
                action,
                f"canonical heavy-attack damage routing unavailable for {resolution.weapon.value}",
            )

        damage_type = {
            HeavyAttackWeaponType.FIRE_STAFF: "flame",
            HeavyAttackWeaponType.FROST_STAFF: "frost",
            HeavyAttackWeaponType.SHOCK_STAFF: "shock",
            HeavyAttackWeaponType.RESTORATION_STAFF: "magical",
            HeavyAttackWeaponType.TWO_HANDED: "physical",
            HeavyAttackWeaponType.DUAL_WIELD: "physical",
            HeavyAttackWeaponType.ONE_HAND_AND_SHIELD: "physical",
        }[resolution.weapon]

        dd_stats = evaluate_dd_stats(self.evaluation.stats, self.evaluation_context)
        damage_taken = damage_taken_from_target_state(self.target_combat_state)
        event = DDDamageEvent(
            base_value=float(formula_damage),
            scaling_coefficient=0.0,
            damage_type=damage_type,
            can_crit=True,
            is_dot=False,
            is_aoe=False,
        )
        raw = calculate_dd_damage(
            event,
            dd_stats,
            damage_taken=damage_taken,
            target_critical_resistance=self.target_critical_resistance,
        )
        mitigation = None
        if (
            self.evaluation_context.target_resistance is not None
            and raw.penetration_stat is not None
        ):
            mitigation = calculate_dd_mitigation(
                target_resistance=self.evaluation_context.target_resistance,
                penetration=raw.penetration,
            )
        resolved = calculate_dd_damage(
            event,
            dd_stats,
            mitigation=mitigation,
            damage_taken=damage_taken,
            target_critical_resistance=self.target_critical_resistance,
        )
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=float(resolved.final_damage),
        )

    def _formula_damage(self, weapon: HeavyAttackWeaponType) -> float | None:
        stats = self.evaluation.stats
        magicka = stats.value(StatId.MAX_MAGICKA)
        stamina = stats.value(StatId.MAX_STAMINA)
        spell_damage = stats.value(StatId.SPELL_DAMAGE)
        weapon_damage = stats.value(StatId.WEAPON_DAMAGE)

        skill2_ha_damage = _sum_contributions(self.evaluation, "skill2_ha_damage")
        cp_ha_damage = _sum_contributions(self.evaluation, "cp_ha_damage")
        skill_ha_damage = _sum_contributions(self.evaluation, "skill_ha_damage")
        set_ha_damage = _sum_contributions(self.evaluation, "set_ha_damage")
        direct_damage_done = _sum_contributions(self.evaluation, "direct_damage_done")
        single_target_damage_done = _sum_contributions(self.evaluation, "single_target_damage_done")
        runtime_damage_done = damage_done_from_combat_state(self.attacker_combat_state).generic
        exploiter_bonus = exploiter_damage_done_bonus(
            self.target_combat_state,
            _sum_contributions(
                self.evaluation,
                "conditional_exploiter_damage_done",
            ),
        )
        damage_done = (
            _sum_contributions(self.evaluation, "damage_done")
            + runtime_damage_done
            + exploiter_bonus
        )
        empower = _sum_contributions(self.evaluation, "empower")

        common = dict(
            magicka=magicka,
            stamina=stamina,
            skill2_ha_damage=skill2_ha_damage,
            cp_ha_damage=cp_ha_damage,
            skill_ha_damage=skill_ha_damage,
            set_ha_damage=set_ha_damage,
            direct_damage_done=direct_damage_done,
            single_target_damage_done=single_target_damage_done,
            damage_done=damage_done,
            empower=empower,
        )

        if weapon is HeavyAttackWeaponType.FIRE_STAFF:
            ha_spell = calculate_ha_flame_spell_damage(
                spell_damage=spell_damage,
                skill_bonus_spell_damage_flame=_sum_contributions(self.evaluation, "skill_bonus_spell_damage_flame"),
                skill2_ha_spell_damage=_sum_contributions(self.evaluation, "skill2_ha_spell_damage"),
                buff_spell_damage=_sum_contributions(self.evaluation, "buff_spell_damage"),
                skill_spell_damage=_sum_contributions(self.evaluation, "skill_spell_damage"),
            )
            ha_weapon = calculate_ha_flame_weapon_damage(
                weapon_damage=weapon_damage,
                skill_bonus_weapon_damage_flame=_sum_contributions(self.evaluation, "skill_bonus_weapon_damage_flame"),
                skill2_ha_weapon_damage=_sum_contributions(self.evaluation, "skill2_ha_weapon_damage"),
                buff_weapon_damage=_sum_contributions(self.evaluation, "buff_weapon_damage"),
                skill_weapon_damage=_sum_contributions(self.evaluation, "skill_weapon_damage"),
            )
            return calculate_ha_flame_staff(
                **common,
                ha_flame_spell_damage=ha_spell,
                ha_flame_weapon_damage=ha_weapon,
                flame_damage_done=_sum_contributions(self.evaluation, "flame_damage_done"),
            )

        if weapon is HeavyAttackWeaponType.FROST_STAFF:
            ha_spell = calculate_ha_frost_spell_damage(
                spell_damage=spell_damage,
                skill_bonus_spell_damage_frost=_sum_contributions(self.evaluation, "skill_bonus_spell_damage_frost"),
                skill2_la_spell_damage=_sum_contributions(self.evaluation, "skill2_la_spell_damage"),
                buff_spell_damage=_sum_contributions(self.evaluation, "buff_spell_damage"),
                skill_spell_damage=_sum_contributions(self.evaluation, "skill_spell_damage"),
            )
            ha_weapon = calculate_ha_frost_weapon_damage(
                weapon_damage=weapon_damage,
                skill_bonus_weapon_damage_frost=_sum_contributions(self.evaluation, "skill_bonus_weapon_damage_frost"),
                skill2_la_weapon_damage=_sum_contributions(self.evaluation, "skill2_la_weapon_damage"),
                buff_weapon_damage=_sum_contributions(self.evaluation, "buff_weapon_damage"),
                skill_weapon_damage=_sum_contributions(self.evaluation, "skill_weapon_damage"),
            )
            return calculate_ha_frost_staff(
                **common,
                ha_frost_spell_damage=ha_spell,
                ha_frost_weapon_damage=ha_weapon,
                frost_damage_done=_sum_contributions(self.evaluation, "frost_damage_done"),
            )

        if weapon is HeavyAttackWeaponType.SHOCK_STAFF:
            ha_spell = calculate_ha_shock_spell_damage(
                spell_damage=spell_damage,
                skill_bonus_spell_damage_shock=_sum_contributions(self.evaluation, "skill_bonus_spell_damage_shock"),
                skill2_ha_spell_damage=_sum_contributions(self.evaluation, "skill2_ha_spell_damage"),
                item_channel_spell_damage=_sum_contributions(self.evaluation, "item_channel_spell_damage"),
                buff_spell_damage=_sum_contributions(self.evaluation, "buff_spell_damage"),
                skill_spell_damage=_sum_contributions(self.evaluation, "skill_spell_damage"),
            )
            ha_weapon = calculate_ha_shock_weapon_damage(
                weapon_damage=weapon_damage,
                skill_bonus_weapon_damage_shock=_sum_contributions(self.evaluation, "skill_bonus_weapon_damage_shock"),
                skill2_ha_weapon_damage=_sum_contributions(self.evaluation, "skill2_ha_weapon_damage"),
                item_channel_weapon_damage=_sum_contributions(self.evaluation, "item_channel_weapon_damage"),
                buff_weapon_damage=_sum_contributions(self.evaluation, "buff_weapon_damage"),
                skill_weapon_damage=_sum_contributions(self.evaluation, "skill_weapon_damage"),
            )
            typed = _sum_contributions(self.evaluation, "shock_damage_done")
            final = calculate_ha_shock_staff_final(
                **common,
                ha_shock_spell_damage=ha_spell,
                ha_shock_weapon_damage=ha_weapon,
                shock_damage_done=typed,
            )
            return calculate_ha_shock_staff(
                **common,
                la_magic_spell_damage=ha_spell,
                la_magic_weapon_damage=ha_weapon,
                shock_damage_done=typed,
                ha_shock_staff_final=final,
            )

        if weapon is HeavyAttackWeaponType.RESTORATION_STAFF:
            ha_spell = calculate_ha_magic_spell_damage(
                spell_damage=spell_damage,
                skill_bonus_spell_damage_magic=_sum_contributions(self.evaluation, "skill_bonus_spell_damage_magic"),
                skill2_ha_spell_damage=_sum_contributions(self.evaluation, "skill2_ha_spell_damage"),
                item_channel_spell_damage=_sum_contributions(self.evaluation, "item_channel_spell_damage"),
                buff_spell_damage=_sum_contributions(self.evaluation, "buff_spell_damage"),
                skill_spell_damage=_sum_contributions(self.evaluation, "skill_spell_damage"),
            )
            ha_weapon = calculate_ha_magic_weapon_damage(
                weapon_damage=weapon_damage,
                skill_bonus_weapon_damage_magic=_sum_contributions(self.evaluation, "skill_bonus_weapon_damage_magic"),
                skill2_ha_weapon_damage=_sum_contributions(self.evaluation, "skill2_ha_weapon_damage"),
                item_channel_weapon_damage=_sum_contributions(self.evaluation, "item_channel_weapon_damage"),
                buff_weapon_damage=_sum_contributions(self.evaluation, "buff_weapon_damage"),
                skill_weapon_damage=_sum_contributions(self.evaluation, "skill_weapon_damage"),
            )
            typed = _sum_contributions(self.evaluation, "magic_damage_done")
            final = calculate_ha_restoration_final(
                **common,
                la_magic_spell_damage=ha_spell,
                la_magic_weapon_damage=ha_weapon,
                magic_damage_done=typed,
            )
            return calculate_ha_restoration(
                **common,
                la_magic_spell_damage=ha_spell,
                la_magic_weapon_damage=ha_weapon,
                magic_damage_done=typed,
                ha_restoration_final=final,
            )

        if weapon in {
            HeavyAttackWeaponType.TWO_HANDED,
            HeavyAttackWeaponType.DUAL_WIELD,
            HeavyAttackWeaponType.ONE_HAND_AND_SHIELD,
        }:
            ha_weapon = calculate_ha_physical_weapon_damage(
                weapon_damage=weapon_damage,
                skill_bonus_weapon_damage_physical=_sum_contributions(self.evaluation, "skill_bonus_weapon_damage_physical"),
                skill2_ha_weapon_damage=_sum_contributions(self.evaluation, "skill2_ha_weapon_damage"),
            )
            ha_spell = calculate_ha_physical_spell_damage(
                spell_damage=spell_damage,
                skill_bonus_spell_damage_physical=_sum_contributions(self.evaluation, "skill_bonus_spell_damage_physical"),
                skill2_ha_spell_damage=_sum_contributions(self.evaluation, "skill2_ha_spell_damage"),
                buff_spell_damage=_sum_contributions(self.evaluation, "buff_spell_damage"),
                skill_spell_damage=_sum_contributions(self.evaluation, "skill_spell_damage"),
            )
            physical = dict(
                **common,
                ha_physical_weapon_damage=ha_weapon,
                ha_physical_spell_damage=ha_spell,
                physical_damage_done=_sum_contributions(self.evaluation, "physical_damage_done"),
            )
            if weapon is HeavyAttackWeaponType.TWO_HANDED:
                return calculate_ha_two_hand(**physical)
            if weapon is HeavyAttackWeaponType.ONE_HAND_AND_SHIELD:
                return calculate_ha_one_hand(**physical)
            return calculate_ha_dual_wield(
                **physical,
                skill_line_damage_dual_wield=_sum_contributions(
                    self.evaluation,
                    "skill_line_damage_dual_wield",
                ),
            )

        return None

    def _completion_for(
        self,
        action: RotationAction,
    ) -> RotationHeavyAttackCompletionEvidence | None:
        matches = tuple(
            item
            for item in self.completion_evidence
            if item.action_time_seconds == action.time_seconds
            and item.action_sequence == action.sequence
        )
        if len(matches) > 1:
            raise ValueError(
                "duplicate heavy-attack completion evidence for "
                f"{action.time_seconds:.3f}s sequence {action.sequence}"
            )
        return matches[0] if matches else None

    @staticmethod
    def _unresolved(
        action: RotationAction,
        *messages: str,
    ) -> RotationActionDamageEvidence:
        return RotationActionDamageEvidence(
            time_seconds=action.time_seconds,
            sequence=action.sequence,
            damage_value=None,
            unresolved=tuple(
                dict.fromkeys(
                    str(message).strip()
                    for message in messages
                    if str(message).strip()
                )
            ),
        )


__all__ = ["RotationCandidateHeavyAttackDamageEvidenceService"]