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
from services.extreme_critical_healing_cap_service import ExtremeCriticalHealingCapService
from services.extreme_healing_event_recipient_scope_service import (
    ExtremeHealingEventRecipientScopeService,
)
from services.extreme_healing_event_temporal_scope_service import (
    ExtremeHealingEventTemporalScopeService,
)
from services.extreme_necromancer_living_death_slotted_healing_service import (
    ExtremeNecromancerLivingDeathSlottedHealingService,
)
from services.extreme_nightblade_class_mastery_healing_service import (
    ExtremeNightbladeClassMasteryHealingService,
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
    the canonical saved-build actual-effect pipeline has applied the additive
    Healing Done bucket and verified component-scoped healing CP. Reviewed
    active-bar Healing Done such as Soul Siphoner and Restoring Tether-family
    while-slotted effects are fed into that same bucket. Ability-family modifiers
    such as Restoration Master and Emerald Moss remain separate reviewed layers.

    ``critical_heal`` is the largest reviewed value of the same event when every
    crit-eligible HEAL component crits. Components explicitly marked non-crittable
    stay at their normal value. Unknown critical eligibility blocks the critical
    result. Critical Healing is capped at the reviewed ESO ceiling; legal mastery
    effects may raise that ceiling explicitly rather than bypassing it.

    Multi-recipient abilities are not aggregated into one recipient's heal unless
    component-recipient identity is proven. Multi-time abilities are likewise not
    aggregated into one instant unless direct-versus-later component identity is
    proven. Their component traces remain available, but ``normal_heal`` and
    ``critical_heal`` stay unresolved.

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
    Healing Done, and healing CP semantics. This service feeds reviewed generic
    Healing Done into that canonical additive bucket, applies reviewed
    ability-family and explicit situational healing modifiers separately, and adds
    the canonical 50% base critical healing multiplier from the UESP
    SpellCritHealing/WeaponCritHealing formula.

    The resulting critical bonus is constrained by ESO's reviewed Critical
    Healing ceiling. Pure Nightblade ``Above and Beyond`` may legally add Critical
    Healing and raise that ceiling; subclassed builds cannot claim Class Mastery.

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
        temporal_scope: ExtremeHealingEventTemporalScopeService | None = None,
        critical_healing_cap: ExtremeCriticalHealingCapService | None = None,
        nightblade_class_mastery_healing: ExtremeNightbladeClassMasteryHealingService | None = None,
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
        self.temporal_scope = temporal_scope or ExtremeHealingEventTemporalScopeService()
        self.critical_healing_cap = critical_healing_cap or ExtremeCriticalHealingCapService()
        self.nightblade_class_mastery_healing = (
            nightblade_class_mastery_healing
            or ExtremeNightbladeClassMasteryHealingService(self.database_path)
        )
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
        additional_healing_done_bonus: float = 0.0,
        additional_healing_done_sources: tuple[str, ...] = (),
    ) -> ExtremeHealingEventResult:
        if target_health_fraction is not None:
            target_health_fraction = float(target_health_fraction)
            if not 0.0 <= target_health_fraction <= 1.0:
                raise ValueError("target_health_fraction must be between 0 and 1")

        bar_multiplier, bar_unresolved = self._reviewed_bar_healing_multiplier(
            build=build,
            context=context,
        )
        reviewed_healing_done_bonus = (
            float(bar_multiplier) - 1.0 + float(additional_healing_done_bonus)
        )
        reviewed_sources = list(additional_healing_done_sources)
        if abs(float(bar_multiplier) - 1.0) > 1e-12:
            reviewed_sources.append("Extreme reviewed active-bar Healing Done")

        result = self.tooltip_service.evaluate_entity_id(
            build=build,
            context=context,
            entity_id=entity_id,
            additional_healing_done_percent=reviewed_healing_done_bonus * 100.0,
            additional_healing_done_sources=tuple(reviewed_sources),
        )
        unresolved = list(bar_unresolved)
        unresolved.extend(result.unresolved)

        skill_name = str(getattr(getattr(result, "skill", None), "name", "") or "").strip()
        temporal_scope = self.temporal_scope.resolve(ability_name=skill_name)
        unresolved.extend(temporal_scope.unresolved)
        single_instant_safe = bool(temporal_scope.single_instant_safe)

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

        all_heal_numbers = tuple(
            int(component.coefficient_number) for component in heal_components
        )
        recipient_scope = self.recipient_scope.resolve(
            ability_name=skill_name,
            heal_coefficient_numbers=all_heal_numbers,
            coefficient_traces=tuple(result.components),
        )
        unresolved.extend(recipient_scope.unresolved)
        single_recipient_safe = bool(recipient_scope.single_recipient_safe)
        selected_numbers = recipient_scope.selected_coefficient_numbers
        if selected_numbers is not None:
            selected = {int(number) for number in selected_numbers}
            heal_components = tuple(
                component
                for component in heal_components
                if int(component.coefficient_number) in selected
            )

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
        healing_multiplier = ability_multiplier * situational_multiplier

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
            elif single_recipient_safe and single_instant_safe:
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

        event = ExtremeHealingEventResult(
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

        mastery = self.nightblade_class_mastery_healing.resolve(
            build=build,
            target_health_fraction=target_health_fraction,
            battle_spirit_active=False,
        )
        mastery_unresolved = list(mastery.unresolved)
        if any(
            str(name or "").strip().casefold() == "an eye for exploitation"
            for name in mastery.selected_masteries
        ):
            mastery_unresolved.append(
                "An Eye for Exploitation Weapon/Spell Damage contribution is not yet applied to the canonical heal coefficient context"
            )
        if mastery_unresolved:
            event = ExtremeHealingEventResult(
                entity_id=event.entity_id,
                normal_heal=event.normal_heal,
                critical_heal=event.critical_heal,
                critical_healing_bonus=event.critical_healing_bonus,
                critical_multiplier=event.critical_multiplier,
                heal_coefficient_numbers=event.heal_coefficient_numbers,
                crit_eligible_coefficient_numbers=event.crit_eligible_coefficient_numbers,
                noncrit_coefficient_numbers=event.noncrit_coefficient_numbers,
                tooltip_result=event.tooltip_result,
                unresolved=tuple(
                    dict.fromkeys((*event.unresolved, *mastery_unresolved))
                ),
            )

        return self.critical_healing_cap.apply(
            event,
            additional_critical_healing=float(mastery.critical_healing_bonus),
            critical_healing_cap=float(mastery.critical_healing_cap),
        ).event

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
        healing_done_bonus = 0.0
        unresolved: list[str] = []

        progression = getattr(context, "progression", None)
        if progression is not None:
            siphoner = self.nightblade_siphoning_healing.resolve(
                build=build,
                progression=progression,
                active_bar=active_bar,
            )
            healing_done_bonus += float(siphoner.multiplier) - 1.0
            unresolved.extend(siphoner.unresolved)

        living_death = self.necromancer_living_death_slotted_healing.resolve(
            build=build,
            active_bar=active_bar,
        )
        healing_done_bonus += float(living_death.multiplier) - 1.0
        unresolved.extend(living_death.unresolved)

        return 1.0 + healing_done_bonus, tuple(
            dict.fromkeys(message for message in unresolved if message)
        )

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