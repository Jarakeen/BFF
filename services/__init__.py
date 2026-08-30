# services/__init__.py
"""
services/__init__.py

Simple rules engine for FoundryDock.

A Rule inspects a context and optionally returns a RuleResult.
Rules never modify data—they only report findings.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


# ----------------------------------------------------------------------
# Result
# ----------------------------------------------------------------------

@dataclass
class RuleResult:
    title: str
    message: str
    severity: str = "info"
    recommendation: str | None = None


# ----------------------------------------------------------------------
# Base Rule
# ----------------------------------------------------------------------

class Rule(ABC):

    @property
    def priority(self) -> int:
        return 100

    @abstractmethod
    def evaluate(self, context: Any) -> RuleResult | None:
        """
        Return a RuleResult if this rule has something to report.
        Return None if everything is OK.
        """
        ...


# ----------------------------------------------------------------------
# Rules Engine
# ----------------------------------------------------------------------

class RulesEngine:

    def __init__(self):
        self._rules: list[Rule] = []

    def register(self, rule: Rule):
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def evaluate(self, context: Any) -> list[RuleResult]:

        results = []

        for rule in self._rules:
            result = rule.evaluate(context)

            if result:
                results.append(result)

        return results


class MissingEffectRule(Rule):

    effect = "Major Slayer"

    def evaluate(self, context):

        if context.has_effect(self.effect):
            return None

        return RuleResult(
            title="Missing Effect",
            message=f"Effect '{self.effect}' is missing.",
            severity="warning"
        )


class RequiresEffectRule:

    def __init__(self, required_effect: str, roster: list[Any]):
        self.required_effect = required_effect
        self.roster = roster

    def evaluate(self) -> bool:
        return any(
            self.required_effect in player.provides
            for player in self.roster
        )


# ----------------------------------------------------------------------
# Build persistence hardening
# ----------------------------------------------------------------------
# BuildService is imported by many pages directly. Installing the hardened
# methods here keeps the public BuildService API intact while making the
# write atomic and preventing corrupt JSON from being silently interpreted
# as an empty roster.

def _install_build_persistence():
    from .build_service import BuildService
    from .build_persistence import load, save

    BuildService.load = load
    BuildService.save = save


_install_build_persistence()
