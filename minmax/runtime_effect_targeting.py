from __future__ import annotations

"""Deterministic runtime target-count handling for canonical EffectVariants.

The caller remains authoritative for target eligibility (range, position,
encounter state, ally/enemy membership, and any game-specific selection rules).
This layer only validates explicit selections against that eligible set and the
source-backed ``EffectVariant.target_count`` cap.
"""

from dataclasses import dataclass
from typing import Iterable

from .character_build.effect_instance import EffectVariant


@dataclass(frozen=True)
class RuntimeEffectTargetSelectionResult:
    """Eligible targets, selected targets, and any runtime fact still required."""

    eligible_targets: tuple[str, ...]
    selected_targets: tuple[str, ...]
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


def _normalize_target_identities(targets: Iterable[str], *, label: str) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for target in targets:
        identity = str(target or "").strip()
        if not identity:
            raise ValueError(f"{label} requires non-empty target identities")
        if identity in seen:
            raise ValueError(f"duplicate {label} target identity: {identity}")
        seen.add(identity)
        normalized.append(identity)
    return tuple(normalized)


def resolve_effect_variant_runtime_targets(
    effect: EffectVariant,
    *,
    eligible_targets: Iterable[str],
    selected_targets: Iterable[str] | None = None,
) -> RuntimeEffectTargetSelectionResult:
    """Resolve target-count handling without inventing a targeting algorithm.

    ``eligible_targets`` must already represent the set that can legally receive
    the effect after range/position/encounter rules. When the eligible set fits
    within the canonical target-count cap, every eligible target can be selected
    deterministically. If more targets are eligible than the cap permits, the
    caller must supply the actual selected subset.

    ``target_count=None`` means the source provides no finite cap. In that case
    all supplied eligible targets are selected unless an explicit subset is
    provided by a caller that knows a narrower runtime selection rule.
    """

    eligible = _normalize_target_identities(eligible_targets, label="eligible")
    selected = (
        None
        if selected_targets is None
        else _normalize_target_identities(selected_targets, label="selected")
    )

    cap = effect.target_count
    if cap is not None:
        if cap < 0:
            raise ValueError("EffectVariant.target_count cannot be negative at runtime")
        cap = int(cap)

    if selected is not None:
        eligible_set = set(eligible)
        unknown = tuple(target for target in selected if target not in eligible_set)
        if unknown:
            raise ValueError(
                "selected targets must be drawn from eligible targets: " + ", ".join(unknown)
            )
        if cap is not None and len(selected) > cap:
            raise ValueError(
                f"selected target count exceeds EffectVariant.target_count: {len(selected)} > {cap}"
            )
        return RuntimeEffectTargetSelectionResult(
            eligible_targets=eligible,
            selected_targets=selected,
        )

    if cap is None or len(eligible) <= cap:
        return RuntimeEffectTargetSelectionResult(
            eligible_targets=eligible,
            selected_targets=eligible,
        )

    return RuntimeEffectTargetSelectionResult(
        eligible_targets=eligible,
        selected_targets=(),
        unresolved=("target_selection_required",),
    )
