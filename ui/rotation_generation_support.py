from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class RotationGenerationResult:
    """One generated plan plus evidence produced while building it."""

    plan: RotationPlan
    duration_evidence: RotationDurationEvidence
    ultimate_projection: RotationUltimateProjection | None = None


class RotationGenerationSupport:
    """Translate saved-build UI state into authoritative planner contracts.

    Generation builds the deterministic saved-bar seed schedule, refines it using
    canonical positive skill durations, optionally projects one explicitly selected
    slot-6 ultimate through the shared Ultimate resource model, then analyzes the
    final plan for dashboard duration evidence. Potion cadence, execute rules,
    editable priorities, and dynamic bar timing remain later Phase 13 work.
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
        seed_plan = self.planner.build_plan(definition, build)
        refinement = self.duration_refinement.refine(seed_plan)
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
        front_skills = self._ordinary_skills(getattr(build, "FrontBarSkills", []))
        back_skills = self._ordinary_skills(getattr(build, "BackBarSkills", []))

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
            "dashboard seed order follows saved front-bar slots then saved back-bar slots",
            "ordinary skill cadence uses the Phase 13 baseline 1.0s action interval",
            "canonical positive skill durations refine premature recast slots after seed generation",
        ]
        unresolved = [
            "ability-priority editing has not yet replaced saved slot order",
            "execute-phase behavior is not yet scheduled",
        ]

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

    @staticmethod
    def _mode(value: str) -> RotationMode:
        normalized = str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")
        try:
            return RotationMode(normalized)
        except ValueError as exc:
            raise ValueError(f"unsupported rotation type: {value!r}") from exc

    @staticmethod
    def _ordinary_skills(values) -> list[str]:
        return [str(value).strip() for value in list(values or [])[:5] if str(value or "").strip()]

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
