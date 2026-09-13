from __future__ import annotations

from types import SimpleNamespace

from minmax.combat_state import CombatState
from minmax.rotation_active_bar_legality import RotationActiveBarAssessor
from minmax.rotation_plan import RotationPlan
from models.build_model import PlayerBuild
from services.rotation_plan_persistent_toggle_combat_state_service import (
    RotationPlanPersistentToggleCombatStateService,
)


def build_plan_attacker_runtime_state_resolver(
    *,
    build: PlayerBuild,
    plan: RotationPlan,
    initial_bar: str = "front",
):
    """Return exact plan-derived attacker state for the standalone DD audit.

    The audit has no authoritative external runtime-history stream. It may still use
    runtime facts proven directly by the final plan itself. Reviewed persistent
    toggles are one such fact. This resolver deliberately projects only those
    plan-owned toggle semantics plus exact active-bar identity; it does not invent
    potion use, proc uptime, group buffs, sustain, or other runtime history.
    """

    bar_assessor = RotationActiveBarAssessor()
    toggle_state = RotationPlanPersistentToggleCombatStateService()
    start_bar = str(initial_bar or "front").strip().casefold()
    if start_bar not in {"front", "back"}:
        raise ValueError("DD audit attacker runtime initial_bar must be front or back")

    def resolve(time_seconds: float, sequence: int | None = None):
        instant = float(time_seconds)
        active_bar = bar_assessor.active_bar_at(
            plan,
            time_seconds=instant,
            sequence=sequence,
            initial_bar=start_bar,
        )
        projected = toggle_state.resolve(
            build,
            plan=plan,
            time_seconds=instant,
            sequence=sequence,
            base_combat_state=CombatState(),
        )
        return SimpleNamespace(
            time_seconds=instant,
            sequence=sequence,
            active_bar=active_bar,
            combat_state=projected.combat_state if projected.resolved else None,
            unresolved=tuple(projected.unresolved),
            resolved=bool(projected.resolved),
        )

    return resolve


__all__ = ["build_plan_attacker_runtime_state_resolver"]
