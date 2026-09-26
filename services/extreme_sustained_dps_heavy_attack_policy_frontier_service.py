from __future__ import annotations

"""Explicit fully-charged Heavy Attack policy expansion for sustained-DPS search.

The caller supplies reviewed safe 1.8-second channel windows tied to exact scheduled
ordinary skill actions. This service owns only structural mutation and proof that the
resulting plan is promotable to canonical full-charge completion evidence.
"""

from dataclasses import dataclass
from itertools import combinations
import math
from typing import Callable

from minmax.rotation_plan import RotationAction, RotationActionKind, RotationPlan
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_heavy_sustain_projection_service import RotationHeavySustainProjectionService


_REVIEWED_FULL_CHARGE_SECONDS = 1.8
_EPSILON = 1e-9


@dataclass(frozen=True)
class ExtremeSustainedDPSHeavyAttackWindow:
    time_seconds: float
    sequence: int
    bar: str
    channel_seconds: float = _REVIEWED_FULL_CHARGE_SECONDS
    encounter_allows_channel: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.bar, str):
            raise TypeError("heavy-attack window bar must be a string")
        bar = self.bar.strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError("heavy-attack window bar must be front or back")
        if isinstance(self.time_seconds, bool) or not isinstance(self.time_seconds, (int, float)):
            raise TypeError("heavy-attack window time_seconds must be numeric")
        if not math.isfinite(float(self.time_seconds)) or float(self.time_seconds) < 0.0:
            raise ValueError("heavy-attack window time_seconds must be finite and non-negative")
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int):
            raise TypeError("heavy-attack window sequence must be an integer")
        if self.sequence < 0:
            raise ValueError("heavy-attack window sequence cannot be negative")
        if isinstance(self.channel_seconds, bool) or not isinstance(self.channel_seconds, (int, float)):
            raise TypeError("heavy-attack window channel_seconds must be numeric")
        if not math.isfinite(float(self.channel_seconds)):
            raise ValueError("heavy-attack window channel_seconds must be finite")
        if abs(float(self.channel_seconds) - _REVIEWED_FULL_CHARGE_SECONDS) > _EPSILON:
            raise ValueError("generated fully charged Heavy Attack window must use reviewed 1.8s timing")
        if not isinstance(self.encounter_allows_channel, bool):
            raise TypeError("heavy-attack window encounter_allows_channel must be boolean")
        object.__setattr__(self, "bar", bar)


@dataclass(frozen=True)
class ExtremeSustainedDPSHeavyAttackPolicyCandidate:
    policy_id: str
    candidate: GeneratedRotationCandidate
    selected_windows: tuple[ExtremeSustainedDPSHeavyAttackWindow, ...]
    completion_evidence_count: int
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


@dataclass(frozen=True)
class ExtremeSustainedDPSHeavyAttackPolicyFrontier:
    candidates: tuple[ExtremeSustainedDPSHeavyAttackPolicyCandidate, ...]
    denominator_proven: bool
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]


class ExtremeSustainedDPSHeavyAttackPolicyFrontierService:
    """Enumerate all non-overlapping explicit reviewed Heavy Attack windows."""

    @staticmethod
    def _window_target(
        plan: RotationPlan,
        window: ExtremeSustainedDPSHeavyAttackWindow,
    ) -> RotationAction | None:
        matches = tuple(
            action
            for action in plan.actions
            if action.kind is RotationActionKind.SKILL
            and abs(float(action.time_seconds) - float(window.time_seconds)) <= _EPSILON
            and int(action.sequence) == int(window.sequence)
            and action.bar == window.bar
        )
        return matches[0] if len(matches) == 1 else None

    @staticmethod
    def _window_end(window: ExtremeSustainedDPSHeavyAttackWindow) -> float:
        return round(float(window.time_seconds) + float(window.channel_seconds), 9)

    @classmethod
    def _compatible(
        cls,
        plan: RotationPlan,
        windows: tuple[ExtremeSustainedDPSHeavyAttackWindow, ...],
    ) -> bool:
        ordered = tuple(sorted(windows, key=lambda row: (row.time_seconds, row.sequence)))
        for prior, current in zip(ordered, ordered[1:]):
            if float(current.time_seconds) < cls._window_end(prior) - _EPSILON:
                return False

        selected_keys = {
            (float(row.time_seconds), int(row.sequence))
            for row in ordered
        }
        for window in ordered:
            if not window.encounter_allows_channel:
                return False
            if cls._window_target(plan, window) is None:
                return False
            end = cls._window_end(window)
            for action in plan.actions:
                key = (float(action.time_seconds), int(action.sequence))
                if key in selected_keys:
                    continue
                if abs(float(action.time_seconds) - float(window.time_seconds)) <= _EPSILON:
                    if action.kind is RotationActionKind.LIGHT_ATTACK and action.bar == window.bar:
                        continue
                if (
                    float(window.time_seconds) + _EPSILON
                    < float(action.time_seconds)
                    < end - _EPSILON
                ):
                    return False
        return True

    @classmethod
    def _mutate(
        cls,
        seed: GeneratedRotationCandidate,
        windows: tuple[ExtremeSustainedDPSHeavyAttackWindow, ...],
    ) -> GeneratedRotationCandidate:
        by_key = {
            (float(row.time_seconds), int(row.sequence)): row
            for row in windows
        }
        selected_times = {
            (float(row.time_seconds), row.bar)
            for row in windows
        }
        actions: list[RotationAction] = []
        for action in seed.plan.actions:
            key = (float(action.time_seconds), int(action.sequence))
            window = by_key.get(key)
            if window is not None:
                actions.append(
                    RotationAction(
                        time_seconds=action.time_seconds,
                        sequence=action.sequence,
                        kind=RotationActionKind.HEAVY_ATTACK,
                        name="Heavy Attack",
                        bar=action.bar,
                    )
                )
                continue
            if (
                action.kind is RotationActionKind.LIGHT_ATTACK
                and (float(action.time_seconds), action.bar) in selected_times
            ):
                continue
            actions.append(action)

        provenance = list(seed.plan.unresolved)
        assumptions = list(seed.plan.assumptions)
        for window in windows:
            end = cls._window_end(window)
            provenance.append(
                f"caller-proven heavy_attack at {float(window.time_seconds):g}s reserved "
                f"the {window.bar}-bar timeline through {end:g}s"
            )
            assumptions.append(
                f"generated sustained-DPS policy replaces one ordinary {window.bar}-bar skill "
                f"with a reviewed fully charged 1.8s Heavy Attack at {float(window.time_seconds):g}s"
            )

        plan = RotationPlan(
            character_name=seed.plan.character_name,
            build_name=seed.plan.build_name,
            duration_seconds=seed.plan.duration_seconds,
            actions=tuple(actions),
            assumptions=tuple(dict.fromkeys(assumptions)),
            unresolved=tuple(dict.fromkeys(provenance)),
        )
        return GeneratedRotationCandidate(
            candidate_id=(
                seed.candidate_id
                + "|heavy:"
                + ",".join(f"{row.time_seconds:g}/{row.sequence}" for row in windows)
            ),
            plan=plan,
            refresh_leads=seed.refresh_leads,
            action_claims=seed.action_claims,
        )

    def expand(
        self,
        *,
        seed: GeneratedRotationCandidate,
        windows: tuple[ExtremeSustainedDPSHeavyAttackWindow, ...],
        candidate_materializer: Callable[
            [tuple[ExtremeSustainedDPSHeavyAttackWindow, ...]],
            GeneratedRotationCandidate,
        ] | None = None,
    ) -> ExtremeSustainedDPSHeavyAttackPolicyFrontier:
        if not isinstance(windows, tuple):
            raise TypeError("heavy-attack policy windows must be a tuple")
        if any(not isinstance(window, ExtremeSustainedDPSHeavyAttackWindow) for window in windows):
            raise TypeError("heavy-attack policy windows must contain reviewed window records")
        unique: dict[tuple[float, int, str], ExtremeSustainedDPSHeavyAttackWindow] = {}
        unresolved: list[str] = []
        for window in windows:
            key = (float(window.time_seconds), int(window.sequence), window.bar)
            if key in unique:
                unresolved.append(
                    f"duplicate Heavy Attack policy window at {window.time_seconds:g}s sequence {window.sequence}"
                )
                continue
            unique[key] = window

        ordered = tuple(
            sorted(unique.values(), key=lambda row: (row.time_seconds, row.sequence, row.bar))
        )
        candidates = [
            ExtremeSustainedDPSHeavyAttackPolicyCandidate(
                policy_id="heavy:none",
                candidate=seed,
                selected_windows=(),
                completion_evidence_count=0,
                evidence=("Baseline plan preserves ordinary actions",),
                unresolved=(),
            )
        ]

        for size in range(1, len(ordered) + 1):
            for subset in combinations(ordered, size):
                if candidate_materializer is None:
                    if not self._compatible(seed.plan, subset):
                        continue
                    candidate = self._mutate(seed, subset)
                else:
                    try:
                        candidate = candidate_materializer(tuple(subset))
                    except ValueError:
                        continue
                completion = (
                    RotationHeavySustainProjectionService
                    .completion_evidence_from_verified_reservations(candidate.plan)
                )
                local_unresolved: list[str] = []
                if len(completion) != len(subset):
                    local_unresolved.append(
                        "generated Heavy Attack policy did not promote every selected "
                        "1.8s reservation to canonical full-charge completion evidence"
                    )
                candidates.append(
                    ExtremeSustainedDPSHeavyAttackPolicyCandidate(
                        policy_id=(
                            "heavy:"
                            + ",".join(
                                f"{row.time_seconds:g}/{row.sequence}"
                                for row in subset
                            )
                        ),
                        candidate=candidate,
                        selected_windows=subset,
                        completion_evidence_count=len(completion),
                        evidence=(
                            f"Selected reviewed Heavy Attack windows: {len(subset)}",
                            "Same-timestamp Light Attack is removed when a skill slot becomes a Heavy Attack",
                            "Canonical completion evidence promotion verifies each reviewed 1.8s reservation",
                        ),
                        unresolved=tuple(local_unresolved),
                    )
                )

        final_unresolved = tuple(
            dict.fromkeys(
                (
                    *unresolved,
                    *(
                        item
                        for row in candidates
                        for item in row.unresolved
                    ),
                )
            )
        )
        return ExtremeSustainedDPSHeavyAttackPolicyFrontier(
            candidates=tuple(candidates),
            denominator_proven=not final_unresolved,
            evidence=(
                f"Explicit Heavy Attack windows supplied: {len(ordered)}",
                f"Compatible Heavy Attack policy variants retained: {len(candidates)}",
                (
                    "Caller-supplied compatibility uses conservative exact-slot mutation"
                    if candidate_materializer is None
                    else "Canonical scheduler materialization validates every retained Heavy Attack subset"
                ),
                "Damage remains owned by RotationCandidateHeavyAttackDamageEvidenceService",
            ),
            unresolved=final_unresolved,
        )


__all__ = [
    "ExtremeSustainedDPSHeavyAttackPolicyCandidate",
    "ExtremeSustainedDPSHeavyAttackPolicyFrontier",
    "ExtremeSustainedDPSHeavyAttackPolicyFrontierService",
    "ExtremeSustainedDPSHeavyAttackWindow",
]
