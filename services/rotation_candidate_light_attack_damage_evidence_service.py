from __future__ import annotations

from dataclasses import replace

from minmax.build_evaluation import BuildEvaluation
from minmax.character_build.character_build import CharacterBuild
from minmax.character_build.weapon_type import WeaponType
from minmax.combat_damage_modifiers import (
    damage_done_from_combat_state,
    damage_taken_from_target_state,
)
from minmax.combat_state import CombatState
from minmax.dd_damage import DDDamageEvent, calculate_dd_damage
from minmax.dd_mitigation import calculate_dd_mitigation
from minmax.dd_stat_evaluation import evaluate_dd_stats
from minmax.evaluation_context import EvaluationContext
from minmax.light_attack_calculator import (
    calculate_bow_light_attack,
    calculate_flame_staff_light_attack,
    calculate_frost_staff_light_attack,
)
from minmax.light_attack_evaluation import resolve_light_attack_from_evaluation
from minmax.rotation_plan import RotationAction, RotationActionKind
from services.rotation_candidate_dd_role_output_service import RotationActionDamageEvidence
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_saved_build_dd_conditional_damage_done_service import (
    exploiter_damage_done_bonus,
)
from services.rotation_weapon_attack_projection_service import (
    RotationWeaponAttackProjectionService,
)


def _sum_contributions(evaluation: BuildEvaluation, *effect_types: str) -> float:
    wanted = set(effect_types)
    return sum(
        contribution.effective_value
        for contribution in evaluation.combat_contributions
        if contribution.effect_type in wanted
    )


class RotationCandidateLightAttackDamageEvidenceService:
    """Resolve supported scheduled light attacks through canonical weapon/LA math.

    Weapon identity and active-bar reconstruction remain owned by
    ``RotationWeaponAttackProjectionService``. Existing UESP-derived light-attack
    formulas own the flame/frost staff and bow pre-critical Damage Done result.
    Existing DD stat, critical, mitigation, and target Damage Taken services own the
    later combat stages.

    ``attacker_combat_state`` supplies reviewed transient attacker-side Damage Done
    such as Berserk at the exact attack instant. Target-state-dependent Exploiter is
    carried as a magnitude in the canonical weapon evaluation and joins that same
    additive Damage Done bucket only when the exact target state is Off Balance.
    Those modifiers are not applied again in the later DD stage.

    Flame staff, frost staff, and bow light attacks are fully routed here. Lightning
    staff remains unresolved because the currently preserved source formula uses HA,
    Empower, and DoT modifier buckets; treating that as ordinary direct damage would
    silently change the source mechanic. Other weapon families remain unresolved
    until their own canonical light-attack formulas are present.
    """

    def __init__(
        self,
        *,
        build: CharacterBuild,
        evaluation: BuildEvaluation,
        initial_bar: str,
        evaluation_context: EvaluationContext = EvaluationContext(),
        weapon_projection_service: RotationWeaponAttackProjectionService | None = None,
        attacker_combat_state: CombatState | None = None,
        target_combat_state: CombatState | None = None,
        target_critical_resistance: float = 0.0,
    ) -> None:
        self.build = build
        self.evaluation = evaluation
        self.initial_bar = str(initial_bar or "").strip().casefold()
        if self.initial_bar not in {"front", "back"}:
            raise ValueError("rotation light-attack initial_bar must be front or back")
        self.evaluation_context = evaluation_context
        self.weapon_projection_service = (
            weapon_projection_service or RotationWeaponAttackProjectionService()
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
        if action.kind is not RotationActionKind.LIGHT_ATTACK:
            return self._unresolved(
                action,
                f"{action.kind.value} damage requires its dedicated canonical action evaluator",
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
                "scheduled light attack has no resolved active-bar weapon identity",
            )

        state = resolve_light_attack_from_evaluation(evaluation=self.evaluation)
        runtime_damage_done = damage_done_from_combat_state(self.attacker_combat_state)
        exploiter_bonus = exploiter_damage_done_bonus(
            self.target_combat_state,
            _sum_contributions(
                self.evaluation,
                "conditional_exploiter_damage_done",
            ),
        )
        additive_damage_done = float(runtime_damage_done.generic) + float(exploiter_bonus)
        if additive_damage_done:
            state = replace(
                state,
                damage_done=state.damage_done + additive_damage_done,
            )

        if resolution.main_hand is WeaponType.FLAME_STAFF:
            formula_damage = calculate_flame_staff_light_attack(state)
            damage_type = "flame"
        elif resolution.main_hand is WeaponType.FROST_STAFF:
            formula_damage = calculate_frost_staff_light_attack(state)
            damage_type = "frost"
        elif resolution.main_hand is WeaponType.BOW:
            formula_damage = calculate_bow_light_attack(state)
            damage_type = "physical"
        elif resolution.main_hand is WeaponType.LIGHTNING_STAFF:
            return self._unresolved(
                action,
                "lightning staff light-attack combat semantics remain unresolved: "
                "the canonical source formula preserves HA, Empower, and DoT modifier buckets",
            )
        else:
            return self._unresolved(
                action,
                f"canonical light-attack damage formula unavailable for {resolution.main_hand.value}",
            )

        # Canonical LA formulas already apply their attacker-side Damage Done buckets.
        # Do not apply that bucket a second time here. This stage adds only expected
        # crit, target resistance mitigation, and explicit target-side Damage Taken.
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
                str(message).strip()
                for message in messages
                if str(message).strip()
            ),
        )


__all__ = ["RotationCandidateLightAttackDamageEvidenceService"]