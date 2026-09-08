from __future__ import annotations

from dataclasses import dataclass, replace

from models.build_model import PlayerBuild
from services.extreme_actual_heal_class_route_catalog_service import (
    ExtremeActualHealClassRouteCatalogResult,
    ExtremeActualHealClassRouteCatalogService,
    ExtremeActualHealClassRouteEntry,
)
from services.extreme_maximum_healing_event_explanation_service import (
    ExtremeMaximumHealingEventExplanationService,
    ExtremeMaximumHealingEventTrace,
)
from services.extreme_sorcerer_blood_magic_class_route_catalog_service import (
    ExtremeSorcererBloodMagicClassRouteCatalogResult,
    ExtremeSorcererBloodMagicClassRouteCatalogService,
    ExtremeSorcererBloodMagicClassRouteEntry,
)


@dataclass(frozen=True)
class ExtremeMaximumHealingEventRouteEntry:
    """One comparable maximum single-heal event from any modeled route source."""

    source_kind: str
    source_name: str
    event_value: float | None
    event_kind: str
    mechanic_complete: bool
    unresolved: tuple[str, ...]
    route_entry: ExtremeActualHealClassRouteEntry | ExtremeSorcererBloodMagicClassRouteEntry
    trace: ExtremeMaximumHealingEventTrace = ExtremeMaximumHealingEventTrace()

    @property
    def route(self):
        return self.route_entry.route

    @property
    def slotted_index(self) -> int:
        return int(self.route_entry.slotted_index)


@dataclass(frozen=True)
class ExtremeMaximumHealingEventWinnerExplanation:
    source_kind: str
    source_name: str
    event_kind: str
    event_value: float
    route_skill_lines: tuple[str, ...]
    slotted_index: int
    trace: ExtremeMaximumHealingEventTrace
    runner_up_name: str | None
    runner_up_value: float | None
    margin: float | None
    reason: str


@dataclass(frozen=True)
class ExtremeMaximumHealingEventClassRouteCatalogResult:
    entries: tuple[ExtremeMaximumHealingEventRouteEntry, ...]
    best_scored: ExtremeMaximumHealingEventRouteEntry | None
    best_complete: ExtremeMaximumHealingEventRouteEntry | None
    ordinary: ExtremeActualHealClassRouteCatalogResult
    blood_magic: ExtremeSorcererBloodMagicClassRouteCatalogResult
    search_scope: tuple[str, ...]
    omitted_scope: tuple[str, ...]

    @property
    def global_maximum_proven(self) -> bool:
        return bool(
            self.entries
            and not self.omitted_scope
            and self.best_scored is not None
            and self.best_scored.mechanic_complete
            and all(entry.mechanic_complete for entry in self.entries)
        )

    @property
    def winner_explanation(self) -> ExtremeMaximumHealingEventWinnerExplanation | None:
        winner = self.best_scored
        if winner is None or winner.event_value is None:
            return None
        scored = tuple(entry for entry in self.entries if entry.event_value is not None)
        runner_up = next((entry for entry in scored if entry is not winner), None)
        runner_value = None if runner_up is None else float(runner_up.event_value)
        margin = None if runner_value is None else float(winner.event_value) - runner_value
        kind_label = (
            "canonical maximum event"
            if winner.event_kind == "canonical_maximum"
            else "proved non-critical event"
        )
        if runner_up is None:
            reason = (
                f"{winner.source_name} is the only scored candidate, with a "
                f"{kind_label} of {float(winner.event_value):.3f}."
            )
        else:
            reason = (
                f"{winner.source_name} wins with a {kind_label} of "
                f"{float(winner.event_value):.3f}, exceeding {runner_up.source_name} "
                f"at {runner_value:.3f} by {float(margin):.3f}."
            )
        return ExtremeMaximumHealingEventWinnerExplanation(
            source_kind=winner.source_kind,
            source_name=winner.source_name,
            event_kind=winner.event_kind,
            event_value=float(winner.event_value),
            route_skill_lines=tuple(winner.route.equipped_skill_lines),
            slotted_index=winner.slotted_index,
            trace=winner.trace,
            runner_up_name=None if runner_up is None else runner_up.source_name,
            runner_up_value=runner_value,
            margin=margin,
            reason=reason,
        )


class ExtremeMaximumHealingEventClassRouteCatalogService:
    """Compare modeled route candidates by their largest legal single heal event.

    Ordinary coefficient-backed heals contribute the canonical ``critical_heal``
    maximum. That field already preserves explicitly non-crittable components at
    normal value, while unresolved critical eligibility leaves the maximum
    unresolved. This aggregator therefore must not fall back to ``normal_heal``
    for an ordinary entry whose critical maximum is unknown.

    Blood Magic contributes its normal event because the reviewed Max-Health proc
    policy proves it cannot critically heal. The comparison therefore uses one
    objective for both families: largest healing event delivered to one canonical
    recipient/event identity, not a mixture of critical-only and normal-only
    leaderboards.

    Each ranked entry also carries a read-only event identity trace. The trace
    reuses the canonical event grouper to expose the winning coefficient group,
    recipient/event identity, and temporal scope without rerunning build search.
    """

    SEARCH_SCOPE = (
        "ordinary coefficient-backed maximum healing events across legal class routes",
        "Blood Magic non-critical maximum healing events across legal Dark Magic routes",
        "single event magnitude comparison across critical and explicitly non-critical heal families",
        "winner source/route/event identity trace and runner-up margin",
    )

    def __init__(
        self,
        *,
        ordinary: ExtremeActualHealClassRouteCatalogService | None = None,
        blood_magic: ExtremeSorcererBloodMagicClassRouteCatalogService | None = None,
        explanations: ExtremeMaximumHealingEventExplanationService | None = None,
    ) -> None:
        self.ordinary = ordinary if ordinary is not None else ExtremeActualHealClassRouteCatalogService()
        self.blood_magic = (
            blood_magic
            if blood_magic is not None
            else ExtremeSorcererBloodMagicClassRouteCatalogService()
        )
        healing_events = getattr(getattr(self.ordinary, "optimizer", None), "healing_events", None)
        self.explanations = (
            explanations
            if explanations is not None
            else ExtremeMaximumHealingEventExplanationService(healing_events=healing_events)
        )

    def rank(
        self,
        baseline_build: PlayerBuild,
        *,
        active_bar: str = "front",
        max_passes: int = 24,
        include_base_class_changes: bool = False,
    ) -> ExtremeMaximumHealingEventClassRouteCatalogResult:
        kwargs = {
            "active_bar": active_bar,
            "max_passes": max_passes,
            "include_base_class_changes": include_base_class_changes,
        }
        ordinary_result = self.ordinary.rank(baseline_build, **kwargs)
        blood_magic_result = self.blood_magic.rank(baseline_build, **kwargs)

        entries = [
            *(self._ordinary_entry(entry) for entry in ordinary_result.entries),
            *(self._blood_magic_entry(entry) for entry in blood_magic_result.entries),
        ]
        ranked = tuple(sorted(entries, key=self._rank_key))
        scored = tuple(entry for entry in ranked if entry.event_value is not None)
        complete = tuple(entry for entry in scored if entry.mechanic_complete)

        search_scope = self._unique(
            (*self.SEARCH_SCOPE, *ordinary_result.search_scope, *blood_magic_result.search_scope)
        )
        omitted_scope = self._unique(
            (
                *ordinary_result.omitted_scope,
                *(
                    item
                    for item in blood_magic_result.omitted_scope
                    if item != "global maximum-event comparison against ordinary-heal candidates"
                ),
            )
        )

        return ExtremeMaximumHealingEventClassRouteCatalogResult(
            entries=ranked,
            best_scored=scored[0] if scored else None,
            best_complete=complete[0] if complete else None,
            ordinary=ordinary_result,
            blood_magic=blood_magic_result,
            search_scope=search_scope,
            omitted_scope=omitted_scope,
        )

    def _ordinary_entry(
        self,
        entry: ExtremeActualHealClassRouteEntry,
    ) -> ExtremeMaximumHealingEventRouteEntry:
        event_value: float | None = None
        event_kind = "unresolved"
        if entry.optimization is not None:
            value = entry.optimization.optimized_event.critical_heal
            if value is not None:
                event_value = float(value)
                event_kind = "canonical_maximum"
        result = ExtremeMaximumHealingEventRouteEntry(
            source_kind="ordinary_skill",
            source_name=entry.candidate.name,
            event_value=event_value,
            event_kind=event_kind,
            mechanic_complete=entry.mechanic_complete,
            unresolved=entry.unresolved,
            route_entry=entry,
        )
        return replace(result, trace=self.explanations.describe(result))

    def _blood_magic_entry(
        self,
        entry: ExtremeSorcererBloodMagicClassRouteEntry,
    ) -> ExtremeMaximumHealingEventRouteEntry:
        value = entry.normal_heal
        result = ExtremeMaximumHealingEventRouteEntry(
            source_kind="blood_magic",
            source_name=f"Blood Magic via {entry.trigger.name}",
            event_value=None if value is None else float(value),
            event_kind="normal_noncritical",
            mechanic_complete=entry.mechanic_complete,
            unresolved=entry.unresolved,
            route_entry=entry,
        )
        return replace(result, trace=self.explanations.describe(result))

    @staticmethod
    def _rank_key(entry: ExtremeMaximumHealingEventRouteEntry) -> tuple[float, str, str, tuple[str, ...], int]:
        value = entry.event_value
        return (
            -(float(value) if value is not None else float("-inf")),
            entry.source_kind,
            entry.source_name.casefold(),
            entry.route.equipped_skill_lines,
            entry.slotted_index,
        )

    @staticmethod
    def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(value for value in values if value))
