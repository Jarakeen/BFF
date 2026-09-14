from types import SimpleNamespace

from ui.rotation_generate_application_context_provider import (
    RotationGenerateApplicationContextProvider,
)


def test_application_context_routes_saved_tank_role_to_explicit_tank_composer():
    tank = object()
    healer = object()
    provider = RotationGenerateApplicationContextProvider(
        role_evidence_composers={
            "tank": tank,
            "healer": healer,
        },
        dd_periodic_semantics_gap_audit_service=SimpleNamespace(),
        static_context_service=SimpleNamespace(),
        demand_policy_provider=SimpleNamespace(),
    )

    assert provider._role_evidence_composer_for(SimpleNamespace(Role="Tank")) is tank
    assert provider._role_evidence_composer_for(SimpleNamespace(Role="Healer")) is healer


def test_application_context_does_not_guess_unknown_role_composer():
    tank = object()
    provider = RotationGenerateApplicationContextProvider(
        role_evidence_composers={"tank": tank},
        dd_periodic_semantics_gap_audit_service=SimpleNamespace(),
        static_context_service=SimpleNamespace(),
        demand_policy_provider=SimpleNamespace(),
    )

    assert provider._role_evidence_composer_for(SimpleNamespace(Role="Support")) is None
