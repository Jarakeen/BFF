from __future__ import annotations

"""Canonical rotation bridge for fail-closed conditional combat output."""

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path

from minmax.character_build.effect_relationship import ConditionContext
from minmax.runtime_event import RuntimeEvent
from minmax.runtime_output_eligibility import (
    RuntimeOutputEligibilityResult,
    RuntimeOutputEligibilityRule,
    evaluate_runtime_output_eligibility,
)
from minmax.skill_coefficient_repository import ability_entity_id


DETONATING_SIPHON_GEOMETRY_CONDITION = "target_in_detonating_siphon_geometry"

RotationRuntimeOutputConditionContextResolver = Callable[
    [RuntimeEvent],
    ConditionContext | None,
]


@dataclass(frozen=True)
class RotationRuntimeOutputConditionRule:
    skill_entity_id: str
    coefficient_number: int
    eligibility: RuntimeOutputEligibilityRule

    def __post_init__(self) -> None:
        identity = ability_entity_id(self.skill_entity_id)
        if not identity:
            raise ValueError("rotation output eligibility rule requires canonical skill identity")
        object.__setattr__(self, "skill_entity_id", identity)
        if self.coefficient_number <= 0:
            raise ValueError("rotation output eligibility coefficient_number must be positive")


@dataclass(frozen=True)
class RotationRuntimeOutputEligibilityResult:
    skill_entity_id: str
    coefficient_number: int
    has_rule: bool
    eligible: bool
    resolved: bool
    required_conditions: tuple[str, ...] = ()
    missing_conditions: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()


@dataclass(frozen=True)
class RotationRuntimeOutputEventFilterResult:
    events: tuple[RuntimeEvent, ...]
    evidence: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def resolved(self) -> bool:
        return not self.unresolved


class RotationRuntimeOutputConditionRegistryService:
    """Load reviewed runtime-output condition rules from versioned repository data.

    The registry stores reviewed policy/evidence only. It does not calculate runtime
    state, geometry, cadence, or output magnitude. Missing data resolves to no
    conditional rules rather than inventing behavior.
    """

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = (
            Path(path)
            if path is not None
            else Path(__file__).resolve().parents[1]
            / "data"
            / "rotation_runtime_output_conditions.json"
        )

    def load(self) -> tuple[RotationRuntimeOutputConditionRule, ...]:
        if not self.path.exists():
            return ()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("runtime output condition registry must be a JSON object")
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("runtime output condition registry schema_version must be 1")
        rows = payload.get("entries", [])
        if not isinstance(rows, list):
            raise ValueError("runtime output condition registry entries must be a list")

        rules: list[RotationRuntimeOutputConditionRule] = []
        seen: set[tuple[str, int]] = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValueError(
                    f"runtime output condition registry entry {index} must be an object"
                )
            try:
                required_conditions = tuple(
                    str(item).strip()
                    for item in row["required_conditions"]
                    if str(item).strip()
                )
                source = str(row["source"]).strip()
                if not required_conditions:
                    raise ValueError("required_conditions must contain at least one condition")
                if not source:
                    raise ValueError("source must be non-empty")
                rule = RotationRuntimeOutputConditionRule(
                    skill_entity_id=str(row["skill_entity_id"]),
                    coefficient_number=int(row["coefficient_number"]),
                    eligibility=RuntimeOutputEligibilityRule(
                        required_conditions=required_conditions,
                        source=source,
                    ),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    f"invalid runtime output condition registry entry {index}: {exc}"
                ) from exc
            key = (rule.skill_entity_id, rule.coefficient_number)
            if key in seen:
                raise ValueError(
                    "duplicate runtime output condition registry rule for "
                    f"{rule.skill_entity_id} coefficient {rule.coefficient_number}"
                )
            seen.add(key)
            rules.append(rule)
        return tuple(rules)


class RotationRuntimeOutputEligibilityService:
    """Evaluate reviewed skill-component output conditions without inventing runtime state.

    Production rules are loaded from the versioned runtime-output condition registry.
    Explicit ``rules`` injection remains available for focused tests and callers that
    already own reviewed rule objects. Rules are keyed by canonical skill identity plus
    coefficient number. Skills/components with no reviewed rule pass through unchanged.

    A reviewed conditional output fails closed when no ``ConditionContext`` is supplied.
    A supplied context that does not contain every required opaque condition resolves
    deterministically to ineligible output. ``filter_events`` evaluates context
    independently for each exact runtime event, so cast-time truth is never smeared over
    later occurrences.
    """

    def __init__(
        self,
        rules: tuple[RotationRuntimeOutputConditionRule, ...] | None = None,
        *,
        registry: RotationRuntimeOutputConditionRegistryService | None = None,
    ) -> None:
        resolved_rules = (
            tuple(rules)
            if rules is not None
            else (registry or RotationRuntimeOutputConditionRegistryService()).load()
        )
        keyed: dict[tuple[str, int], RotationRuntimeOutputConditionRule] = {}
        for rule in resolved_rules:
            key = (rule.skill_entity_id, rule.coefficient_number)
            if key in keyed:
                raise ValueError(
                    "duplicate rotation output eligibility rule for "
                    f"{rule.skill_entity_id} coefficient {rule.coefficient_number}"
                )
            keyed[key] = rule
        self._rules = keyed

    def rule_for(
        self,
        skill_entity_id: str,
        coefficient_number: int,
    ) -> RotationRuntimeOutputConditionRule | None:
        return self._rules.get(
            (ability_entity_id(skill_entity_id), int(coefficient_number))
        )

    def evaluate(
        self,
        *,
        skill_entity_id: str,
        coefficient_number: int,
        condition_context: ConditionContext | None,
    ) -> RotationRuntimeOutputEligibilityResult:
        identity = ability_entity_id(skill_entity_id)
        number = int(coefficient_number)
        rule = self.rule_for(identity, number)
        if rule is None:
            return RotationRuntimeOutputEligibilityResult(
                skill_entity_id=identity,
                coefficient_number=number,
                has_rule=False,
                eligible=True,
                resolved=True,
            )

        result: RuntimeOutputEligibilityResult = evaluate_runtime_output_eligibility(
            rule.eligibility,
            condition_context,
        )
        evidence = (
            "required runtime output conditions: "
            + ", ".join(rule.eligibility.required_conditions),
            f"condition provenance: {rule.eligibility.source}",
        )
        unresolved: tuple[str, ...] = ()
        if not result.resolved:
            unresolved = (
                f"{identity} coefficient {number}: runtime output eligibility requires "
                "authoritative ConditionContext for "
                + ", ".join(result.missing_conditions),
            )

        return RotationRuntimeOutputEligibilityResult(
            skill_entity_id=identity,
            coefficient_number=number,
            has_rule=True,
            eligible=result.eligible,
            resolved=result.resolved,
            required_conditions=rule.eligibility.required_conditions,
            missing_conditions=result.missing_conditions,
            evidence=evidence,
            unresolved=unresolved,
        )

    def filter_events(
        self,
        *,
        skill_entity_id: str,
        coefficient_number: int,
        events: tuple[RuntimeEvent, ...],
        condition_context_resolver: (
            RotationRuntimeOutputConditionContextResolver | None
        ) = None,
    ) -> RotationRuntimeOutputEventFilterResult:
        """Filter exact runtime events through reviewed output conditions."""

        rule = self.rule_for(skill_entity_id, coefficient_number)
        if rule is None or not events:
            return RotationRuntimeOutputEventFilterResult(events=tuple(events))

        eligible_events: list[RuntimeEvent] = []
        evidence = (
            "required runtime output conditions: "
            + ", ".join(rule.eligibility.required_conditions),
            f"condition provenance: {rule.eligibility.source}",
        )
        unresolved: list[str] = []

        for event in events:
            context = (
                condition_context_resolver(event)
                if condition_context_resolver is not None
                else None
            )
            result = evaluate_runtime_output_eligibility(rule.eligibility, context)
            if not result.resolved:
                unresolved.append(
                    f"{rule.skill_entity_id} coefficient {rule.coefficient_number} at "
                    f"{float(event.time_seconds):g}s: runtime output eligibility requires "
                    "authoritative ConditionContext for "
                    + ", ".join(result.missing_conditions)
                )
                continue
            if result.eligible:
                eligible_events.append(event)

        return RotationRuntimeOutputEventFilterResult(
            events=tuple(eligible_events),
            evidence=evidence,
            unresolved=tuple(dict.fromkeys(unresolved)),
        )


__all__ = [
    "DETONATING_SIPHON_GEOMETRY_CONDITION",
    "RotationRuntimeOutputConditionContextResolver",
    "RotationRuntimeOutputConditionRegistryService",
    "RotationRuntimeOutputConditionRule",
    "RotationRuntimeOutputEligibilityResult",
    "RotationRuntimeOutputEligibilityService",
    "RotationRuntimeOutputEventFilterResult",
]
