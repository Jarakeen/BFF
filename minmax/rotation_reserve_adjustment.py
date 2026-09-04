from __future__ import annotations

from dataclasses import dataclass

from .rotation_plan import RotationAction, RotationPlan
from .rotation_reserve_priority import RotationReserveProtectionPlan


@dataclass(frozen=True)
class ReserveProtectionActionBinding:
    """Explicit bridge from one reserve candidate to one scheduled action.

    Timeline candidates are identified by time/source while a RotationPlan also
    has an action sequence. Requiring this binding avoids guessing which action
    should be withheld when several actions share a timestamp or similar name.
    """

    candidate_time_seconds: float
    candidate_source: str
    action_time_seconds: float
    action_sequence: int

    def __post_init__(self) -> None:
        source = str(self.candidate_source or "").strip()
        if not source:
            raise ValueError("reserve adjustment candidate source is required")
        object.__setattr__(self, "candidate_source", source)

        if int(self.action_sequence) < 0:
            raise ValueError("reserve adjustment action sequence cannot be negative")
        object.__setattr__(self, "action_sequence", int(self.action_sequence))


@dataclass(frozen=True)
class WithheldRotationAction:
    action: RotationAction
    candidate_source: str
    recovered_amount: int


@dataclass(frozen=True)
class RotationReserveAdjustmentProposal:
    original_plan: RotationPlan
    adjusted_plan: RotationPlan
    protection_plan: RotationReserveProtectionPlan
    withheld_actions: tuple[WithheldRotationAction, ...]


def propose_rotation_reserve_adjustment(
    *,
    plan: RotationPlan,
    protection_plan: RotationReserveProtectionPlan,
    bindings: tuple[ReserveProtectionActionBinding, ...],
) -> RotationReserveAdjustmentProposal:
    """Return a new plan with selected reserve-protection actions withheld.

    This function does not invent a later recast time. It only applies the
    already-selected withholding decision. Rescheduling belongs to a separate
    policy-aware layer because moving a heal, DoT, taunt, or support skill after
    a demand window has role-specific consequences.
    """

    selected = protection_plan.selected_to_withhold
    selected_by_key = {
        (float(item.candidate.time_seconds), item.candidate.source): item
        for item in selected
    }

    binding_by_candidate: dict[tuple[float, str], ReserveProtectionActionBinding] = {}
    action_keys: set[tuple[float, int]] = set()
    for binding in bindings:
        candidate_key = (
            float(binding.candidate_time_seconds),
            binding.candidate_source,
        )
        if candidate_key in binding_by_candidate:
            raise ValueError(
                "duplicate reserve adjustment binding for candidate: "
                f"{binding.candidate_source} at {binding.candidate_time_seconds:g}s"
            )
        if candidate_key not in selected_by_key:
            raise ValueError(
                "reserve adjustment binding does not match a selected candidate: "
                f"{binding.candidate_source} at {binding.candidate_time_seconds:g}s"
            )

        action_key = (float(binding.action_time_seconds), binding.action_sequence)
        if action_key in action_keys:
            raise ValueError(
                "multiple reserve adjustment bindings target the same rotation action: "
                f"{binding.action_time_seconds:g}s sequence {binding.action_sequence}"
            )
        binding_by_candidate[candidate_key] = binding
        action_keys.add(action_key)

    missing = set(selected_by_key) - set(binding_by_candidate)
    if missing:
        time_seconds, source = sorted(missing)[0]
        raise ValueError(
            "selected reserve protection candidate is missing an action binding: "
            f"{source} at {time_seconds:g}s"
        )

    actions_by_key = {
        (float(action.time_seconds), action.sequence): action
        for action in plan.actions
    }
    withheld: list[WithheldRotationAction] = []
    remove_keys: set[tuple[float, int]] = set()

    for candidate_key, binding in binding_by_candidate.items():
        action_key = (float(binding.action_time_seconds), binding.action_sequence)
        action = actions_by_key.get(action_key)
        if action is None:
            raise ValueError(
                "reserve adjustment binding does not match a rotation action: "
                f"{binding.action_time_seconds:g}s sequence {binding.action_sequence}"
            )

        ranked = selected_by_key[candidate_key]
        candidate = ranked.candidate
        remove_keys.add(action_key)
        withheld.append(
            WithheldRotationAction(
                action=action,
                candidate_source=candidate.source,
                recovered_amount=candidate.amount,
            )
        )

    adjusted = RotationPlan(
        character_name=plan.character_name,
        build_name=plan.build_name,
        duration_seconds=plan.duration_seconds,
        actions=tuple(
            action
            for action in plan.actions
            if (float(action.time_seconds), action.sequence) not in remove_keys
        ),
        assumptions=plan.assumptions + (
            "reserve protection proposal withholds explicitly bound discretionary actions; no replacement timing is inferred",
        ),
        unresolved=plan.unresolved,
    )

    return RotationReserveAdjustmentProposal(
        original_plan=plan,
        adjusted_plan=adjusted,
        protection_plan=protection_plan,
        withheld_actions=tuple(
            sorted(
                withheld,
                key=lambda item: (item.action.time_seconds, item.action.sequence),
            )
        ),
    )
