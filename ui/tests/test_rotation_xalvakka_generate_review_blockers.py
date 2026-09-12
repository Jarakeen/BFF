from types import SimpleNamespace

from minmax.resource_costs import ResourceType
from ui.rotation_generate_application_context_provider import (
    RotationGenerateApplicationContextProvider,
)


class _StaticContext:
    resolved = True
    unresolved = ()
    progression = SimpleNamespace(character_id="magrat-id")

    def maximum_amount_for(self, bar, resource):
        assert bar == "front"
        assert resource is ResourceType.MAGICKA
        return 32123


class _StaticContextService:
    def resolve(self, build):
        return _StaticContext()


class _Page:
    def __init__(self) -> None:
        self.build = SimpleNamespace(Role="Healer")

    def _selected_build(self):
        return self.build

    def selected_encounter_id(self):
        return "xalvakka"

    def canonical_recovery_policy(self):
        return {
            "resource": ResourceType.MAGICKA,
            "trigger_fraction": 0.35,
        }

    def canonical_threshold_projection_policy(self):
        raise AssertionError(
            "unreviewed Xalvakka obligations must not request threshold projection inputs"
        )


def test_live_generate_surfaces_three_distinct_xalvakka_review_blockers() -> None:
    provider = RotationGenerateApplicationContextProvider(
        static_context_service=_StaticContextService(),  # type: ignore[arg-type]
    )

    context = provider.context_for(_Page())

    assert context.evidence_inputs.demand_policies == ()
    assert context.evidence_inputs.threshold_demand_policies == ()
    assert context.evidence_inputs.threshold_damage_segments == ()
    assert context.evidence_inputs.difficulty == ""

    gaps = context.evidence_inputs.knowledge_gaps
    assert tuple(gap.key for gap in gaps) == (
        "xalvakka.creeping_manifold_healer_demand",
        "xalvakka.xalvakka_stair_transition_healer_demand",
        "xalvakka.xalvakka_split_floor_healer_demand",
    )
    assert all(gap.blocking for gap in gaps)
    assert all(gap.consumers == ("rotation_maker",) for gap in gaps)
    assert "Heal-Check (Manifold)" in gaps[0].source_context
    assert "Healing Stairs" in gaps[1].source_context
    assert "Healing Triple Split Damage" in gaps[2].source_context
