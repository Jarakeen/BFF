from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_definition import RotationDefinition, RotationMode, RotationStep
from minmax.rotation_plan import RotationActionKind, RotationPlan
from minmax.semi_static_rotation_planner import SemiStaticRotationPlanner


@dataclass(frozen=True)
class RotationGenerationRequest:
    """UI-facing generation inputs for the first Phase 13 semi-static slice."""

    duration_seconds: float = 60.0
    rotation_type: str = "Semi-static"
    potion: str = ""
    potion_on_cooldown: bool = False
    weave_light_attacks: bool = True


class RotationGenerationSupport:
    """Translate saved-build UI state into the authoritative planner contracts.

    The first slice intentionally uses the saved bars as a deterministic authored
    sequence: five normal front-bar skills, explicit swap, five normal back-bar
    skills, explicit swap, then repeat. Ultimate, potion cadence, execute rules,
    priority editing, and dynamic recast logic remain explicit later Phase 13 work.
    """

    def __init__(self, planner: SemiStaticRotationPlanner | None = None) -> None:
        self.planner = planner or SemiStaticRotationPlanner()

    def generate(self, *, build, request: RotationGenerationRequest) -> RotationPlan:
        definition = self.build_definition(build=build, request=request)
        return self.planner.build_plan(definition, build)

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
            steps.append(
                RotationStep(
                    kind=RotationActionKind.SKILL,
                    name=skill,
                    bar="front",
                )
            )

        if back_skills:
            steps.append(
                RotationStep(kind=RotationActionKind.BAR_SWAP, bar="back")
            )
            for skill in back_skills:
                steps.append(
                    RotationStep(
                        kind=RotationActionKind.SKILL,
                        name=skill,
                        bar="back",
                    )
                )
            if front_skills:
                steps.append(
                    RotationStep(kind=RotationActionKind.BAR_SWAP, bar="front")
                )

        if not steps:
            raise ValueError("selected saved build has no ordinary slotted skills to schedule")

        assumptions = [
            "dashboard seed order follows saved front-bar slots then saved back-bar slots",
            "ordinary skill cadence uses the Phase 13 baseline 1.0s action interval",
        ]
        unresolved = [
            "ability-priority editing has not yet replaced saved slot order",
            "duration-aware recast timing has not yet been projected",
            "ultimate generation is not yet scheduled from dashboard seed order",
            "execute-phase behavior is not yet scheduled",
        ]

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
        return [
            str(value).strip()
            for value in list(values or [])[:5]
            if str(value or "").strip()
        ]

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
