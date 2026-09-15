from __future__ import annotations

"""Gate gear-proc runtime attempts by proven bar-local set activation.

A legal two-bar build can carry set bonuses that exist only on one weapon bar.
Proc attempts therefore need separate proofs:

* the required set breakpoint was active on the bar where the trigger occurred;
* the canonical effect explicitly defines what happens if that source becomes
  inactive after activation;
* strict source-bound persistence uses the complete ordered BAR_SWAP history;
* the ordinary shared runtime window/cooldown machinery decides whether the
  effect is still inside its timed window at the requested snapshot.

The result exposes both named buffs and generic active timed ``EffectVariant`` rows.
Named Major/Minor effects continue through ``active_buffs`` for CombatState. Timed
non-named proc effects, such as Armor of Truth's Weapon/Spell Damage window, remain
machine-readable in ``active_effects`` for objective-specific consumers.
"""

from dataclasses import dataclass
import re

from minmax.character_build.effect_instance import EffectVariant
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
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition


_SOURCE_BREAKPOINT_RE = re.compile(r"\((\d+)\)\s*$")


@dataclass(frozen=True)
class ExtremeDualBarGearRuntimeLegalityResult:
    active_buffs: tuple[str, ...] = ()
    active_effects: tuple[EffectVariant, ...] = ()
    attempts_reviewed: int = 0
    attempts_rejected_inactive_breakpoint: int = 0
    unresolved: tuple[str, ...] = ()


class ExtremeDualBarGearRuntimeLegalityService:
    """Project only bar-legally-triggered gear proc windows to one snapshot."""

    def __init__(self, *, resolver: GearSetEffectVariantResolver) -> None:
        self.resolver = resolver

    @staticmethod
    def _named_buff(effect: EffectVariant) -> str | None:
        if effect.layer is not EffectLayer.PROC:
            return None
        if effect.duration is None or float(effect.duration) <= 0.0:
            return None
        canonical = canonical_buff_name(str(effect.name or "").replace("_", " "))
        if canonical is None or not effects_for_buff(canonical):
            return None
        return canonical

    @staticmethod
    def _timed_self_proc(effect: EffectVariant) -> bool:
        return bool(
            effect.layer is EffectLayer.PROC
            and effect.duration is not None
            and float(effect.duration) > 0.0
            and effect.trigger is not None
            and str(effect.trigger).strip()
            and effect.target_type in (SupportTargetType.SELF, SupportTargetType.SELF_OR_ALLY)
        )

    @staticmethod
    def _required_breakpoint(effect: EffectVariant) -> int | None:
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

    @classmethod
    def _breakpoint_active_on_both_bars(
        cls,
        evidence: ExtremeDualBarSetActivationEvidence,
        required: int,
    ) -> bool:
        return (
            required in cls._breakpoints_for_bar(evidence, "front")
            and required in cls._breakpoints_for_bar(evidence, "back")
        )

    @classmethod
    def _window_loses_source(
        cls,
        evidence: ExtremeDualBarSetActivationEvidence,
        required: int,
        window,
        transitions: tuple[ExtremeRuntimeBarTransition, ...],
        *,
        snapshot_time_seconds: float,
    ) -> bool:
        start_key = (float(window.start_time_seconds), int(window.sequence))
        for transition in transitions:
            transition_key = (float(transition.time_seconds), int(transition.sequence))
            if transition_key <= start_key:
                continue
            if float(transition.time_seconds) > float(snapshot_time_seconds) + 1e-12:
                break
            if required not in cls._breakpoints_for_bar(evidence, transition.to_bar):
                return True
        return False

    @staticmethod
    def _append_active(
        effect: EffectVariant,
        *,
        active_effects: list[EffectVariant],
        active_buffs: list[str],
    ) -> None:
        active_effects.append(effect)
        buff = ExtremeDualBarGearRuntimeLegalityService._named_buff(effect)
        if buff is not None:
            active_buffs.append(buff)

    def resolve_history(
        self,
        activation: ExtremeDualBarSetActivationEvidenceCatalog,
        *,
        attempts: tuple[ExtremeRuntimeBarEffectAttempt, ...],
        snapshot_time_seconds: float,
        snapshot_active_bar: str | None = None,
        bar_transitions: tuple[ExtremeRuntimeBarTransition, ...] = (),
        bar_transition_history_complete: bool = False,
    ) -> ExtremeDualBarGearRuntimeLegalityResult:
        snapshot = float(snapshot_time_seconds)
        snapshot_bar = str(snapshot_active_bar or "").strip().casefold() or None
        if snapshot_bar not in {None, "front", "back"}:
            raise ValueError(f"unsupported Extreme gear snapshot bar: {snapshot_active_bar!r}")

        unresolved: list[str] = list(activation.unresolved)
        active_buffs: list[str] = []
        active_effects: list[EffectVariant] = []
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
        ordered_transitions = tuple(
            sorted(
                bar_transitions,
                key=lambda row: (row.time_seconds, row.sequence),
            )
        )

        for set_evidence in activation.evidence:
            max_count = max(int(set_evidence.front_count), int(set_evidence.back_count))
            if max_count <= 0:
                continue
            effects = tuple(self.resolver.resolve(int(set_evidence.set_id), max_count))
            for effect in effects:
                if effect.layer is not EffectLayer.PROC:
                    continue
                if effect.duration is None or float(effect.duration) <= 0.0:
                    continue
                if effect.trigger is None or not str(effect.trigger).strip():
                    continue

                label = self._named_buff(effect) or str(effect.name or "runtime effect")
                if effect.target_type not in (SupportTargetType.SELF, SupportTargetType.SELF_OR_ALLY):
                    target = effect.target_type.value if effect.target_type is not None else "unclassified"
                    unresolved.append(
                        f"{set_evidence.set_name} {label} proc target {target!r} does not canonically prove wearer self-application"
                    )
                    continue

                required = self._required_breakpoint(effect)
                if required is None:
                    unresolved.append(
                        f"{set_evidence.set_name} {label} proc has no canonical set-breakpoint provenance"
                    )
                    continue

                persistence = effect.source_persistence
                if persistence is None:
                    unresolved.append(
                        f"{set_evidence.set_name} {label} proc persistence after source deactivation is unclassified"
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
                            f"{set_evidence.set_name} {label} runtime history unresolved: {', '.join(reasons)}"
                        )
                partition = partition_runtime_effect_windows(
                    stream.final_state.windows,
                    at_time_seconds=snapshot,
                )
                active_windows = tuple(
                    window for window in partition.active if window.effect_name == effect.name
                )
                if not active_windows:
                    continue

                if persistence is EffectSourcePersistence.PERSISTS_AFTER_ACTIVATION:
                    self._append_active(
                        effect,
                        active_effects=active_effects,
                        active_buffs=active_buffs,
                    )
                    continue

                if persistence is EffectSourcePersistence.REQUIRES_SOURCE_ACTIVE_AT_SNAPSHOT:
                    if snapshot_bar is None:
                        unresolved.append(
                            f"{set_evidence.set_name} {label} requires the source breakpoint active at the snapshot, but snapshot bar provenance is missing"
                        )
                    elif required in self._breakpoints_for_bar(set_evidence, snapshot_bar):
                        self._append_active(
                            effect,
                            active_effects=active_effects,
                            active_buffs=active_buffs,
                        )
                    continue

                if persistence is EffectSourcePersistence.ENDS_WHEN_SOURCE_INACTIVE:
                    if self._breakpoint_active_on_both_bars(set_evidence, required):
                        self._append_active(
                            effect,
                            active_effects=active_effects,
                            active_buffs=active_buffs,
                        )
                        continue
                    if not bar_transition_history_complete:
                        unresolved.append(
                            f"{set_evidence.set_name} {label} ends when its source becomes inactive; complete bar-transition history is required"
                        )
                        continue
                    if any(
                        not self._window_loses_source(
                            set_evidence,
                            required,
                            window,
                            ordered_transitions,
                            snapshot_time_seconds=snapshot,
                        )
                        for window in active_windows
                    ):
                        self._append_active(
                            effect,
                            active_effects=active_effects,
                            active_buffs=active_buffs,
                        )
                    continue

                unresolved.append(
                    f"{set_evidence.set_name} {label} has unsupported source persistence: {persistence!r}"
                )

        unique_effects: dict[tuple[str, str, float | None], EffectVariant] = {}
        for effect in active_effects:
            key = (str(effect.source), str(effect.name), effect.magnitude)
            unique_effects[key] = effect

        return ExtremeDualBarGearRuntimeLegalityResult(
            active_buffs=tuple(dict.fromkeys(active_buffs)),
            active_effects=tuple(unique_effects.values()),
            attempts_reviewed=len(ordered_attempts),
            attempts_rejected_inactive_breakpoint=rejected,
            unresolved=tuple(dict.fromkeys(item for item in unresolved if item)),
        )
