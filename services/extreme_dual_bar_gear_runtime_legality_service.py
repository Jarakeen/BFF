from __future__ import annotations

"""Gate gear-proc runtime attempts by proven bar-local set activation.

A legal two-bar build can carry set bonuses that exist only on one weapon bar.
Proc attempts therefore need separate proofs:

* the required set breakpoint was active on the bar where the trigger occurred;
* the canonical effect explicitly defines what happens if that source becomes
  inactive after activation;
* the ordinary shared runtime window/cooldown machinery decides whether the
  effect is still inside its timed window at the requested snapshot.

This service owns no set-count math and no proc math. Bar-local breakpoint truth
comes from ``ExtremeDualBarSetActivationEvidenceCatalog`` and runtime transitions
remain owned by the existing shared effect stream helpers. Active-bar provenance
comes from the unified Extreme runtime-history wrapper rather than a local type.
"""

from dataclasses import dataclass
import re

from minmax.character_build.effect_layer import EffectLayer
from minmax.effect_source_persistence import EffectSourcePersistence
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
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt


_SOURCE_BREAKPOINT_RE = re.compile(r"\((\d+)\)\s*$")


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
        attempts: tuple[ExtremeRuntimeBarEffectAttempt, ...],
        snapshot_time_seconds: float,
        snapshot_active_bar: str | None = None,
    ) -> ExtremeDualBarGearRuntimeLegalityResult:
        snapshot = float(snapshot_time_seconds)
        snapshot_bar = str(snapshot_active_bar or "").strip().casefold() or None
        if snapshot_bar not in {None, "front", "back"}:
            raise ValueError(f"unsupported Extreme gear snapshot bar: {snapshot_active_bar!r}")

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

                persistence = effect.source_persistence
                if persistence is None:
                    unresolved.append(
                        f"{set_evidence.set_name} {buff} proc persistence after source deactivation is unclassified"
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
                if not any(window.effect_name == effect.name for window in partition.active):
                    continue

                if persistence is EffectSourcePersistence.PERSISTS_AFTER_ACTIVATION:
                    active.append(buff)
                    continue

                if persistence is EffectSourcePersistence.REQUIRES_SOURCE_ACTIVE_AT_SNAPSHOT:
                    if snapshot_bar is None:
                        unresolved.append(
                            f"{set_evidence.set_name} {buff} requires the source breakpoint active at the snapshot, but snapshot bar provenance is missing"
                        )
                    elif required in self._breakpoints_for_bar(set_evidence, snapshot_bar):
                        active.append(buff)
                    continue

                if persistence is EffectSourcePersistence.ENDS_WHEN_SOURCE_INACTIVE:
                    unresolved.append(
                        f"{set_evidence.set_name} {buff} ends when its source becomes inactive; continuous bar-transition evidence is required"
                    )
                    continue

                unresolved.append(
                    f"{set_evidence.set_name} {buff} has unsupported source persistence: {persistence!r}"
                )

        return ExtremeDualBarGearRuntimeLegalityResult(
            active_buffs=tuple(dict.fromkeys(active)),
            attempts_reviewed=len(ordered_attempts),
            attempts_rejected_inactive_breakpoint=rejected,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
