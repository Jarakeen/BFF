from __future__ import annotations

"""Deterministic runtime stacking transitions for bounded effect windows.

``EffectVariant.name`` remains the logical effect identity. ``StackingBehavior``
remains authoritative for refresh/stack/highest-only semantics. This module
applies one newly created runtime window to previously retained windows without
inventing a second stacking taxonomy.
"""

from dataclasses import dataclass, replace
from typing import Iterable

from .runtime_effect_window import RuntimeEffectActiveWindow, order_runtime_effect_windows
from .support_stacking import StackingBehavior


@dataclass(frozen=True)
class RuntimeEffectStackingResult:
    """Updated retained windows plus any windows superseded by this application."""

    retained: tuple[RuntimeEffectActiveWindow, ...]
    superseded: tuple[RuntimeEffectActiveWindow, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


def _same_runtime_effect_scope(
    left: RuntimeEffectActiveWindow,
    right: RuntimeEffectActiveWindow,
) -> bool:
    """Same logical effect on the same runtime target scope."""

    return left.effect_name == right.effect_name and left.target == right.target


def _truncate_window_at_refresh(
    window: RuntimeEffectActiveWindow,
    *,
    refresh_time_seconds: float,
) -> RuntimeEffectActiveWindow | None:
    """End an older UNIQUE application exactly when its refresh begins."""

    if refresh_time_seconds <= window.start_time_seconds:
        return None
    if refresh_time_seconds >= window.end_time_seconds:
        return window
    return replace(window, end_time_seconds=refresh_time_seconds)


def apply_runtime_effect_window_stacking(
    existing_windows: Iterable[RuntimeEffectActiveWindow],
    new_window: RuntimeEffectActiveWindow,
    *,
    behavior: StackingBehavior | None,
) -> RuntimeEffectStackingResult:
    """Apply one new bounded window using canonical stacking behavior.

    ``None`` leaves behavior unresolved rather than assuming UNIQUE or STACKS.
    UNIQUE refreshes the same logical effect on the same target by truncating
    older overlapping windows at the new activation time. STACKS retains every
    application. HIGHEST_ONLY compares source-backed magnitudes and suppresses
    weaker overlapping applications while preserving stronger ones that may
    become effective again after the weaker/new window expires.
    """

    ordered = list(order_runtime_effect_windows(existing_windows))

    if behavior is None:
        return RuntimeEffectStackingResult(
            retained=tuple(ordered),
            unresolved=("stacking_behavior_required",),
        )

    if behavior is StackingBehavior.STACKS:
        return RuntimeEffectStackingResult(
            retained=order_runtime_effect_windows((*ordered, new_window)),
        )

    same_scope = [window for window in ordered if _same_runtime_effect_scope(window, new_window)]
    other_scope = [window for window in ordered if not _same_runtime_effect_scope(window, new_window)]

    if behavior is StackingBehavior.UNIQUE:
        retained_same: list[RuntimeEffectActiveWindow] = []
        superseded: list[RuntimeEffectActiveWindow] = []
        for window in same_scope:
            if window.end_time_seconds <= new_window.start_time_seconds:
                retained_same.append(window)
                continue
            if window.start_time_seconds > new_window.start_time_seconds:
                raise ValueError("runtime UNIQUE applications must be applied in chronological order")

            truncated = _truncate_window_at_refresh(
                window,
                refresh_time_seconds=new_window.start_time_seconds,
            )
            superseded.append(window)
            if truncated is not None:
                retained_same.append(truncated)

        return RuntimeEffectStackingResult(
            retained=order_runtime_effect_windows((*other_scope, *retained_same, new_window)),
            superseded=order_runtime_effect_windows(superseded),
        )

    if behavior is StackingBehavior.HIGHEST_ONLY:
        overlapping = [
            window
            for window in same_scope
            if window.start_time_seconds < new_window.end_time_seconds
            and new_window.start_time_seconds < window.end_time_seconds
        ]
        comparison = [*overlapping, new_window]
        if len(comparison) > 1 and any(window.magnitude is None for window in comparison):
            return RuntimeEffectStackingResult(
                retained=tuple(ordered),
                unresolved=("magnitude_required_for_highest_only",),
            )

        # HIGHEST_ONLY does not destroy lower-strength source windows. They may
        # become effective when the strongest window expires, so retain them all.
        return RuntimeEffectStackingResult(
            retained=order_runtime_effect_windows((*ordered, new_window)),
        )

    raise ValueError(f"Unsupported stacking behavior: {behavior}")


def effective_runtime_effect_windows(
    windows: Iterable[RuntimeEffectActiveWindow],
    *,
    behavior: StackingBehavior,
    at_time_seconds: float,
) -> RuntimeEffectStackingResult:
    """Resolve effective windows at one time from already-applied runtime state."""

    candidates = [window for window in windows if window.is_active_at(at_time_seconds)]
    if behavior in {StackingBehavior.STACKS, StackingBehavior.UNIQUE}:
        return RuntimeEffectStackingResult(retained=order_runtime_effect_windows(candidates))

    groups: dict[tuple[str, str | None], list[RuntimeEffectActiveWindow]] = {}
    for window in candidates:
        groups.setdefault((window.effect_name, window.target), []).append(window)

    retained: list[RuntimeEffectActiveWindow] = []
    unresolved: list[str] = []
    superseded: list[RuntimeEffectActiveWindow] = []
    for group in groups.values():
        if len(group) == 1:
            retained.extend(group)
            continue
        if any(window.magnitude is None for window in group):
            unresolved.append("magnitude_required_for_highest_only")
            continue

        maximum = max(float(window.magnitude) for window in group if window.magnitude is not None)
        strongest = [window for window in group if float(window.magnitude) == maximum]
        # Equal magnitudes are semantically equivalent. Pick a deterministic
        # representative for contribution accounting, not as a gameplay rule.
        chosen = max(
            strongest,
            key=lambda window: (
                window.start_time_seconds,
                window.sequence,
                window.end_time_seconds,
                window.source,
            ),
        )
        retained.append(chosen)
        superseded.extend(window for window in group if window is not chosen)

    return RuntimeEffectStackingResult(
        retained=order_runtime_effect_windows(retained),
        superseded=order_runtime_effect_windows(superseded),
        unresolved=tuple(dict.fromkeys(unresolved)),
    )
