from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_definition import RotationDefinition, RotationMode, RotationStep
from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan


@dataclass(frozen=True)
class SemiStaticRotationPlanner:
    """Produce a deterministic ``RotationPlan`` from one saved build definition.

    The planner validates authored intent against the saved build's bars. It does
    not calculate costs, damage, healing, effects, proc results, or encounter
    consequences. Those remain owned by the existing Phase 3/4/7/8 systems.
    """

    def build_plan(self, definition: RotationDefinition, build) -> RotationPlan:
        if definition.mode is not RotationMode.SEMI_STATIC:
            raise ValueError(
                "semi-static planner only accepts RotationMode.SEMI_STATIC definitions"
            )

        self._validate_identity(definition, build)

        unresolved = list(definition.unresolved)
        assumptions = list(definition.assumptions)
        assumptions.append(
            f"semi-static authored steps repeat every {definition.action_interval_seconds:g}s"
        )
        if definition.weave_light_attacks:
            assumptions.append(
                "light attacks are ordered immediately before eligible skill/ultimate actions "
                "at the same schedule timestamp; sub-GCD animation timing is unresolved"
            )

        actions: list[RotationAction] = []
        current_bar = definition.initial_bar
        step_index = 0
        time_seconds = 0.0

        while time_seconds <= definition.duration_seconds:
            step = definition.steps[step_index % len(definition.steps)]
            step_actions, current_bar, step_unresolved = self._schedule_step(
                step=step,
                build=build,
                current_bar=current_bar,
                time_seconds=time_seconds,
                weave_light_attacks=definition.weave_light_attacks,
            )
            actions.extend(step_actions)
            unresolved.extend(step_unresolved)
            step_index += 1
            time_seconds = round(
                step_index * definition.action_interval_seconds,
                9,
            )

        return RotationPlan(
            character_name=definition.character_name,
            build_name=definition.build_name,
            duration_seconds=definition.duration_seconds,
            actions=tuple(actions),
            assumptions=tuple(self._dedupe(assumptions)),
            unresolved=tuple(self._dedupe(unresolved)),
        )

    @staticmethod
    def _validate_identity(definition: RotationDefinition, build) -> None:
        character_name = str(
            getattr(build, "CharacterName", "")
            or getattr(build, "Name", "")
            or ""
        ).strip()
        build_name = str(getattr(build, "BuildName", "") or "Current Build").strip()

        if not character_name or character_name.casefold() != definition.character_name.casefold():
            raise ValueError(
                "rotation definition character identity does not match the selected saved build"
            )
        if build_name.casefold() != definition.build_name.casefold():
            raise ValueError(
                "rotation definition build identity does not match the selected saved build"
            )

    def _schedule_step(
        self,
        *,
        step: RotationStep,
        build,
        current_bar: str,
        time_seconds: float,
        weave_light_attacks: bool,
    ) -> tuple[list[RotationAction], str, list[str]]:
        unresolved: list[str] = []

        if step.kind is RotationActionKind.BAR_SWAP:
            destination = str(step.bar)
            if destination == current_bar:
                unresolved.append(
                    f"bar swap to {destination} at {time_seconds:g}s is redundant; already on that bar"
                )
            return (
                [
                    RotationAction(
                        time_seconds=time_seconds,
                        sequence=0,
                        kind=RotationActionKind.BAR_SWAP,
                        bar=destination,
                    )
                ],
                destination,
                unresolved,
            )

        if step.kind in {RotationActionKind.SKILL, RotationActionKind.ULTIMATE}:
            requested_bar = str(step.bar)
            if requested_bar != current_bar:
                unresolved.append(
                    f"{step.kind.value} '{step.name}' at {time_seconds:g}s requires {requested_bar} bar "
                    f"but current bar is {current_bar}; add an explicit bar swap"
                )
                return [], current_bar, unresolved

            if not self._is_slotted(build, requested_bar, step.kind, str(step.name)):
                slot_scope = "ultimate slot" if step.kind is RotationActionKind.ULTIMATE else "skill slots"
                unresolved.append(
                    f"{step.kind.value} '{step.name}' is not present in saved {requested_bar}-bar {slot_scope}"
                )
                return [], current_bar, unresolved

            actions: list[RotationAction] = []
            if weave_light_attacks:
                actions.append(
                    RotationAction(
                        time_seconds=time_seconds,
                        sequence=0,
                        kind=RotationActionKind.LIGHT_ATTACK,
                        bar=current_bar,
                    )
                )
                action_sequence = 1
            else:
                action_sequence = 0

            actions.append(
                RotationAction(
                    time_seconds=time_seconds,
                    sequence=action_sequence,
                    kind=step.kind,
                    name=step.name,
                    bar=current_bar,
                )
            )
            return actions, current_bar, unresolved

        if step.kind is RotationActionKind.POTION:
            saved_potion = str(getattr(build, "Potion", "") or "").strip()
            if not saved_potion:
                unresolved.append(
                    f"potion '{step.name}' requested at {time_seconds:g}s but the saved build has no potion"
                )
                return [], current_bar, unresolved
            if saved_potion.casefold() != str(step.name).casefold():
                unresolved.append(
                    f"potion '{step.name}' requested at {time_seconds:g}s does not match saved potion '{saved_potion}'"
                )
                return [], current_bar, unresolved

        action_bar = step.bar or current_bar
        return (
            [
                RotationAction(
                    time_seconds=time_seconds,
                    sequence=0,
                    kind=step.kind,
                    name=step.name,
                    bar=action_bar,
                )
            ],
            current_bar,
            unresolved,
        )

    @staticmethod
    def _is_slotted(build, bar: str, kind: RotationActionKind, name: str) -> bool:
        values = list(
            getattr(build, "FrontBarSkills" if bar == "front" else "BackBarSkills", [])
            or []
        )
        normalized = name.strip().casefold()
        if kind is RotationActionKind.ULTIMATE:
            candidates = values[5:6]
        else:
            candidates = values[:5]
        return any(str(value or "").strip().casefold() == normalized for value in candidates)

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return ordered
