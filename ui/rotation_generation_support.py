from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from minmax.rotation_definition import RotationDefinition, RotationMode, RotationStep
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.semi_static_rotation_planner import SemiStaticRotationPlanner
from services.rotation_duration_refinement_service import RotationDurationRefinementService
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


@dataclass(frozen=True)
class RotationGenerationResult:
    """One generated plan plus evidence produced while building it."""

    plan: RotationPlan
    duration_evidence: RotationDurationEvidence
    ultimate_projection: RotationUltimateProjection | None = None


class RotationGenerationSupport:
    """Translate saved-build UI state into authoritative planner contracts.

    Generation builds the deterministic saved-bar seed schedule, optionally orders
    ordinary skills by an explicit AbilityPriorityList, refines the plan using
    canonical positive skill durations and the same explicit priorities, optionally
    projects one explicitly selected slot-6 ultimate through the shared Ultimate
    resource model, then analyzes the final plan for dashboard duration evidence.
    Potion cadence, execute rules, and dynamic bar timing remain later Phase 13 work.
    """

    def __init__(
        self,
        planner: SemiStaticRotationPlanner | None = None,
        duration_refinement: RotationDurationRefinementService | None = None,
        duration_evidence: RotationDurationEvidenceSupport | None = None,
        ultimate_service: RotationUltimateService | None = None,
    ) -> None:
        self.planner = planner or SemiStaticRotationPlanner()
        self.duration_refinement = duration_refinement or RotationDurationRefinementService()
        self.duration_evidence = duration_evidence or RotationDurationEvidenceSupport()
        self.ultimate_service = ultimate_service or RotationUltimateService()

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
        definition = self.build_definition(build=build, request=request)
        priority_list = self._priority_list(build=build, request=request)
        seed_plan = self.planner.build_plan(definition, build)
        if priority_list is None:
            refinement = self.duration_refinement.refine(seed_plan)
        else:
            refinement = self.duration_refinement.refine(
                seed_plan,
                priorities=priority_list,
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
