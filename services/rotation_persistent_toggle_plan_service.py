from __future__ import annotations

from dataclasses import dataclass

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from minmax.rotation_recast import RotationRecastRule
from services.rotation_scribed_skill_damage_semantics_service import (
    RotationScribedSkillDamageSemanticsService,
)


@dataclass(frozen=True)
class RotationPersistentTogglePlanResult:
    plan: RotationPlan
    normalized_toggle_names: tuple[str, ...] = ()


class RotationPersistentTogglePlanService:
    """Normalize reviewed persistent toggles after ordinary duration refinement.

    The duration scheduler intentionally owns finite-duration recasts. Persistent
    toggles are different: once activated they have no timed refresh obligation.
    For a toggle represented on both bars, the first activation is preserved and
    later scheduled activations are replaced with deterministic same-bar ordinary
    fillers that have no finite-duration recast rule.

    A toggle represented on only one bar is left untouched because swapping away may
    deactivate it; that lifecycle needs explicit bar-aware runtime semantics rather
    than a global assumption. Unknown scribed results are ignored and remain owned by
    their ordinary planner path.
    """

    def __init__(
        self,
        *,
        semantics: RotationScribedSkillDamageSemanticsService | None = None,
    ) -> None:
        self.semantics = semantics or RotationScribedSkillDamageSemanticsService()

    def normalize(
        self,
        plan: RotationPlan,
        *,
        duration_rules: tuple[RotationRecastRule, ...] = (),
    ) -> RotationPersistentTogglePlanResult:
        toggle_names: dict[str, str] = {}
        toggle_bars: dict[str, set[str]] = {}
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            semantic = self.semantics.resolve(action.name)
            if semantic is None or not semantic.persistent_toggle:
                continue
            key = semantic.result_name.casefold()
            toggle_names.setdefault(key, semantic.result_name)
            if action.bar in {"front", "back"}:
                toggle_bars.setdefault(key, set()).add(str(action.bar))

        if not toggle_names:
            return RotationPersistentTogglePlanResult(plan=plan)

        duration_names = {rule.skill_name.casefold() for rule in duration_rules}
        fillers = self._fillers(
            plan,
            persistent_names=set(toggle_names),
            duration_names=duration_names,
        )
        filler_index = {"front": 0, "back": 0}
        activated: set[str] = set()
        normalized: set[str] = set()
        unresolved = list(plan.unresolved)
        assumptions = list(plan.assumptions)
        actions: list[RotationAction] = []

        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                actions.append(action)
                continue

            semantic = self.semantics.resolve(action.name)
            if semantic is None or not semantic.persistent_toggle:
                actions.append(action)
                continue

            key = semantic.result_name.casefold()
            bars = toggle_bars.get(key, set())
            if bars != {"front", "back"}:
                actions.append(action)
                unresolved.append(
                    f"persistent toggle '{semantic.result_name}' is not represented on both bars; "
                    "single-bar toggle lifetime across bar swaps is unresolved"
                )
                continue

            if key not in activated:
                activated.add(key)
                normalized.add(key)
                actions.append(action)
                assumptions.append(
                    f"reviewed persistent toggle '{semantic.result_name}' is activated once and remains active while double-barred"
                )
                continue

            replacement = self._next_filler(
                fillers=fillers,
                filler_index=filler_index,
                bar=action.bar,
            )
            if replacement is None:
                actions = self._remove_same_time_light_attack(actions, action)
                actions.append(
                    RotationAction(
                        time_seconds=action.time_seconds,
                        sequence=0,
                        kind=RotationActionKind.WAIT,
                        name=None,
                        bar=action.bar,
                    )
                )
                unresolved.append(
                    f"persistent toggle recast of '{semantic.result_name}' at {action.time_seconds:g}s "
                    "had no verified same-bar no-duration filler; scheduled wait instead"
                )
                continue

            actions.append(
                RotationAction(
                    time_seconds=action.time_seconds,
                    sequence=action.sequence,
                    kind=RotationActionKind.SKILL,
                    name=replacement,
                    bar=action.bar,
                )
            )
            unresolved.append(
                f"persistent toggle recast of '{semantic.result_name}' at {action.time_seconds:g}s was replaced "
                f"with same-bar filler '{replacement}'; exact priority ranking is unresolved"
            )

        normalized_plan = RotationPlan(
            character_name=plan.character_name,
            build_name=plan.build_name,
            duration_seconds=plan.duration_seconds,
            actions=tuple(actions),
            assumptions=tuple(self._dedupe(assumptions)),
            unresolved=tuple(self._dedupe(unresolved)),
        )
        return RotationPersistentTogglePlanResult(
            plan=normalized_plan,
            normalized_toggle_names=tuple(toggle_names[key] for key in sorted(normalized)),
        )

    def _fillers(
        self,
        plan: RotationPlan,
        *,
        persistent_names: set[str],
        duration_names: set[str],
    ) -> dict[str, tuple[str, ...]]:
        result: dict[str, list[str]] = {"front": [], "back": []}
        seen: dict[str, set[str]] = {"front": set(), "back": set()}
        for action in plan.actions:
            if action.kind is not RotationActionKind.SKILL or not action.name:
                continue
            if action.bar not in result:
                continue
            key = action.name.casefold()
            if key in persistent_names or key in duration_names or key in seen[action.bar]:
                continue
            seen[action.bar].add(key)
            result[action.bar].append(action.name)
        return {bar: tuple(values) for bar, values in result.items()}

    @staticmethod
    def _next_filler(
        *,
        fillers: dict[str, tuple[str, ...]],
        filler_index: dict[str, int],
        bar: str | None,
    ) -> str | None:
        if bar not in fillers or not fillers[bar]:
            return None
        values = fillers[bar]
        index = filler_index[bar] % len(values)
        filler_index[bar] += 1
        return values[index]

    @staticmethod
    def _remove_same_time_light_attack(
        actions: list[RotationAction],
        skill_action: RotationAction,
    ) -> list[RotationAction]:
        return [
            action
            for action in actions
            if not (
                action.kind is RotationActionKind.LIGHT_ATTACK
                and action.time_seconds == skill_action.time_seconds
                and action.bar == skill_action.bar
            )
        ]

    @staticmethod
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for raw in values:
            value = str(raw or "").strip()
            if not value:
                continue
            key = value.casefold()
            if key in seen:
                continue
            seen.add(key)
            ordered.append(value)
        return ordered


__all__ = [
    "RotationPersistentTogglePlanResult",
    "RotationPersistentTogglePlanService",
]
