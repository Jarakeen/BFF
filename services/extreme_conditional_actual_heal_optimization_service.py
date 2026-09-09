from __future__ import annotations

from dataclasses import replace

from minmax.character_progression import AttributeAllocation, CharacterProgression
from minmax.combat_state import CombatState
from minmax.potion_cadence import PotionCadence
from minmax.potion_use_event import PotionUseEventResolver
from models.build_model import PlayerBuild
from services.extreme_actual_heal_optimization_service import (
    ExtremeActualHealOptimizationResult,
    ExtremeActualHealOptimizationService,
)
from services.extreme_actual_heal_potion_candidate_service import (
    ExtremeActualHealPotionCandidateService,
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
from services.extreme_restoration_heavy_combat_state_service import (
    ExtremeRestorationHeavyCombatStateService,
)
from services.extreme_templar_restoring_light_healing_service import (
    ExtremeTemplarRestoringLightHealingService,
)
from services.extreme_templar_sacred_ground_combat_state_service import (
    ExtremeTemplarSacredGroundCombatStateService,
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
        healer_has_negative_effect: bool | None = None,
        active_crux: int | None = None,
        active_buffs: tuple[str, ...] = (),
        potion_elapsed_seconds: float | None = None,
        potion_use_resolver: PotionUseEventResolver | None = None,
        potion_candidates: ExtremeActualHealPotionCandidateService | None = None,
        restoration_heavy_state: ExtremeRestorationHeavyCombatStateService | None = None,
        templar_sacred_ground_state: ExtremeTemplarSacredGroundCombatStateService | None = None,
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
        self.healer_has_negative_effect = healer_has_negative_effect
        self.active_crux = active_crux
        self.active_buffs = tuple(
            dict.fromkeys(
                name
                for raw_name in active_buffs
                if (name := str(raw_name or "").strip())
            )
        )
        if potion_elapsed_seconds is None:
            self.potion_elapsed_seconds = None
        else:
            potion_elapsed = float(potion_elapsed_seconds)
            if potion_elapsed < 0.0:
                raise ValueError("potion_elapsed_seconds cannot be negative")
            self.potion_elapsed_seconds = potion_elapsed
        self.potion_use_resolver = potion_use_resolver
        self.potion_candidates = potion_candidates
        self.restoration_heavy_state = restoration_heavy_state
        self.templar_sacred_ground_state = templar_sacred_ground_state
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
        if self.potion_elapsed_seconds is not None:
            scenarios.append(
                "explicit saved-potion use window at "
                f"{self.potion_elapsed_seconds:.6f} seconds; "
                "Medicinal Use duration requires progression proof"
            )
        if self.sacred_ground_window_active:
            scenarios.append(
                "explicit Sacred Ground active/grace window; "
                "Sacred Ground Minor Mending requires canonical legality proof"
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
        _ = progression, entity_id, active_bar
        if self.potion_elapsed_seconds is None:
            return ()
        service = self.potion_candidates
        if service is None:
            service = ExtremeActualHealPotionCandidateService()
            self.potion_candidates = service
        return service.build_candidates(
            baseline_build,
            character_id=character_id,
            baseline_build_id=baseline_build_id,
        )

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

        if self.potion_elapsed_seconds is not None:
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
