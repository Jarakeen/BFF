from __future__ import annotations

from dataclasses import dataclass, replace

from minmax.healer_heavy_attack_build_discovery import (
    HeavyAttackBuildIncentiveKind,
    discover_healer_heavy_attack_build_incentives,
)
from minmax.healer_wait_decision_provider import (
    HealerHeavyAttackCandidate,
    HealerWaitDecisionProvider,
)
from minmax.resource_costs import ResourceType
from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_definition import RotationDefinition, RotationMode, RotationStep
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.runtime_healer_wait_decision_provider import (
    RecoveryHeavyPressureResolver,
    RuntimeHealerWaitDecisionProvider,
)
from minmax.semi_static_rotation_planner import SemiStaticRotationPlanner
from services.rotation_duration_refinement_service import RotationDurationRefinementService
from services.rotation_heavy_attack_effect_duration_service import (
    RotationHeavyAttackEffectDurationService,
)
from services.rotation_recovery_heavy_replay_service import (
    RecoveryReserveAssessmentResolver,
    VerifiedRecoveryHeavyRestorationResolver,
)
from services.rotation_recovery_heavy_stabilization_service import (
    RotationRecoveryHeavyStabilizationResult,
    RotationRecoveryHeavyStabilizationService,
)
from services.rotation_ultimate_service import (
    RotationUltimateProjection,
    RotationUltimateService,
)
from ui.rotation_duration_evidence_support import (
    RotationDurationEvidence,
    RotationDurationEvidenceSupport,
)


@dataclass(frozen=True)
class RotationGenerationRequest:
    """UI-facing generation inputs for the current Phase 13 semi-static slice."""

    duration_seconds: float = 60.0
    rotation_type: str = "Semi-static"
    potion: str = ""
    potion_on_cooldown: bool = False
    weave_light_attacks: bool = True
    ultimate_bar: str = ""
    starting_ultimate: float = 0.0
    use_scheduled_combat_attacks_for_ultimate: bool = False
    ability_priorities: tuple[AbilityPriorityEntry, ...] = ()
    heavy_attack_candidates: tuple[HealerHeavyAttackCandidate, ...] = ()
    auto_required_heavy_attacks: bool = True
    required_heavy_channel_seconds: float = 1.8
    recovery_pressure_resolver: RecoveryHeavyPressureResolver | None = None
    stabilize_recovery_heavies: bool = False
    recovery_stabilization_resource: ResourceType = ResourceType.MAGICKA
    recovery_maximum_amount: int | None = None
    recovery_trigger_fraction: float | None = None
    recovery_restoration_resolver: VerifiedRecoveryHeavyRestorationResolver | None = None
    recovery_reserve_assessment_resolver: RecoveryReserveAssessmentResolver | None = None
    recovery_stabilization_max_iterations: int = 6


@dataclass(frozen=True)
class RotationGenerationResult:
    """One generated plan plus evidence produced while building it."""

    plan: RotationPlan
    duration_evidence: RotationDurationEvidence
    ultimate_projection: RotationUltimateProjection | None = None
    recovery_stabilization: RotationRecoveryHeavyStabilizationResult | None = None


class RotationGenerationSupport:
    """Translate saved-build UI state into authoritative planner contracts.

    Generation builds the deterministic saved-bar seed schedule, optionally orders
    ordinary skills by an explicit AbilityPriorityList, refines the plan using
    canonical positive skill durations and the same explicit priorities, optionally
    uses caller-proven healer heavy opportunities in slots that would otherwise be
    WAITs, and automatically discovers required-effect healer heavy incentives from
    saved-build state when enabled. When explicit recovery-pressure evidence is
    supplied, discovered recovery-value incentives may use the same safe channel
    reservation path.

    Recovery-heavy stabilization is opt-in and requires caller-verified restoration
    evidence plus an explicit resource maximum and recovery threshold. When enabled,
    generation iterates through the shared sustain replay service until the heavy
    schedule stabilizes or the configured hard iteration cap is reached. It then
    optionally projects one explicitly selected slot-6 ultimate through the shared
    Ultimate resource model. Potion cadence, execute rules, and dynamic bar timing
    remain later Phase 13 work.
    """

    def __init__(
        self,
        planner: SemiStaticRotationPlanner | None = None,
        duration_refinement: RotationDurationRefinementService | None = None,
        duration_evidence: RotationDurationEvidenceSupport | None = None,
        ultimate_service: RotationUltimateService | None = None,
        recovery_stabilization: RotationRecoveryHeavyStabilizationService | None = None,
        heavy_attack_effect_duration: RotationHeavyAttackEffectDurationService | None = None,
    ) -> None:
        self.planner = planner or SemiStaticRotationPlanner()
        self.duration_refinement = duration_refinement or RotationDurationRefinementService()
        self.duration_evidence = duration_evidence or RotationDurationEvidenceSupport()
        self.ultimate_service = ultimate_service or RotationUltimateService()
        self.recovery_stabilization = (
            recovery_stabilization or RotationRecoveryHeavyStabilizationService()
        )
        self.heavy_attack_effect_duration = (
            heavy_attack_effect_duration or RotationHeavyAttackEffectDurationService()
        )

    def generate(self, *, build, request: RotationGenerationRequest) -> RotationPlan:
        """Compatibility entry point returning only the final generated plan."""
        return self.generate_with_evidence(build=build, request=request).plan

    def generate_with_evidence(
        self,
        *,
        build,
        request: RotationGenerationRequest,
    ) -> RotationGenerationResult:
        """Return the final plan together with generation evidence."""
        if not request.stabilize_recovery_heavies:
            return self._generate_once(build=build, request=request)
        return self._generate_stabilized(build=build, request=request)

    def _generate_stabilized(
        self,
        *,
        build,
        request: RotationGenerationRequest,
    ) -> RotationGenerationResult:
        maximum = request.recovery_maximum_amount
        trigger = request.recovery_trigger_fraction
        restore = request.recovery_restoration_resolver
        if maximum is None or int(maximum) <= 0:
            raise ValueError(
                "recovery-heavy stabilization requires a positive recovery_maximum_amount"
            )
        if trigger is None or not 0 <= float(trigger) <= 1:
            raise ValueError(
                "recovery-heavy stabilization requires recovery_trigger_fraction between 0 and 1"
            )
        if restore is None:
            raise ValueError(
                "recovery-heavy stabilization requires a verified recovery_restoration_resolver"
            )

        generated_results: list[RotationGenerationResult] = []

        def generate(pressure_resolver: RecoveryHeavyPressureResolver | None) -> RotationPlan:
            iteration_request = replace(
                request,
                stabilize_recovery_heavies=False,
                recovery_pressure_resolver=pressure_resolver,
            )
            result = self._generate_once(build=build, request=iteration_request)
            generated_results.append(result)
            return result.plan

        stabilization = self.recovery_stabilization.stabilize(
            build=build,
            generate=generate,
            resource=request.recovery_stabilization_resource,
            maximum_amount=int(maximum),
            trigger_fraction=float(trigger),
            restoration_resolver=restore,
            reserve_assessment_resolver=request.recovery_reserve_assessment_resolver,
            max_iterations=int(request.recovery_stabilization_max_iterations),
        )
        if not generated_results:
            raise RuntimeError("recovery-heavy stabilization produced no generation pass")

        final_generated = generated_results[-1]
        return RotationGenerationResult(
            plan=stabilization.plan,
            duration_evidence=final_generated.duration_evidence,
            ultimate_projection=final_generated.ultimate_projection,
            recovery_stabilization=stabilization,
        )

    def _generate_once(
        self,
        *,
        build,
        request: RotationGenerationRequest,
    ) -> RotationGenerationResult:
        definition = self.build_definition(build=build, request=request)
        priority_list = self._priority_list(build=build, request=request)
        wait_decision = self._wait_decision(build=build, request=request)
        seed_plan = self.planner.build_plan(definition, build)

        if priority_list is None and wait_decision is None:
            refinement = self.duration_refinement.refine(seed_plan)
        elif priority_list is not None and wait_decision is None:
            refinement = self.duration_refinement.refine(
                seed_plan,
                priorities=priority_list,
            )
        elif priority_list is None:
            refinement = self.duration_refinement.refine(
                seed_plan,
                wait_decision=wait_decision,
            )
        else:
            refinement = self.duration_refinement.refine(
                seed_plan,
                priorities=priority_list,
                wait_decision=wait_decision,
            )

        final_plan = refinement.plan
        ultimate_projection: RotationUltimateProjection | None = None

        selected_ultimate_bar = str(request.ultimate_bar or "").strip().casefold()
        if selected_ultimate_bar:
            ultimate_projection = self.ultimate_service.apply_generation(
                build=build,
                plan=final_plan,
                ultimate_bar=selected_ultimate_bar,
                starting_ultimate=float(request.starting_ultimate),
                use_scheduled_combat_attacks=bool(
                    request.use_scheduled_combat_attacks_for_ultimate
                ),
            )
            final_plan = ultimate_projection.plan
            evidence = self.duration_evidence.build(final_plan)
        else:
            evidence = self.duration_evidence.from_projection(
                refinement.duration_projection
            )

        return RotationGenerationResult(
            plan=final_plan,
            duration_evidence=evidence,
            ultimate_projection=ultimate_projection,
        )

    def build_definition(
        self,
        *,
        build,
        request: RotationGenerationRequest,
    ) -> RotationDefinition:
        mode = self._mode(request.rotation_type)
        if mode is not RotationMode.SEMI_STATIC:
            raise ValueError(
                "Phase 13 currently generates only Semi-static rotations from the dashboard"
            )

        character_name = self._character_name(build)
        build_name = self._build_name(build)
        front_slots = self._ordinary_skill_slots(getattr(build, "FrontBarSkills", []))
        back_slots = self._ordinary_skill_slots(getattr(build, "BackBarSkills", []))
        priority_list = self._priority_list(build=build, request=request)

        front_skills = self._ordered_ordinary_skills(
            bar="front",
            slots=front_slots,
            priorities=priority_list,
        )
        back_skills = self._ordered_ordinary_skills(
            bar="back",
            slots=back_slots,
            priorities=priority_list,
        )

        steps: list[RotationStep] = []
        for skill in front_skills:
            steps.append(RotationStep(kind=RotationActionKind.SKILL, name=skill, bar="front"))

        if back_skills:
            steps.append(RotationStep(kind=RotationActionKind.BAR_SWAP, bar="back"))
            for skill in back_skills:
                steps.append(RotationStep(kind=RotationActionKind.SKILL, name=skill, bar="back"))
            if front_skills:
                steps.append(RotationStep(kind=RotationActionKind.BAR_SWAP, bar="front"))

        if not steps:
            raise ValueError("selected saved build has no ordinary slotted skills to schedule")

        assumptions = [
            "ordinary skill cadence uses the Phase 13 baseline 1.0s action interval",
            "canonical positive skill durations refine premature recast slots after seed generation",
        ]
        unresolved = [
            "execute-phase behavior is not yet scheduled",
        ]

        if priority_list is None:
            assumptions.append(
                "dashboard seed order follows saved front-bar slots then saved back-bar slots"
            )
            unresolved.append(
                "ability-priority editing has not yet replaced saved slot order"
            )
        else:
            assumptions.append(
                "dashboard seed and due-refresh selection use explicit ability priority values within each saved bar; lower numbers are higher priority"
            )

        if request.heavy_attack_candidates:
            assumptions.append(
                "caller-proven healer heavy-attack opportunities may replace premature-recast WAIT slots on the same active bar"
            )
        else:
            discovered = self._auto_heavy_incentives(build=build)
            if request.auto_required_heavy_attacks and any(
                incentive.kind is HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT
                for incentive in discovered
            ):
                assumptions.append(
                    "saved-build required-effect heavy incentives are discovered automatically and may reserve legal premature-recast windows"
                )
            if request.recovery_pressure_resolver is not None and any(
                incentive.kind is HeavyAttackBuildIncentiveKind.RECOVERY_VALUE
                for incentive in discovered
            ):
                assumptions.append(
                    "explicit runtime recovery pressure may use discovered recovery-value heavy incentives in legal premature-recast windows"
                )

        selected_ultimate_bar = str(request.ultimate_bar or "").strip().casefold()
        if selected_ultimate_bar:
            if selected_ultimate_bar not in {"front", "back"}:
                raise ValueError("ultimate bar must be 'front', 'back', or blank")
            assumptions.append(
                f"dashboard Ultimate projection explicitly selects the {selected_ultimate_bar} slot-6 ultimate"
            )
            if request.use_scheduled_combat_attacks_for_ultimate:
                assumptions.append(
                    "scheduled light/heavy attacks are treated as successful damaging attacks for base Ultimate generation"
                )
        else:
            unresolved.append(
                "ultimate timing is not scheduled because no ultimate bar is selected"
            )

        selected_potion = str(request.potion or "").strip()
        saved_potion = str(getattr(build, "Potion", "") or "").strip()
        if request.potion_on_cooldown and selected_potion and selected_potion.casefold() != "none":
            if not saved_potion:
                unresolved.append(
                    f"potion '{selected_potion}' selected for cooldown use but saved build has no potion"
                )
            elif selected_potion.casefold() != saved_potion.casefold():
                unresolved.append(
                    f"selected potion '{selected_potion}' does not match saved potion '{saved_potion}'"
                )
            else:
                unresolved.append(
                    "potion-on-cooldown cadence is selected but exact potion timing is not yet scheduled"
                )

        return RotationDefinition(
            character_name=character_name,
            build_name=build_name,
            duration_seconds=float(request.duration_seconds),
            steps=tuple(steps),
            mode=mode,
            action_interval_seconds=1.0,
            initial_bar="front" if front_skills else "back",
            weave_light_attacks=bool(request.weave_light_attacks),
            assumptions=tuple(assumptions),
            unresolved=tuple(unresolved),
        )

    def _wait_decision(self, *, build, request: RotationGenerationRequest):
        if request.heavy_attack_candidates:
            return HealerWaitDecisionProvider(tuple(request.heavy_attack_candidates))

        discovered = self._auto_heavy_incentives(build=build)
        if not discovered:
            return None

        incentives = []
        if request.auto_required_heavy_attacks:
            incentives.extend(
                incentive
                for incentive in discovered
                if incentive.kind is HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT
            )
        if request.recovery_pressure_resolver is not None:
            incentives.extend(
                incentive
                for incentive in discovered
                if incentive.kind is HeavyAttackBuildIncentiveKind.RECOVERY_VALUE
            )
        if not incentives:
            return None

        enriched = self.heavy_attack_effect_duration.enrich_saved_build(
            build=build,
            incentives=tuple(incentives),
        )
        incentives = list(enriched.incentives)

        channel = float(request.required_heavy_channel_seconds)
        if channel <= 0:
            raise ValueError("required heavy attack channel seconds must be positive")
        return RuntimeHealerWaitDecisionProvider(
            incentives=tuple(incentives),
            required_window_seconds=channel,
            recovery_pressure_resolver=request.recovery_pressure_resolver,
        )

    @staticmethod
    def _auto_heavy_incentives(*, build):
        if str(getattr(build, "Role", "") or "").strip().casefold() != "healer":
            return ()
        return tuple(discover_healer_heavy_attack_build_incentives(build))

    @classmethod
    def _auto_required_heavy_incentives(cls, *, build, request: RotationGenerationRequest):
        if not request.auto_required_heavy_attacks:
            return ()
        return tuple(
            incentive
            for incentive in cls._auto_heavy_incentives(build=build)
            if incentive.kind is HeavyAttackBuildIncentiveKind.REQUIRED_EFFECT
        )

    def _priority_list(
        self,
        *,
        build,
        request: RotationGenerationRequest,
    ) -> AbilityPriorityList | None:
        if not request.ability_priorities:
            return None

        priority_list = AbilityPriorityList(
            character_name=self._character_name(build),
            build_name=self._build_name(build),
            role=str(getattr(build, "Role", "") or "Unspecified").strip(),
            entries=tuple(request.ability_priorities),
        )
        front_slots = self._ordinary_skill_slots(getattr(build, "FrontBarSkills", []))
        back_slots = self._ordinary_skill_slots(getattr(build, "BackBarSkills", []))
        self._validate_priority_coverage(
            priority_list=priority_list,
            ordinary_slots=tuple(
                ("front", slot, skill) for slot, skill in front_slots
            ),
        )
        self._validate_priority_coverage(
            priority_list=priority_list,
            ordinary_slots=tuple(
                ("back", slot, skill) for slot, skill in back_slots
            ),
        )
        return priority_list

    @staticmethod
    def _mode(value: str) -> RotationMode:
        normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
        try:
            return RotationMode(normalized)
        except ValueError as exc:
            raise ValueError(f"unsupported rotation type: {value!r}") from exc

    @staticmethod
    def _ordinary_skill_slots(values) -> list[tuple[int, str]]:
        return [
            (slot, str(value).strip())
            for slot, value in enumerate(list(values or [])[:5], start=1)
            if str(value or "").strip()
        ]

    @staticmethod
    def _ordered_ordinary_skills(
        *,
        bar: str,
        slots: list[tuple[int, str]],
        priorities: AbilityPriorityList | None,
    ) -> list[str]:
        if priorities is None:
            return [skill for _, skill in slots]

        slot_map = {slot: skill for slot, skill in slots}
        return [
            item.entry.skill_name
            for item in priorities.resolve()
            if item.entry.bar == bar and item.entry.slot in slot_map
        ]

    @staticmethod
    def _validate_priority_coverage(
        *,
        priority_list: AbilityPriorityList,
        ordinary_slots,
    ) -> None:
        by_slot = {
            (item.entry.bar, item.entry.slot): item.entry
            for item in priority_list.resolve()
        }
        for bar, slot, skill in ordinary_slots:
            entry = by_slot.get((bar, slot))
            if entry is None:
                raise ValueError(
                    f"ability priority is missing for {bar} slot {slot}: {skill}"
                )
            if entry.skill_name != skill:
                raise ValueError(
                    "ability priority skill does not match saved slot: "
                    f"{entry.skill_name!r} != {skill!r} at {bar} slot {slot}"
                )

    @staticmethod
    def _character_name(build) -> str:
        return str(
            getattr(build, "CharacterName", "")
            or getattr(build, "Name", "")
            or getattr(build, "Gamertag", "")
            or ""
        ).strip()

    @staticmethod
    def _build_name(build) -> str:
        return str(getattr(build, "BuildName", "") or "Current Build").strip()
