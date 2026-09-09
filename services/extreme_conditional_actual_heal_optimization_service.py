from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.character_build.effect_relationship import ConditionContext
from minmax.combat_state import CombatState
from minmax.potion_cadence import PotionCadence
from minmax.potion_use_event import PotionUseEventResolver
from minmax.runtime_effect_eligibility import RuntimeEffectState
from minmax.runtime_event import RuntimeEvent
from models.build_model import PlayerBuild
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationResult,
    ExtremeActualHealOptimizationService,
)
from services.extreme_actual_heal_gear_runtime_buff_service import (
    ExtremeActualHealGearRuntimeBuffService,
)
from services.extreme_actual_heal_potion_candidate_service import (
    ExtremeActualHealPotionCandidateService,
)
from services.extreme_actual_heal_skill_buff_candidate_service import (
    ExtremeActualHealSkillBuffCandidateService,
)
from services.extreme_arcanist_cascading_fortune_healing_service import (
    ExtremeArcanistCascadingFortuneHealingService,
)
from services.extreme_arcanist_curative_runeforms_healing_service import (
    ExtremeArcanistCurativeRuneformsHealingService,
)
from services.extreme_healing_event_service import ExtremeHealingEventResult
from services.extreme_necromancer_living_death_healing_service import (
    ExtremeNecromancerLivingDeathHealingService,
)
from services.extreme_runtime_snapshot import ExtremeRuntimeSnapshot
from services.extreme_runtime_snapshot_combat_state_service import (
    ExtremeRuntimeSnapshotCombatStateService,
)
from services.extreme_restoration_heavy_combat_state_service import (
    ExtremeRestorationHeavyCombatStateService,
)
from services.extreme_templar_restoring_light_healing_service import (
    ExtremeTemplarRestoringLightHealingService,
)
from services.extreme_templar_sacred_ground_combat_state_service import (
    ExtremeTemplarSacredGroundCombatStateService,
)
from services.extreme_warden_accelerated_growth_combat_state_service import (
    ExtremeWardenAcceleratedGrowthCombatStateService,
)


class ExtremeConditionalActualHealOptimizationService(ExtremeActualHealOptimizationService):
    """Optimize one heal under explicit emergency/combat-state conditions.

    The ordinary ``ExtremeActualHealOptimizationService`` remains the standing
    result and does not activate target-health or trigger-dependent conditionals.
    This service forwards one explicit target-health fraction through every
    whole-build candidate rebuild.

    Reviewed Arcanist ``Healing Tides`` may be activated by an explicit active
    Crux count. At reviewed U50 max rank it contributes generic Healing Done per
    active Crux, so it can increase heals from any ability family. No Crux count
    is invented when the caller omits that scenario. Crux-consuming Remedy
    Cascade-family casts remain blocked from claiming this bonus until the
    consume-versus-heal snapshot order is canonically proven.

    Reviewed Arcanist ``Cascading Fortune`` is an ability-specific emergency-heal
    modifier. Its beam heals for up to 50% more in proportion to the target's
    missing health. It is applied only when the resolved event is Cascading
    Fortune and Curative Runeforms is legal for the build.

    Reviewed Templar ``Mending`` is also resolved here because its Restoring Light
    healing bonus scales continuously with the explicit target-health fraction.
    Keeping it in this conditional layer prevents the standing optimizer from
    inventing a target-health assumption merely to obtain a larger number.

    Reviewed Templar ``Sacred Ground`` may be activated by an explicit window
    state. When legal, it contributes Minor Mending through canonical
    ``CombatState`` rather than an ad-hoc heal multiplier. This permits legitimate
    Minor + Major Mending coexistence when both independent conditions are proven.

    Reviewed Necromancer ``Curative Curse`` may be activated by an explicit
    healer-negative-effect scenario. Its max-rank bonus is generic Healing Done,
    so once legally active it can increase heals from any ability family. The
    default ``None`` state means the caller did not request that scenario and no
    negative-effect assumption is invented.

    A caller may also state that a fully charged Restoration Staff heavy attack
    has just completed. When that trigger is requested, the reviewed Essence
    Drain resolver proves weapon/passive legality and routes Major Mending through
    canonical ``CombatState``. The +16% therefore remains owned by the named-buff
    Healing Done layer rather than becoming an ad-hoc event multiplier.

    Reviewed Warden ``Accelerated Growth`` may likewise be activated only by an
    explicit already-active post-trigger window. Its resolver proves Green Balance
    and passive-rank legality, then contributes Major Mending through canonical
    ``CombatState``. The triggering Green Balance heal itself is never assumed to
    benefit from the buff it creates.

    Conditional scenario assumptions are added to the returned search scope so a
    standalone optimization result cannot be mistaken for the ordinary standing
    maximum or for a different emergency/combat-state window.
    """

    CRUX_CONSUMING_REMEDY_CASCADE_FAMILY = frozenset(
        {"remedy cascade", "cascading fortune", "curative surge"}
    )

    def __init__(
        self,
        *,
        target_health_fraction: float,
        fully_charged_restoration_heavy_attack_completed: bool = False,
        sacred_ground_window_active: bool = False,
        accelerated_growth_window_active: bool = False,
        healer_has_negative_effect: bool | None = None,
        active_crux: int | None = None,
        active_buffs: tuple[str, ...] = (),
        runtime_snapshot: ExtremeRuntimeSnapshot | None = None,
        potion_elapsed_seconds: float | None = None,
        potion_use_resolver: PotionUseEventResolver | None = None,
        potion_candidates: ExtremeActualHealPotionCandidateService | None = None,
        skill_precast_elapsed_seconds: float | None = None,
        skill_buff_candidates: ExtremeActualHealSkillBuffCandidateService | None = None,
        skill_trigger_event: RuntimeEvent | None = None,
        skill_trigger_snapshot_seconds: float | None = None,
        skill_trigger_effect_state: RuntimeEffectState = RuntimeEffectState(),
        skill_trigger_chance_roll: float | None = None,
        skill_trigger_condition_context: ConditionContext | None = None,
        gear_trigger_event: RuntimeEvent | None = None,
        gear_trigger_snapshot_seconds: float | None = None,
        gear_trigger_effect_state: RuntimeEffectState = RuntimeEffectState(),
        gear_trigger_chance_roll: float | None = None,
        gear_trigger_condition_context: ConditionContext | None = None,
        gear_runtime_buffs: ExtremeActualHealGearRuntimeBuffService | None = None,
        runtime_snapshot_state: ExtremeRuntimeSnapshotCombatStateService | None = None,
        restoration_heavy_state: ExtremeRestorationHeavyCombatStateService | None = None,
        templar_sacred_ground_state: ExtremeTemplarSacredGroundCombatStateService | None = None,
        warden_accelerated_growth_state: ExtremeWardenAcceleratedGrowthCombatStateService | None = None,
        templar_restoring_light_healing: ExtremeTemplarRestoringLightHealingService | None = None,
        necromancer_living_death_healing: ExtremeNecromancerLivingDeathHealingService | None = None,
        arcanist_curative_runeforms_healing: ExtremeArcanistCurativeRuneformsHealingService | None = None,
        arcanist_cascading_fortune_healing: ExtremeArcanistCascadingFortuneHealingService | None = None,
        **kwargs,
    ) -> None:
        value = float(target_health_fraction)
        if not 0.0 <= value <= 1.0:
            raise ValueError("target_health_fraction must be between 0 and 1")
        if active_crux is not None:
            try:
                normalized_crux = int(active_crux)
            except (TypeError, ValueError) as exc:
                raise ValueError("active_crux must be an integer from 0 through 3") from exc
            if normalized_crux != active_crux or not 0 <= normalized_crux <= 3:
                raise ValueError("active_crux must be an integer from 0 through 3")
            active_crux = normalized_crux
        self.target_health_fraction = value
        self.fully_charged_restoration_heavy_attack_completed = bool(
            fully_charged_restoration_heavy_attack_completed
        )
        self.sacred_ground_window_active = bool(sacred_ground_window_active)
        self.accelerated_growth_window_active = bool(accelerated_growth_window_active)
        self.healer_has_negative_effect = healer_has_negative_effect
        self.active_crux = active_crux
        self.active_buffs = tuple(
            dict.fromkeys(
                name
                for raw_name in active_buffs
                if (name := str(raw_name or "").strip())
            )
        )
        self.runtime_snapshot = runtime_snapshot
        if runtime_snapshot is not None:
            if any(
                value is not None
                for value in (
                    skill_trigger_event,
                    skill_trigger_snapshot_seconds,
                    gear_trigger_event,
                    gear_trigger_snapshot_seconds,
                )
            ):
                raise ValueError(
                    "runtime_snapshot cannot be combined with legacy skill/gear trigger inputs"
                )
            if potion_elapsed_seconds is not None:
                raise ValueError(
                    "runtime_snapshot potion timing must be supplied on the snapshot contract"
                )
            potion_elapsed_seconds = runtime_snapshot.potion_elapsed_seconds
        if potion_elapsed_seconds is None:
            self.potion_elapsed_seconds = None
        else:
            potion_elapsed = float(potion_elapsed_seconds)
            if potion_elapsed < 0.0:
                raise ValueError("potion_elapsed_seconds cannot be negative")
            self.potion_elapsed_seconds = potion_elapsed
        self.potion_use_resolver = potion_use_resolver
        self.potion_candidates = potion_candidates
        if skill_precast_elapsed_seconds is None:
            self.skill_precast_elapsed_seconds = None
        else:
            skill_elapsed = float(skill_precast_elapsed_seconds)
            if skill_elapsed < 0.0:
                raise ValueError("skill_precast_elapsed_seconds cannot be negative")
            self.skill_precast_elapsed_seconds = skill_elapsed
        self.skill_buff_candidates = skill_buff_candidates
        if (skill_trigger_event is None) != (skill_trigger_snapshot_seconds is None):
            raise ValueError(
                "skill_trigger_event and skill_trigger_snapshot_seconds must be provided together"
            )
        if (
            skill_trigger_event is not None
            and float(skill_trigger_snapshot_seconds) < skill_trigger_event.time_seconds
        ):
            raise ValueError("skill trigger snapshot cannot precede the runtime event")
        self.skill_trigger_event = skill_trigger_event
        self.skill_trigger_snapshot_seconds = (
            None if skill_trigger_snapshot_seconds is None else float(skill_trigger_snapshot_seconds)
        )
        self.skill_trigger_effect_state = skill_trigger_effect_state
        self.skill_trigger_chance_roll = skill_trigger_chance_roll
        self.skill_trigger_condition_context = (
            None if skill_trigger_condition_context is None else frozenset(str(value) for value in skill_trigger_condition_context)
        )
        if (gear_trigger_event is None) != (gear_trigger_snapshot_seconds is None):
            raise ValueError(
                "gear_trigger_event and gear_trigger_snapshot_seconds must be provided together"
            )
        if (
            gear_trigger_event is not None
            and float(gear_trigger_snapshot_seconds) < gear_trigger_event.time_seconds
        ):
            raise ValueError("gear trigger snapshot cannot precede the runtime event")
        self.gear_trigger_event = gear_trigger_event
        self.gear_trigger_snapshot_seconds = (
            None if gear_trigger_snapshot_seconds is None else float(gear_trigger_snapshot_seconds)
        )
        self.gear_trigger_effect_state = gear_trigger_effect_state
        self.gear_trigger_chance_roll = gear_trigger_chance_roll
        self.gear_trigger_condition_context = (
            None if gear_trigger_condition_context is None else frozenset(str(value) for value in gear_trigger_condition_context)
        )
        self.gear_runtime_buffs = gear_runtime_buffs
        self.runtime_snapshot_state = runtime_snapshot_state
        self.restoration_heavy_state = restoration_heavy_state
        self.templar_sacred_ground_state = templar_sacred_ground_state
        self.warden_accelerated_growth_state = warden_accelerated_growth_state
        self.templar_restoring_light_healing = templar_restoring_light_healing
        self.necromancer_living_death_healing = necromancer_living_death_healing
        self.arcanist_curative_runeforms_healing = arcanist_curative_runeforms_healing
        self.arcanist_cascading_fortune_healing = arcanist_cascading_fortune_healing
        super().__init__(**kwargs)

    def optimize(
        self,
        baseline_build: PlayerBuild,
        entity_id: str,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        progression_override: CharacterProgression | None = None,
    ) -> ExtremeActualHealOptimizationResult:
        result = super().optimize(
            baseline_build,
            entity_id,
            active_bar=active_bar,
            max_passes=max_passes,
            progression_override=progression_override,
        )
        scenarios = [
            "explicit conditional target health fraction "
            f"{self.target_health_fraction:.6f}"
        ]
        if self.active_crux is not None:
            scenarios.append(
                f"explicit active Crux count {self.active_crux}; "
                "Healing Tides requires canonical legality proof"
            )
        if self.active_buffs:
            scenarios.append(
                "explicit active named buffs: " + ", ".join(self.active_buffs)
            )
        if self.runtime_snapshot is not None:
            scenarios.append(
                "unified runtime snapshot at "
                f"{self.runtime_snapshot.snapshot_time_seconds:.6f}s from "
                f"{len(self.runtime_snapshot.attempts)} ordered event attempts"
            )
        if self.potion_elapsed_seconds is not None:
            scenarios.append(
                "explicit saved-potion use window at "
                f"{self.potion_elapsed_seconds:.6f} seconds; "
                "Medicinal Use duration requires progression proof"
            )
        if self.skill_precast_elapsed_seconds is not None:
            scenarios.append(
                "explicit self-buff skill pre-cast window at "
                f"{self.skill_precast_elapsed_seconds:.6f} seconds; "
                "only unconditional self-target named buffs are discoverable"
            )
        if self.skill_trigger_event is not None:
            scenarios.append(
                "explicit triggered skill-buff runtime event "
                f"{self.skill_trigger_event.trigger!r} at {self.skill_trigger_event.time_seconds:.6f}s "
                f"with heal snapshot {self.skill_trigger_snapshot_seconds:.6f}s"
            )
            if self.skill_trigger_condition_context is not None:
                scenarios.append(
                    "explicit skill runtime conditions: "
                    + ", ".join(sorted(self.skill_trigger_condition_context))
                )
        if self.gear_trigger_event is not None:
            scenarios.append(
                "explicit gear-proc runtime event "
                f"{self.gear_trigger_event.trigger!r} at {self.gear_trigger_event.time_seconds:.6f}s "
                f"with heal snapshot {self.gear_trigger_snapshot_seconds:.6f}s; "
                "wearer self-application requires canonical SELF targeting"
            )
            if self.gear_trigger_condition_context is not None:
                scenarios.append(
                    "explicit gear runtime conditions: "
                    + ", ".join(sorted(self.gear_trigger_condition_context))
                )
        if self.sacred_ground_window_active:
            scenarios.append(
                "explicit Sacred Ground active/grace window; "
                "Sacred Ground Minor Mending requires canonical legality proof"
            )
        if self.accelerated_growth_window_active:
            scenarios.append(
                "explicit Accelerated Growth post-trigger window; "
                "Accelerated Growth Major Mending requires canonical legality proof"
            )
        if self.healer_has_negative_effect is not None:
            scenarios.append(
                "explicit healer negative-effect state "
                f"{str(bool(self.healer_has_negative_effect)).casefold()}; "
                "Curative Curse requires canonical legality proof"
            )
        if self.fully_charged_restoration_heavy_attack_completed:
            scenarios.append(
                "explicit fully charged Restoration Staff heavy attack completed; "
                "Essence Drain Major Mending requires canonical legality proof"
            )
        return replace(
            result,
            search_scope=(*scenarios, *result.search_scope),
        )

    def _additional_candidates(
        self,
        baseline_build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        baseline_build_id: str,
        entity_id: str,
        active_bar: str,
    ):
        _ = progression
        result = []
        if self.potion_elapsed_seconds is not None:
            service = self.potion_candidates
            if service is None:
                service = ExtremeActualHealPotionCandidateService()
                self.potion_candidates = service
            result.extend(
                service.build_candidates(
                    baseline_build,
                    character_id=character_id,
                    baseline_build_id=baseline_build_id,
                )
            )
        if self.skill_precast_elapsed_seconds is not None:
            service = self.skill_buff_candidates
            if service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    service = ExtremeActualHealSkillBuffCandidateService(database_path)
                    self.skill_buff_candidates = service
            if service is not None:
                result.extend(
                    service.build_candidates(
                        baseline_build,
                        character_id=character_id,
                        baseline_build_id=baseline_build_id,
                        protected_entity_id=entity_id,
                        active_bar=active_bar,
                    )
                )
        if self.runtime_snapshot is not None and self.runtime_snapshot.attempts:
            service = self.skill_buff_candidates
            if service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    service = ExtremeActualHealSkillBuffCandidateService(database_path)
                    self.skill_buff_candidates = service
            if service is not None:
                for attempt in self.runtime_snapshot.attempts:
                    result.extend(
                        service.triggered_build_candidates(
                            baseline_build,
                            character_id=character_id,
                            baseline_build_id=baseline_build_id,
                            protected_entity_id=entity_id,
                            active_bar=active_bar,
                            event=attempt.event,
                            snapshot_time_seconds=self.runtime_snapshot.snapshot_time_seconds,
                            chance_roll=attempt.chance_roll,
                            condition_context=attempt.condition_context,
                        )
                    )
        if self.skill_trigger_event is not None:
            service = self.skill_buff_candidates
            if service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    service = ExtremeActualHealSkillBuffCandidateService(database_path)
                    self.skill_buff_candidates = service
            if service is not None:
                result.extend(
                    service.triggered_build_candidates(
                        baseline_build,
                        character_id=character_id,
                        baseline_build_id=baseline_build_id,
                        protected_entity_id=entity_id,
                        active_bar=active_bar,
                        event=self.skill_trigger_event,
                        snapshot_time_seconds=self.skill_trigger_snapshot_seconds,
                        state=self.skill_trigger_effect_state,
                        chance_roll=self.skill_trigger_chance_roll,
                        condition_context=self.skill_trigger_condition_context,
                    )
                )
        return tuple(result)

    def _restoration_combat_state(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        active_bar: str,
    ) -> tuple[CombatState, tuple[str, ...]]:
        active_buffs: list[str] = list(self.active_buffs)
        unresolved: list[str] = []
        in_combat = False

        if self.skill_precast_elapsed_seconds is not None:
            service = self.skill_buff_candidates
            if service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    service = ExtremeActualHealSkillBuffCandidateService(database_path)
                    self.skill_buff_candidates = service
            if service is not None:
                active_buffs.extend(
                    service.active_named_buffs(
                        build,
                        active_bar=active_bar,
                        elapsed_seconds=self.skill_precast_elapsed_seconds,
                    )
                )

        if self.runtime_snapshot is not None:
            state_service = self.runtime_snapshot_state
            if state_service is None:
                state_service = ExtremeRuntimeSnapshotCombatStateService(
                    getattr(self.optimizer, "database_path", None),
                    skill_buff_candidates=self.skill_buff_candidates,
                    gear_runtime_buffs=self.gear_runtime_buffs,
                    potion_use_resolver=self.potion_use_resolver,
                )
                self.runtime_snapshot_state = state_service
            snapshot_result = state_service.resolve(
                build,
                progression=progression,
                active_bar=active_bar,
                snapshot=self.runtime_snapshot,
                base_active_buffs=tuple(active_buffs),
            )
            active_buffs = list(snapshot_result.combat_state.active_buffs)
            unresolved.extend(snapshot_result.unresolved)
            in_combat = in_combat or bool(snapshot_result.combat_state.in_combat)

        if self.skill_trigger_event is not None:
            service = self.skill_buff_candidates
            if service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    service = ExtremeActualHealSkillBuffCandidateService(database_path)
                    self.skill_buff_candidates = service
            if service is not None:
                active_buffs.extend(
                    service.active_triggered_named_buffs(
                        build,
                        active_bar=active_bar,
                        event=self.skill_trigger_event,
                        snapshot_time_seconds=self.skill_trigger_snapshot_seconds,
                        state=self.skill_trigger_effect_state,
                        chance_roll=self.skill_trigger_chance_roll,
                        condition_context=self.skill_trigger_condition_context,
                    )
                )

        if self.gear_trigger_event is not None:
            service = self.gear_runtime_buffs
            if service is None:
                database_path = getattr(self.optimizer, "database_path", None)
                if database_path is not None:
                    service = ExtremeActualHealGearRuntimeBuffService(database_path)
                    self.gear_runtime_buffs = service
            if service is not None:
                gear_result = service.resolve(
                    build,
                    active_bar=active_bar,
                    event=self.gear_trigger_event,
                    snapshot_time_seconds=self.gear_trigger_snapshot_seconds,
                    state=self.gear_trigger_effect_state,
                    chance_roll=self.gear_trigger_chance_roll,
                )
                active_buffs.extend(gear_result.active_buffs)
                unresolved.extend(gear_result.unresolved)

        if self.potion_elapsed_seconds is not None and self.runtime_snapshot is None:
            potion_name = " ".join(str(build.Potion or "").strip().split())
            if not potion_name:
                unresolved.append(
                    "Explicit potion-use window requested but build has no potion selection"
                )
            else:
                medicinal_use_rank = progression.passive_rank("Medicinal Use")
                if medicinal_use_rank is None:
                    unresolved.append(
                        "Medicinal Use rank is unresolved for explicit potion-use window"
                    )
                else:
                    resolver = self.potion_use_resolver
                    if resolver is None:
                        resolver = PotionUseEventResolver(
                            database_path=getattr(self.optimizer, "database_path", None)
                        )
                        self.potion_use_resolver = resolver
                    event = resolver.resolve(potion_name)
                    unresolved.extend(event.unresolved)
                    if event.resolved:
                        try:
                            cadence = PotionCadence(
                                event, medicinal_use_rank=medicinal_use_rank
                            )
                        except ValueError as exc:
                            unresolved.append(str(exc))
                        else:
                            active_buffs.extend(
                                cadence.window(
                                    self.potion_elapsed_seconds
                                ).active_buff_names
                            )

        if self.fully_charged_restoration_heavy_attack_completed:
            service = self.restoration_heavy_state
            if service is None:
                service = ExtremeRestorationHeavyCombatStateService(
                    getattr(self.optimizer, "database_path", None)
                )
                self.restoration_heavy_state = service
            result = service.resolve(
                build=build,
                progression=progression,
                active_bar=active_bar,
                fully_charged_heavy_attack_completed=True,
            )
            active_buffs.extend(result.combat_state.active_buffs)
            unresolved.extend(result.unresolved)
            in_combat = in_combat or bool(result.combat_state.in_combat)

        if self.sacred_ground_window_active:
            service = self.templar_sacred_ground_state
            if service is None:
                service = ExtremeTemplarSacredGroundCombatStateService(
                    getattr(self.optimizer, "database_path", None)
                )
                self.templar_sacred_ground_state = service
            result = service.resolve(
                build=build,
                progression=progression,
                sacred_ground_window_active=True,
            )
            active_buffs.extend(result.combat_state.active_buffs)
            unresolved.extend(result.unresolved)
            in_combat = in_combat or bool(result.combat_state.in_combat)

        if self.accelerated_growth_window_active:
            service = self.warden_accelerated_growth_state
            if service is None:
                service = ExtremeWardenAcceleratedGrowthCombatStateService()
                self.warden_accelerated_growth_state = service
            result = service.resolve(
                build=build,
                progression=progression,
                accelerated_growth_window_active=True,
            )
            active_buffs.extend(result.combat_state.active_buffs)
            unresolved.extend(result.unresolved)
            in_combat = in_combat or bool(result.combat_state.in_combat)

        return (
            CombatState(in_combat=in_combat, active_buffs=tuple(active_buffs)),
            tuple(dict.fromkeys(message for message in unresolved if message)),
        )

    def _templar_mending_event(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        event: ExtremeHealingEventResult,
    ) -> ExtremeHealingEventResult:
        tooltip_result = getattr(event, "tooltip_result", None)
        skill = getattr(tooltip_result, "skill", None)
        skill_name = str(getattr(skill, "name", "") or "").strip()
        if not skill_name:
            return event

        service = self.templar_restoring_light_healing
        if service is None:
            service = ExtremeTemplarRestoringLightHealingService(
                getattr(self.optimizer, "database_path", None)
            )
            self.templar_restoring_light_healing = service

        mending = service.resolve(
            build=build,
            progression=progression,
            ability_name=skill_name,
            target_health_fraction=self.target_health_fraction,
        )
        multiplier = float(mending.multiplier)
        normal_heal = (
            None if event.normal_heal is None else float(event.normal_heal) * multiplier
        )
        critical_heal = (
            None
            if event.critical_heal is None
            else float(event.critical_heal) * multiplier
        )
        unresolved = tuple(dict.fromkeys((*event.unresolved, *mending.unresolved)))
        return replace(
            event,
            normal_heal=normal_heal,
            critical_heal=critical_heal,
            unresolved=unresolved,
        )

    def _necromancer_curative_curse_event(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        event: ExtremeHealingEventResult,
    ) -> ExtremeHealingEventResult:
        if self.healer_has_negative_effect is None:
            return event

        service = self.necromancer_living_death_healing
        if service is None:
            service = ExtremeNecromancerLivingDeathHealingService(
                getattr(self.optimizer, "database_path", None)
            )
            self.necromancer_living_death_healing = service

        curse = service.resolve(
            build=build,
            progression=progression,
            has_negative_effect=self.healer_has_negative_effect,
        )
        multiplier = float(curse.multiplier)
        normal_heal = (
            None if event.normal_heal is None else float(event.normal_heal) * multiplier
        )
        critical_heal = (
            None
            if event.critical_heal is None
            else float(event.critical_heal) * multiplier
        )
        unresolved = tuple(dict.fromkeys((*event.unresolved, *curse.unresolved)))
        return replace(
            event,
            normal_heal=normal_heal,
            critical_heal=critical_heal,
            unresolved=unresolved,
        )

    def _arcanist_healing_tides_event(
        self,
        *,
        build: PlayerBuild,
        progression: CharacterProgression,
        event: ExtremeHealingEventResult,
    ) -> ExtremeHealingEventResult:
        if self.active_crux is None:
            return event

        tooltip_result = getattr(event, "tooltip_result", None)
        skill = getattr(tooltip_result, "skill", None)
        skill_name = str(getattr(skill, "name", "") or "").strip().casefold()
        if self.active_crux > 0 and skill_name in self.CRUX_CONSUMING_REMEDY_CASCADE_FAMILY:
            unresolved = tuple(
                dict.fromkeys(
                    (
                        *event.unresolved,
                        "Healing Tides timing is unresolved for a Crux-consuming "
                        "Remedy Cascade-family cast; active Crux may be consumed "
                        "before the heal snapshots Healing Done",
                    )
                )
            )
            return replace(event, unresolved=unresolved)

        service = self.arcanist_curative_runeforms_healing
        if service is None:
            service = ExtremeArcanistCurativeRuneformsHealingService(
                getattr(self.optimizer, "database_path", None)
            )
            self.arcanist_curative_runeforms_healing = service

        tides = service.resolve(
            build=build,
            progression=progression,
            active_crux=self.active_crux,
        )
        multiplier = float(tides.multiplier)
        normal_heal = (
            None if event.normal_heal is None else float(event.normal_heal) * multiplier
        )
        critical_heal = (
            None
            if event.critical_heal is None
            else float(event.critical_heal) * multiplier
        )
        unresolved = tuple(dict.fromkeys((*event.unresolved, *tides.unresolved)))
        return replace(
            event,
            normal_heal=normal_heal,
            critical_heal=critical_heal,
            unresolved=unresolved,
        )

    def _arcanist_cascading_fortune_event(
        self,
        *,
        build: PlayerBuild,
        event: ExtremeHealingEventResult,
    ) -> ExtremeHealingEventResult:
        tooltip_result = getattr(event, "tooltip_result", None)
        skill = getattr(tooltip_result, "skill", None)
        skill_name = str(getattr(skill, "name", "") or "").strip()
        if not skill_name:
            return event

        service = self.arcanist_cascading_fortune_healing
        if service is None:
            service = ExtremeArcanistCascadingFortuneHealingService()
            self.arcanist_cascading_fortune_healing = service

        fortune = service.resolve(
            build=build,
            ability_name=skill_name,
            target_health_fraction=self.target_health_fraction,
        )
        multiplier = float(fortune.multiplier)
        normal_heal = (
            None if event.normal_heal is None else float(event.normal_heal) * multiplier
        )
        critical_heal = (
            None
            if event.critical_heal is None
            else float(event.critical_heal) * multiplier
        )
        unresolved = tuple(dict.fromkeys((*event.unresolved, *fortune.unresolved)))
        return replace(
            event,
            normal_heal=normal_heal,
            critical_heal=critical_heal,
            unresolved=unresolved,
        )

    def _evaluate(
        self,
        build: PlayerBuild,
        *,
        progression: CharacterProgression,
        character_id: str,
        build_id: str,
        entity_id: str,
        active_bar: str,
    ) -> tuple[ExtremeHealingEventResult, tuple[str, ...]]:
        candidate_progression = replace(
            progression,
            attributes=AttributeAllocation(
                health=int(build.AttributeHealth or 0),
                magicka=int(build.AttributeMagicka or 0),
                stamina=int(build.AttributeStamina or 0),
            ),
        )
        combat_state, combat_unresolved = self._restoration_combat_state(
            build=build,
            progression=candidate_progression,
            active_bar=active_bar,
        )
        context = self.optimizer.context_factory.build(
            character_id=character_id,
            build_id=build_id,
            build=build,
            progression=candidate_progression,
            combat_state=combat_state,
            active_bar=active_bar,
        )
        event = self.healing_events.evaluate(
            build=build,
            context=context,
            entity_id=entity_id,
            target_health_fraction=self.target_health_fraction,
        )
        event = self._templar_mending_event(
            build=build,
            progression=candidate_progression,
            event=event,
        )
        event = self._necromancer_curative_curse_event(
            build=build,
            progression=candidate_progression,
            event=event,
        )
        event = self._arcanist_healing_tides_event(
            build=build,
            progression=candidate_progression,
            event=event,
        )
        event = self._arcanist_cascading_fortune_event(
            build=build,
            event=event,
        )
        unresolved = (
            tuple(context.unresolved_gear_effects)
            + tuple(combat_unresolved)
            + tuple(event.unresolved)
        )
        return event, tuple(dict.fromkeys(message for message in unresolved if message))
