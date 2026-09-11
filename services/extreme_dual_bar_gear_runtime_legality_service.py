from __future__ import annotations

"""Gate gear-proc runtime attempts by proven bar-local set activation.

A legal two-bar build can carry set bonuses that exist only on one weapon bar.
Proc attempts therefore need two separate proofs:

* the required set breakpoint was active on the bar where the trigger occurred;
* once legally triggered, the ordinary shared runtime window/cooldown machinery
  decides whether the effect is still active at the requested snapshot.

This service owns no set-count math and no proc math. Bar-local breakpoint truth
comes from ``ExtremeDualBarSetActivationEvidenceCatalog`` and runtime transitions
remain owned by the existing shared effect stream helpers.
"""

from dataclasses import dataclass
import re

from minmax.character_build.effect_layer import EffectLayer
from minmax.gear_set_effect_variant_resolver import GearSetEffectVariantResolver
from minmax.named_combat_buffs import canonical_buff_name, effects_for_buff
from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.runtime_effect_stream import process_effect_variant_runtime_stream
from minmax.runtime_effect_window import partition_runtime_effect_windows
from minmax.runtime_event import runtime_event_matches_effect_variant
from minmax.support_target_type import SupportTargetType
from services.extreme_dual_bar_set_activation_evidence_service import (
    ExtremeDualBarSetActivationEvidence,
    ExtremeDualBarSetActivationEvidenceCatalog,
)


_SOURCE_BREAKPOINT_RE = re.compile(r"\((\d+)\)\s*$")


@dataclass(frozen=True)
class ExtremeGearRuntimeBarAttempt:
    attempt: RuntimeEffectEventAttempt
    active_bar: str

    def __post_init__(self) -> None:
        bar = str(self.active_bar or "").strip().casefold()
        if bar not in {"front", "back"}:
            raise ValueError(f"unsupported Extreme gear runtime bar: {self.active_bar!r}")
        object.__setattr__(self, "active_bar", bar)


@dataclass(frozen=True)
class ExtremeDualBarGearRuntimeLegalityResult:
    active_buffs: tuple[str, ...] = ()
    attempts_reviewed: int = 0
    attempts_rejected_inactive_breakpoint: int = 0
    unresolved: tuple[str, ...] = ()


class ExtremeDualBarGearRuntimeLegalityService:
    """Project only bar-legally-triggered gear proc windows to one snapshot."""

    def __init__(self, *, resolver: GearSetEffectVariantResolver) -> None:
        self.resolver = resolver

    @staticmethod
    def _named_buff(effect) -> str | None:
        if effect.layer is not EffectLayer.PROC:
            return None
        if effect.duration is None or float(effect.duration) <= 0.0:
            return None
        canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
        if canonical is None or not effects_for_buff(canonical):
            return None
        return canonical

    @staticmethod
    def _required_breakpoint(effect) -> int | None:
        match = _SOURCE_BREAKPOINT_RE.search(str(effect.source or ""))
        if match is None:
            return None
        value = int(match.group(1))
        return value if value > 0 else None

    @staticmethod
    def _breakpoints_for_bar(
        evidence: ExtremeDualBarSetActivationEvidence,
        bar: str,
    ) -> tuple[int, ...]:
        return (
            evidence.front_active_breakpoints
            if bar == "front"
            else evidence.back_active_breakpoints
        )

    def resolve_history(
        self,
        activation: ExtremeDualBarSetActivationEvidenceCatalog,
        *,
        attempts: tuple[ExtremeGearRuntimeBarAttempt, ...],
        snapshot_time_seconds: float,
    ) -> ExtremeDualBarGearRuntimeLegalityResult:
        snapshot = float(snapshot_time_seconds)
        unresolved: list[str] = list(activation.unresolved)
        active: list[str] = []
        rejected = 0

        ordered_attempts = tuple(
            sorted(
                attempts,
                key=lambda row: (
                    row.attempt.event.time_seconds,
                    row.attempt.event.sequence,
                ),
            )
        )

        for set_evidence in activation.evidence:
            max_count = max(int(set_evidence.front_count), int(set_evidence.back_count))
            if max_count <= 0:
                continue
            effects = tuple(self.resolver.resolve(int(set_evidence.set_id), max_count))
            for effect in effects:
                buff = self._named_buff(effect)
                if buff is None:
                    continue
                if effect.target_type not in (SupportTargetType.SELF, SupportTargetType.SELF_OR_ALLY):
                    target = effect.target_type.value if effect.target_type is not None else "unclassified"
                    unresolved.append(
                        f"{set_evidence.set_name} {buff} proc target {target!r} does not canonically prove wearer self-application"
                    )
                    continue

                required = self._required_breakpoint(effect)
                if required is None:
                    unresolved.append(
                        f"{set_evidence.set_name} {buff} proc has no canonical set-breakpoint provenance"
                    )
                    continue

                relevant: list[RuntimeEffectEventAttempt] = []
                for row in ordered_attempts:
                    if row.attempt.event.time_seconds > snapshot + 1e-12:
                        continue
                    if not runtime_event_matches_effect_variant(row.attempt.event, effect):
                        continue
                    if required not in self._breakpoints_for_bar(set_evidence, row.active_bar):
                        rejected += 1
                        continue
                    relevant.append(row.attempt)

                if not relevant:
                    continue
                stream = process_effect_variant_runtime_stream(tuple(relevant), effect)
                for step in stream.unresolved_steps:
                    reasons = step.transition.unresolved or step.transition.activation.eligibility.reasons
                    if reasons:
                        unresolved.append(
                            f"{set_evidence.set_name} {buff} runtime history unresolved: {', '.join(reasons)}"
                        )
                partition = partition_runtime_effect_windows(
                    stream.final_state.windows,
                    at_time_seconds=snapshot,
                )
                if any(window.effect_name == effect.name for window in partition.active):
                    active.append(buff)

        return ExtremeDualBarGearRuntimeLegalityResult(
            active_buffs=tuple(dict.fromkeys(active)),
            attempts_reviewed=len(ordered_attempts),
            attempts_rejected_inactive_breakpoint=rejected,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
