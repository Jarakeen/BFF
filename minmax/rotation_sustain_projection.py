from __future__ import annotations

from dataclasses import dataclass

from .build_sustain import NamedBuildAction
from .rotation_plan import RotationActionKind, RotationPlan


@dataclass(frozen=True)
class RotationSustainProjection:
    """Phase 13 schedule projected into the existing Phase 4 sustain contract.

    Only named skill costs can be projected without additional verified inputs.
    Other action kinds remain explicit boundaries rather than being assigned fake
    zero-cost or restoration behavior.
    """

    actions: tuple[NamedBuildAction, ...]
    unresolved: tuple[str, ...] = ()


def project_rotation_plan_to_sustain(
    plan: RotationPlan,
) -> RotationSustainProjection:
    """Translate one rotation schedule into Phase 4 named cost actions.

    Damage, healing, effect, proc, and resource consequence math remains outside
    this adapter. Light attacks, bar swaps, and waits require no named skill-cost
    lookup. Heavy attacks, potions, and Ultimates can alter resource state, but
    they require consumers with additional verified inputs and therefore remain
    explicit unresolved sustain boundaries here.
    """

    actions: list[NamedBuildAction] = []
    unresolved: list[str] = list(plan.unresolved)

    for action in plan.actions:
        if action.kind is RotationActionKind.SKILL:
            assert action.name is not None
            actions.append(
                NamedBuildAction(
                    time_seconds=action.time_seconds,
                    skill_name=action.name,
                )
            )
            continue

        if action.kind in {
            RotationActionKind.LIGHT_ATTACK,
            RotationActionKind.BAR_SWAP,
            RotationActionKind.WAIT,
        }:
            continue

        if action.kind is RotationActionKind.HEAVY_ATTACK:
            unresolved.append(
                f"{action.time_seconds:g}s heavy_attack: sustain restoration requires "
                "verified weapon-specific heavy-attack inputs"
            )
            continue

        if action.kind is RotationActionKind.POTION:
            unresolved.append(
                f"{action.time_seconds:g}s potion {action.name!r}: sustain restoration "
                "requires explicit canonical potion activation/restoration projection"
            )
            continue

        if action.kind is RotationActionKind.ULTIMATE:
            unresolved.append(
                f"{action.time_seconds:g}s ultimate {action.name!r}: primary-resource "
                "sustain projection does not model Ultimate resource spending"
            )
            continue

        raise AssertionError(f"Unhandled rotation action kind: {action.kind!r}")

    return RotationSustainProjection(
        actions=tuple(actions),
        unresolved=tuple(unresolved),
    )
