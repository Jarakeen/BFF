from types import SimpleNamespace

import pytest

from minmax.resource_costs import ResourceType
from ui.rotation_generate_application_context_provider import (
    RotationGenerateApplicationContextProvider,
)


class _StaticContext:
    resolved = True
    unresolved = ()
    progression = SimpleNamespace(character_id="parse-cat-id")

    def maximum_amount_for(self, bar, resource):
        assert bar == "front"
        assert resource is ResourceType.MAGICKA
        return 30000


class _StaticContextService:
    def resolve(self, build):
        return _StaticContext()


class _Policies:
    def policies_for(self, encounter_id):
        return ()

    def threshold_policies_for(self, encounter_id):
        return ()

    def review_blockers_for(self, encounter_id):
        return ()


class _Page:
    def __init__(self, resistance):
        self.build = SimpleNamespace(Role="DD")
        self.resistance = resistance

    def _selected_build(self):
        return self.build

    def selected_encounter_id(self):
        return "test_encounter"

    def canonical_recovery_policy(self):
        return {
            "resource": ResourceType.MAGICKA,
            "trigger_fraction": 0.35,
        }

    def canonical_dd_evaluation_policy(self):
        return {"target_resistance": self.resistance}


def _provider():
    return RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
        demand_policy_provider=_Policies(),  # type: ignore[arg-type]
    )


def test_explicit_dd_target_resistance_enters_generate_evidence_inputs() -> None:
    context = _provider().context_for(_Page(18200.0))

    assert context.evidence_inputs.target_resistance == 18200.0


def test_explicit_zero_target_resistance_is_preserved() -> None:
    context = _provider().context_for(_Page(0.0))

    assert context.evidence_inputs.target_resistance == 0.0


def test_missing_dd_target_resistance_remains_unknown_for_role_composer() -> None:
    context = _provider().context_for(_Page(None))

    assert context.evidence_inputs.target_resistance is None


def test_negative_target_resistance_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        _provider().context_for(_Page(-1.0))
