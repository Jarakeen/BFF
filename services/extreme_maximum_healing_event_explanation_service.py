from __future__ import annotations

from dataclasses import dataclass

from services.extreme_canonical_healing_event_service import ExtremeCanonicalHealingEventService


@dataclass(frozen=True)
class ExtremeMaximumHealingEventTrace:
    coefficient_numbers: tuple[int, ...] = ()
    recipient_scopes: tuple[str, ...] = ()
    recipient_keys: tuple[str, ...] = ()
    event_keys: tuple[str, ...] = ()
    temporal_scopes: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


class ExtremeMaximumHealingEventExplanationService:
    """Recover the canonical winning event identity for unified heal ranking.

    The ordinary canonical evaluator already computes enough information to
    reconstruct per-component values and score reviewed recipient/event groups.
    This service replays only that final grouping step so UI/reporting code can
    explain which recipient/event actually won without rerunning build search.

    Blood Magic does not use coefficient rows. Its reviewed trigger contract is a
    separate self-heal event on the caster, so its identity is explicit here.
    """

    def __init__(self, *, healing_events=None) -> None:
        self.healing_events = healing_events

    def describe(self, entry) -> ExtremeMaximumHealingEventTrace:
        source_kind = str(getattr(entry, "source_kind", "") or "")
        if source_kind == "blood_magic":
            return ExtremeMaximumHealingEventTrace(
                recipient_scopes=("self",),
                recipient_keys=("caster",),
                event_keys=("blood_magic_costed_dark_magic_trigger",),
                temporal_scopes=("direct",),
            )
        if source_kind != "ordinary_skill":
            return ExtremeMaximumHealingEventTrace(
                unresolved=(f"Unsupported maximum-heal explanation source: {source_kind or '(empty)'}",),
            )
        return self._ordinary(entry)

    def _ordinary(self, entry) -> ExtremeMaximumHealingEventTrace:
        healing_events = self.healing_events
        if healing_events is None:
            return ExtremeMaximumHealingEventTrace(
                unresolved=("Canonical healing-event evaluator is unavailable for winner identity trace",),
            )

        route_entry = getattr(entry, "route_entry", None)
        optimization = getattr(route_entry, "optimization", None)
        event = getattr(optimization, "optimized_event", None)
        candidate = getattr(route_entry, "candidate", None)
        skill_rank_id = getattr(candidate, "skill_rank_id", None)
        if event is None or skill_rank_id is None:
            return ExtremeMaximumHealingEventTrace(
                unresolved=("Ordinary winner lacks optimization event or skill-rank identity",),
            )

        critical_multiplier = getattr(event, "critical_multiplier", None)
        if critical_multiplier is None:
            return ExtremeMaximumHealingEventTrace(
                unresolved=("Ordinary winner lacks Critical Healing multiplier for event-group trace",),
            )

        tooltip_service = getattr(healing_events, "tooltip_service", None)
        component_repository = getattr(tooltip_service, "components", None)
        scoring_service = getattr(healing_events, "event_group_scoring", None)
        if component_repository is None or scoring_service is None:
            return ExtremeMaximumHealingEventTrace(
                unresolved=("Canonical component repository/group scorer is unavailable for winner identity trace",),
            )

        components = tuple(component_repository.get_for_skill_rank(int(skill_rank_id)))
        scoring = scoring_service.score(
            components=components,
            value_by_coefficient=ExtremeCanonicalHealingEventService._component_values(event),
            critical_multiplier=float(critical_multiplier),
        )
        winner_numbers = tuple(int(value) for value in scoring.critical_winner_coefficients)
        if not winner_numbers:
            return ExtremeMaximumHealingEventTrace(
                unresolved=tuple(scoring.unresolved)
                or ("Canonical critical winner coefficient group is unavailable",),
            )

        by_number = {
            int(getattr(component, "coefficient_number")): component
            for component in components
        }
        winner_components = tuple(
            by_number[number]
            for number in winner_numbers
            if number in by_number
        )

        def unique(values) -> tuple[str, ...]:
            return tuple(
                dict.fromkeys(
                    str(value.value if hasattr(value, "value") else value)
                    for value in values
                    if value is not None and str(value).strip()
                )
            )

        return ExtremeMaximumHealingEventTrace(
            coefficient_numbers=winner_numbers,
            recipient_scopes=unique(
                getattr(component, "heal_recipient_scope", None)
                for component in winner_components
            ),
            recipient_keys=unique(
                getattr(component, "heal_recipient_key", None)
                for component in winner_components
            ),
            event_keys=unique(
                getattr(component, "heal_event_key", None)
                for component in winner_components
            ),
            temporal_scopes=unique(
                getattr(component, "heal_temporal_scope", None)
                for component in winner_components
            ),
            unresolved=tuple(scoring.unresolved),
        )
