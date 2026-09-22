from __future__ import annotations

"""Compose controlled Objective #32 runtime witnesses from external event history.

RotationPlan owns bar transitions. Finalized potion timing is evaluated directly from
scheduled POTION actions downstream and therefore must not be duplicated here.
Callers supply only genuinely external/runtime event evidence such as proc attempts,
condition windows, and external group-buff applications.
"""

from dataclasses import dataclass

from minmax.runtime_effect_sequence import RuntimeEffectEventAttempt
from minmax.external_group_buff_provenance import ExternalGroupBuffApplication
from models.build_model import PlayerBuild
from services.extreme_runtime_bar_effect_attempt import ExtremeRuntimeBarEffectAttempt
from services.extreme_runtime_bar_transition import ExtremeRuntimeBarTransition
from services.extreme_runtime_condition_window import ExtremeRuntimeConditionWindow
from services.extreme_runtime_snapshot import (
    ExtremeRuntimePotionUse,
    ExtremeRuntimeSnapshot,
)
from services.rotation_runtime_bar_provenance_service import (
    RotationRuntimeBarProvenanceService,
)


_ALLOWED_EXTERNAL = (
    RuntimeEffectEventAttempt,
    ExtremeRuntimeBarEffectAttempt,
    ExtremeRuntimeConditionWindow,
    ExternalGroupBuffApplication,
)


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeExternalHistoryChoice:
    history_id: str
    entries: tuple[object, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        key = str(self.history_id or "").strip()
        if not key:
            raise ValueError("runtime external-history choice requires history_id")
        object.__setattr__(self, "history_id", key)
        object.__setattr__(self, "entries", tuple(self.entries))
        object.__setattr__(
            self,
            "unresolved",
            tuple(
                dict.fromkeys(
                    str(item).strip()
                    for item in self.unresolved
                    if str(item).strip()
                )
            ),
        )


@dataclass(frozen=True)
class ExtremeSustainedDPSRuntimeWitnessComposition:
    snapshot: ExtremeRuntimeSnapshot | None
    evidence: tuple[str, ...]
    unresolved: tuple[str, ...]

    @property
    def resolved(self) -> bool:
        return self.snapshot is not None and not self.unresolved


class ExtremeSustainedDPSRuntimeWitnessCompositionService:
    """Bind external runtime evidence to the finalized plan's bar timeline."""

    def __init__(
        self,
        *,
        bar_provenance: RotationRuntimeBarProvenanceService | None = None,
    ) -> None:
        self.bar_provenance = bar_provenance or RotationRuntimeBarProvenanceService()

    @staticmethod
    def _validate_entries(entries: tuple[object, ...]) -> tuple[str, ...]:
        unresolved: list[str] = []
        for entry in entries:
            if isinstance(entry, ExtremeRuntimeBarTransition):
                unresolved.append(
                    "External runtime history must not supply bar transitions; RotationPlan owns BAR_SWAP truth"
                )
                continue
            if isinstance(entry, ExtremeRuntimePotionUse):
                unresolved.append(
                    "External runtime history must not supply potion uses; finalized RotationPlan POTION actions own potion timing"
                )
                continue
            if not isinstance(entry, _ALLOWED_EXTERNAL):
                unresolved.append(
                    "Unsupported Objective #32 external runtime history entry: "
                    + type(entry).__name__
                )
        return tuple(dict.fromkeys(unresolved))

    def compose(
        self,
        *,
        plan,
        player_build: PlayerBuild,
        external_entries: tuple[object, ...],
        initial_bar: str = "front",
        snapshot_time_seconds: float | None = None,
    ) -> ExtremeSustainedDPSRuntimeWitnessComposition:
        entries = tuple(external_entries)
        unresolved = list(self._validate_entries(entries))
        if unresolved:
            return ExtremeSustainedDPSRuntimeWitnessComposition(
                snapshot=None,
                evidence=(),
                unresolved=tuple(unresolved),
            )

        snapshot_time = (
            float(plan.duration_seconds)
            if snapshot_time_seconds is None
            else float(snapshot_time_seconds)
        )
        seed = ExtremeRuntimeSnapshot(
            runtime_history=entries,
            snapshot_time_seconds=snapshot_time,
            runtime_history_complete=True,
        )
        bound = self.bar_provenance.bind(
            plan,
            seed,
            initial_bar=initial_bar,
            player_build=player_build,
        )
        unresolved.extend(tuple(bound.unresolved))
        if bound.snapshot is None or unresolved:
            return ExtremeSustainedDPSRuntimeWitnessComposition(
                snapshot=None,
                evidence=(
                    f"External runtime entries supplied: {len(entries)}",
                    f"Plan-owned bar transitions projected: {bound.transitions_projected}",
                ),
                unresolved=tuple(dict.fromkeys(unresolved)),
            )

        return ExtremeSustainedDPSRuntimeWitnessComposition(
            snapshot=bound.snapshot,
            evidence=(
                f"External runtime entries supplied: {len(entries)}",
                f"Plan-owned bar transitions projected: {bound.transitions_projected}",
                f"Runtime attempts tagged with plan bar provenance: {bound.attempts_tagged}",
                f"Pre-tagged runtime attempts verified: {bound.attempts_verified}",
                "Potion timing is intentionally excluded because finalized plan POTION actions own that state downstream",
            ),
            unresolved=(),
        )


__all__ = [
    "ExtremeSustainedDPSRuntimeExternalHistoryChoice",
    "ExtremeSustainedDPSRuntimeWitnessComposition",
    "ExtremeSustainedDPSRuntimeWitnessCompositionService",
]
