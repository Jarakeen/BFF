from __future__ import annotations

"""Fail-closed runtime eligibility for conditional combat output.

This module is intentionally generic. It does not know what a named condition means;
callers supply opaque canonical condition names through the existing ``ConditionContext``
contract. A missing context is different from a known-empty context:

- ``None`` means the runtime fact was not supplied and the output remains unresolved.
- ``frozenset()`` means the caller supplied context and none of the required conditions
  hold, so the output is deterministically ineligible rather than unresolved.

This distinction lets periodic damage, healing, proc output, pets, tethers, geometry,
and future target-state mechanics share one gate without inventing role-specific rules.
"""

from dataclasses import dataclass

from minmax.character_build.effect_relationship import ConditionContext


@dataclass(frozen=True)
class RuntimeOutputEligibilityRule:
    """Reviewed condition requirements for one combat-output responsibility."""

    required_conditions: tuple[str, ...]
    source: str

    def __post_init__(self) -> None:
        cleaned = tuple(
            dict.fromkeys(str(value or "").strip() for value in self.required_conditions)
        )
        if not cleaned or any(not value for value in cleaned):
            raise ValueError("runtime output eligibility requires non-empty condition names")
        object.__setattr__(self, "required_conditions", cleaned)

        source = str(self.source or "").strip()
        if not source:
            raise ValueError("runtime output eligibility requires provenance")
        object.__setattr__(self, "source", source)


@dataclass(frozen=True)
class RuntimeOutputEligibilityResult:
    eligible: bool
    resolved: bool
    missing_conditions: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()


def evaluate_runtime_output_eligibility(
    rule: RuntimeOutputEligibilityRule,
    condition_context: ConditionContext | None,
) -> RuntimeOutputEligibilityResult:
    """Evaluate one reviewed output rule against explicit runtime condition evidence.

    No condition is inferred from names, skill identity, target state, or timing. When
    context is unavailable, the result fails closed as unresolved. When context is
    supplied but a required condition is absent, the result is resolved and ineligible.
    Multiple conditions use AND semantics.
    """

    if condition_context is None:
        return RuntimeOutputEligibilityResult(
            eligible=False,
            resolved=False,
            missing_conditions=rule.required_conditions,
            reasons=("condition_context_required",),
        )

    missing = tuple(
        condition
        for condition in rule.required_conditions
        if condition not in condition_context
    )
    if missing:
        return RuntimeOutputEligibilityResult(
            eligible=False,
            resolved=True,
            missing_conditions=missing,
            reasons=("condition_unsatisfied",),
        )

    return RuntimeOutputEligibilityResult(
        eligible=True,
        resolved=True,
    )


__all__ = [
    "RuntimeOutputEligibilityResult",
    "RuntimeOutputEligibilityRule",
    "evaluate_runtime_output_eligibility",
]
