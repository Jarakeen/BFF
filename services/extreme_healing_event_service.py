from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from engine.config import get_data_dir
from minmax.build_calculation_context import BuildCalculationContext
from minmax.character_build.weapon_type import WeaponSkillLine, WeaponType, resolve_weapon_skill_line
from minmax.eso_weapon_type_id import weapon_type_from_saved_name
from minmax.saved_build_skill_tooltip_service import SavedBuildSkillTooltipService
from minmax.skill_component_classification import SkillEffectKind
from minmax.skill_line_repository import SkillLineRepository
from minmax.skill_tooltip_calculator import SkillTooltipResult
from minmax.stat_ids import StatId
from models.build_model import PlayerBuild
from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
)
from services.extreme_necromancer_living_death_slotted_healing_service import (
    ExtremeNecromancerLivingDeathSlottedHealingService,
)
from services.extreme_nightblade_siphoning_healing_service import (
    ExtremeNightbladeSiphoningHealingService,
)
from services.extreme_warden_green_balance_healing_service import (
    ExtremeWardenGreenBalanceHealingService,
)


@dataclass(frozen=True)
class ExtremeHealingEventResult:
    """One reviewed healing event from an actual saved-build context.

    ``normal_heal`` is the sum of HEAL-classified coefficient components after
    the canonical saved-build actual-effect pipeline has applied sheet Healing
    Done and verified component-scoped healing CP. Reviewed active-bar Healing
    Done such as Soul Siphoner and Restoring Tether-family while-slotted effects,
    plus ability-family modifiers such as Restoration Master and Emerald Moss,
    are then applied in their own reviewed layers. Explicit situational inputs may
    add conditional modifiers such as Restoration Expert without pretending those
    conditions are always active.

    ``critical_heal`` is the largest reviewed value of the same event when every
    crit-eligible HEAL component crits. Components explicitly marked non-crittable
    stay at their normal value. Unknown critical eligibility blocks the critical
    result.

    Multi-recipient abilities are not aggregated into one recipient's heal unless
    component-recipient identity is proven. Their component traces remain
    available, but ``normal_heal`` and ``critical_heal`` stay unresolved.

    This is deliberately not an expected-value model and therefore does not
    multiply by critical chance.
    """

    entity_id: str
    normal_heal: float | None
    critical_heal: float | None
    critical_healing_bonus: float | None
    critical_multiplier: float | None
    heal_coefficient_numbers: tuple[int, ...]
    crit_eligible_coefficient_numbers: tuple[int, ...]
    noncrit_coefficient_numbers: tuple[int, ...]
    tooltip_result: SkillTooltipResult
    unresolved: tuple[str, ...]

    @property
    def mechanic_complete(self) -> bool:
        return (
            self.normal_heal is not None
            and self.critical_heal is not None
            and self.critical_healing_bonus is not None
            and not self.unresolved
        )


class ExtremeHealingEventService:
    """Evaluate one real heal without collapsing healing stats into one number.

    BFF already owns coefficient scaling, component classification, saved-build
    Healing Done, and healing CP semantics. This service composes those reviewed
    layers for the Extreme lab, adds reviewed active-bar Healing Done that is not
    yet represented in the canonical sheet context, applies reviewed
    ability-family and explicit situational healing modifiers, and adds the
    canonical 50% base critical healing multiplier from the UESP
    SpellCritHealing/WeaponCritHealing formula.

    Critical chance is intentionally absent. "Largest actual heal" asks how big
    the event can be when it crits; an expected-heal objective is a separate
    probability problem and must remain separate.
    """

    BASE_CRITICAL_HEALING = 0.50
    RESTORATION_MASTER_HEALING_MULTIPLIER = 1.05
    RESTORATION_EXPERT_HEALING_MULTIPLIER = 1.15
    RESTORATION_EXPERT_HEALTH_THRESHOLD = 0.30

    def __init__(
        self,
        *,
        database_path: Path | None = None,
        tooltip_service: SavedBuildSkillTooltipService | None = None,
        skill_line_repository: SkillLineRepository | None = None,
        recipient_scope: ExtremeHealingEventRecipientScopeService | None = None,
        nightblade_siphoning_healing: ExtremeNightbladeSiphoningHealingService | None = None,
        necromancer_living_death_slotted_healing: ExtremeNecromancerLivingDeathSlottedHealingService | None = None,
        warden_green_balance_healing: ExtremeWardenGreenBalanceHealingService | None = None,
    ) -> None:
        self.database_path = Path(database_path or get_data_dir() / "eso.db")
        self.tooltip_service = tooltip_service or SavedBuildSkillTooltipService(
            self.database_path
        )
        self.skill_line_repository = skill_line_repository or SkillLineRepository(
            self.database_path
        )
        self.recipient_scope = recipient_scope or ExtremeHealingEventRecipientScopeService()
        self.nightblade_siphoning_healing = (
            nightblade_siphoning_healing
            or ExtremeNightbladeSiphoningHealingService(
                self.database_path,
                skill_line_repository=self.skill_line_repository,
            )
        )
        self.necromancer_living_death_slotted_healing = (
            necromancer_living_death_slotted_healing
            or ExtremeNecromancerLivingDeathSlottedHealingService(
                self.database_path,
                skill_line_repository=self.skill_line_repository,
            )
        )
        self.warden_green_balance_healing = (
            warden_green_balance_healing
            or ExtremeWardenGreenBalanceHealingService(
                self.database_path,
                skill_line_repository=self.skill_line_repository,
            )
        )

    def evaluate(
        self,
        *,
        build: PlayerBuild,
        context: BuildCalculationContext,
        entity_id: str,
        target_health_fraction: float | None = None,
    ) -> ExtremeHealingEventResult:
        if target_health_fraction is not None:
            target_health_fraction = float(target_health_fraction)
            if not 0.0 <= target_health_fraction <= 1.0:
                raise ValueError("target_health_fraction must be between 0 and 1")

        result = self.tooltip_service.evaluate_entity_id(
            build=build,
            context=context,
            entity_id=entity_id,
        )
        unresolved = list(result.unresolved)

        skill_name = str(getattr(getattr(result, "skill", None), "name", "") or "").strip()
        recipient_scope = self.recipient_scope.resolve(ability_name=skill_name)
        unresolved.extend(recipient_scope.unresolved)
        single_recipient_safe = bool(recipient_scope.single_recipient_safe)

        heal_components = ()
        if result.skill is None:
            unresolved.append(f"{entity_id}: skill rank is unresolved")
        else:
            heal_components = tuple(
                component
                for component in self.tooltip_service.components.get_for_skill_rank(
                    result.skill.skill_rank_id
                )
                if component.effect_kind is SkillEffectKind.HEAL
            )
            if not heal_components:
                unresolved.append(f"{entity_id}: no HEAL-classified coefficient components")

        heal_numbers = tuple(int(component.coefficient_number) for component in heal_components)
        crit_eligible = tuple(
            int(component.coefficient_number)
            for component in heal_components
            if component.can_crit is True
        )
        noncrit = tuple(
            int(component.coefficient_number)
            for component in heal_components
            if component.can_crit is False
        )
        unknown_crit = tuple(
            int(component.coefficient_number)
            for component in heal_components
            if component.can_crit is None
        )
        if unknown_crit:
            unresolved.append(
                f"{entity_id}: HEAL critical eligibility unresolved for coefficient(s): "
                + ", ".join(str(number) for number in unknown_crit)
            )

        actual_by_number = {
            int(trace.coefficient_number): float(trace.output_value)
            for trace in result.component_actual_effect_trace
        }
        base_by_number = {
            int(trace.coefficient_number): float(trace.final_value)
            for trace in result.components
        }

        bar_multiplier, bar_unresolved = self._reviewed_bar_healing_multiplier(
            build=build,
            context=context,
        )
        unresolved.extend(bar_unresolved)
        ability_multiplier, family_unresolved = self._ability_family_healing_multiplier(
            build=build,
            context=context,
            result=result,
        )
        unresolved.extend(family_unresolved)
        situational_multiplier, situational_unresolved = self._situational_healing_multiplier(
            build=build,
            context=context,
            target_health_fraction=target_health_fraction,
        )
        unresolved.extend(situational_unresolved)
        healing_multiplier = bar_multiplier * ability_multiplier * situational_multiplier

        value_by_number: dict[int, float] = {}
        normal_heal: float | None = None
        if heal_numbers:
            missing = [
                number
                for number in heal_numbers
                if number not in actual_by_number and number not in base_by_number
            ]
            if missing:
                unresolved.append(
                    f"{entity_id}: HEAL coefficient values unavailable: "
                    + ", ".join(str(number) for number in missing)
                )
            elif single_recipient_safe:
                value_by_number = {
                    number: actual_by_number.get(number, base_by_number[number]) * healing_multiplier
                    for number in heal_numbers
                }
                normal_heal = sum(value_by_number.values())

        critical_bonus: float | None = None
        core_state = getattr(context, "core_state", None)
        if core_state is None:
            unresolved.append("Critical Healing requires canonical core_state")
        else:
            critical_trace = core_state.derived.get(StatId.CRITICAL_HEALING)
            if critical_trace is None:
                unresolved.append("Canonical Critical Healing stat is unavailable")
            else:
                critical_bonus = float(critical_trace.final_value)

        critical_multiplier: float | None = None
        critical_heal: float | None = None
        if critical_bonus is not None:
            critical_multiplier = 1.0 + self.BASE_CRITICAL_HEALING + critical_bonus
            if normal_heal is not None and not unknown_crit:
                critical_heal = sum(
                    value_by_number[number] * critical_multiplier
                    if number in crit_eligible
                    else value_by_number[number]
                    for number in heal_numbers
                )

        return ExtremeHealingEventResult(
            entity_id=str(entity_id),
            normal_heal=normal_heal,
            critical_heal=critical_heal,
            critical_healing_bonus=critical_bonus,
            critical_multiplier=critical_multiplier,
            heal_coefficient_numbers=heal_numbers,
            crit_eligible_coefficient_numbers=crit_eligible,
            noncrit_coefficient_numbers=noncrit,
            tooltip_result=result,
            unresolved=tuple(dict.fromkeys(message for message in unresolved if message)),
        )

    def _active_weapon_line(
        self,
        *,
        build: PlayerBuild,
        context: BuildCalculationContext,
    ) -> WeaponSkillLine | None:
        active_bar = str(getattr(context, "active_bar", "front") or "front").casefold()
        main, offhand = build.active_weapon_slots(active_bar)
        main_type = weapon_type_from_saved_name(main.WeaponType)
        offhand_type = weapon_type_from_saved_name(offhand.WeaponType)
        if main_type is None:
            return None
        if offhand_type is None:
            offhand_type = WeaponType.NONE
        try:
            return resolve_weapon_skill_line(main_type, offhand_type)
        except ValueError:
            return None

    def _maxed_passive_multiplier(
        self,
        *,
        context: BuildCalculationContext,
        passive_name: str,
        multiplier: float,
    ) -> tuple[float, tuple[str, ...]]:
        progression = getattr(context, "progression", None)
        if progression is None or not progression.owns_skill_line("Restoration Staff"):
            return 1.0, ()

        passive_ranks = getattr(progression, "passive_ranks", None)
        if passive_ranks is None:
            return 1.0, (f"{passive_name} passive rank is not recorded",)
        rank = progression.passive_rank(passive_name)
        if rank is None:
            return 1.0, (f"Passive rank is not recorded for character: {passive_name}",)
        if rank == 0:
            return 1.0, ()

        maximum = self.skill_line_repository.passive_max_rank(passive_name)
        if maximum is None:
            return 1.0, (f"Passive max rank is not available in canonical data: {passive_name}",)
        if rank != maximum:
            return 1.0, (f"Partial passive rank is not yet modeled: {passive_name} {rank}/{maximum}",)
        return multiplier, ()

    def _reviewed_bar_healing_multiplier(
        self,
        *,
        build: PlayerBuild,
        context: BuildCalculationContext,
    ) -> tuple[float, tuple[str, ...]]:
        active_bar = str(getattr(context, "active_bar", "front") or "front")
        multiplier = 1.0
        unresolved: list[str] = []

        progression = getattr(context, "progression", None)
        if progression is not None:
            siphoner = self.nightblade_siphoning_healing.resolve(
                build=build,
                progression=progression,
                active_bar=active_bar,
            )
            multiplier *= siphoner.multiplier
            unresolved.extend(siphoner.unresolved)

        living_death = self.necromancer_living_death_slotted_healing.resolve(
            build=build,
            active_bar=active_bar,
        )
        multiplier *= living_death.multiplier
        unresolved.extend(living_death.unresolved)

        return multiplier, tuple(dict.fromkeys(message for message in unresolved if message))

    def _ability_family_healing_multiplier(
        self,
        *,
        build: PlayerBuild,
        context: BuildCalculationContext,
        result: SkillTooltipResult,
    ) -> tuple[float, tuple[str, ...]]:
        skill = getattr(result, "skill", None)
        skill_name = str(getattr(skill, "name", "") or "").strip()
        if not skill_name:
            return 1.0, ()

        multiplier = 1.0
        unresolved: list[str] = []
        skill_line = self.skill_line_repository.skill_line_for_ability_name(skill_name)

        if str(skill_line or "").strip().casefold() == "restoration staff":
            if self._active_weapon_line(build=build, context=context) is WeaponSkillLine.RESTORATION_STAFF:
                restoration_multiplier, restoration_unresolved = self._maxed_passive_multiplier(
                    context=context,
                    passive_name="Restoration Master",
                    multiplier=self.RESTORATION_MASTER_HEALING_MULTIPLIER,
                )
                multiplier *= restoration_multiplier
                unresolved.extend(restoration_unresolved)

        progression = getattr(context, "progression", None)
        if progression is not None:
            emerald = self.warden_green_balance_healing.resolve(
                build=build,
                progression=progression,
                ability_name=skill_name,
                active_bar=str(getattr(context, "active_bar", "front") or "front"),
            )
            multiplier *= emerald.multiplier
            unresolved.extend(emerald.unresolved)

        return multiplier, tuple(dict.fromkeys(message for message in unresolved if message))

    def _situational_healing_multiplier(
        self,
        *,
        build: PlayerBuild,
        context: BuildCalculationContext,
        target_health_fraction: float | None,
    ) -> tuple[float, tuple[str, ...]]:
        if target_health_fraction is None:
            return 1.0, ()
        if target_health_fraction > self.RESTORATION_EXPERT_HEALTH_THRESHOLD:
            return 1.0, ()
        if self._active_weapon_line(build=build, context=context) is not WeaponSkillLine.RESTORATION_STAFF:
            return 1.0, ()

        return self._maxed_passive_multiplier(
            context=context,
            passive_name="Restoration Expert",
            multiplier=self.RESTORATION_EXPERT_HEALING_MULTIPLIER,
        )
