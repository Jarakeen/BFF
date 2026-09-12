from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from ui.rotation_generate_application_context_provider import (
    RotationGenerateApplicationContextProvider,
)


class _StaticContext:
    resolved = True
    unresolved = ()
    progression = SimpleNamespace(character_id="role-routing-test")

    def maximum_amount_for(self, bar, resource):
        assert bar == "front"
        assert resource is ResourceType.MAGICKA
        return 32000


class _StaticContextService:
    def resolve(self, build):
        return _StaticContext()


class _PolicyProvider:
    def policies_for(self, encounter_id):
        return ()

    def threshold_policies_for(self, encounter_id):
        return ()

    def review_blockers_for(self, encounter_id):
        return ()


class _Page:
    def __init__(self, role: str) -> None:
        self.build = SimpleNamespace(Role=role)

    def _selected_build(self):
        return self.build

    def selected_encounter_id(self):
        return "test_encounter"

    def canonical_recovery_policy(self):
        return {
            "resource": ResourceType.MAGICKA,
            "trigger_fraction": 0.35,
        }

    def canonical_threshold_projection_policy(self):
        return {"difficulty": None, "raid_dps": None}


def _provider(role_map):
    return RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
        demand_policy_provider=_PolicyProvider(),  # type: ignore[arg-type]
        role_evidence_composers=role_map,  # type: ignore[arg-type]
    )


def test_generate_routes_saved_healer_role_to_registered_composer() -> None:
    healer_composer = object()
    provider = _provider({"healer": healer_composer})

    context = provider.context_for(_Page(" Healer "))

    assert context.role_evidence_composer is healer_composer


def test_generate_role_routing_normalizes_role_key_without_inventing_aliases() -> None:
    healer_composer = object()
    provider = _provider({"damage-dealer": object(), "healer": healer_composer})

    healer_context = provider.context_for(_Page("HEALER"))
    unsupported_context = provider.context_for(_Page("Tank"))

    assert healer_context.role_evidence_composer is healer_composer
    assert unsupported_context.role_evidence_composer is None
