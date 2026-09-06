from types import SimpleNamespace

from models.build_model import PlayerBuild
from minmax.rotation_ability_priority import AbilityPriorityEntry, AbilityPriorityList
from ui.rotation_generation_support import RotationGenerationRequest, RotationGenerationSupport


def _build() -> PlayerBuild:
    build = PlayerBuild(Name="Magrat", BuildName="DF Healer", Role="Healer")
    build.FrontBarSkills = [
        "Combat Prayer",
        "Radiating Regeneration",
        "Energy Orb",
        "",
        "",
        "Aggressive Horn",
    ]
    build.BackBarSkills = [
        "Overflowing Altar",
        "Expansive Frost Cloak",
        "",
        "",
        "",
        "Barrier",
    ]
    return build


def test_generation_passes_explicit_priorities_into_duration_refinement() -> None:
    received = []
    projection = SimpleNamespace(label="priority refined")
    evidence = SimpleNamespace(summary="duration evidence")

    class RefinementStub:
        def refine(self, plan, *, priorities=None):
            received.append(priorities)
            return SimpleNamespace(plan=plan, duration_projection=projection)

    class EvidenceStub:
        def from_projection(self, value):
            assert value is projection
            return evidence

    priorities = (
        AbilityPriorityEntry("front", 1, "Combat Prayer", 1),
        AbilityPriorityEntry("front", 2, "Radiating Regeneration", 2),
        AbilityPriorityEntry("front", 3, "Energy Orb", 3),
        AbilityPriorityEntry("back", 1, "Overflowing Altar", 4),
        AbilityPriorityEntry("back", 2, "Expansive Frost Cloak", 5),
    )

    RotationGenerationSupport(
        duration_refinement=RefinementStub(),
        duration_evidence=EvidenceStub(),
    ).generate_with_evidence(
        build=_build(),
        request=RotationGenerationRequest(
            duration_seconds=6.0,
            ability_priorities=priorities,
        ),
    )

    assert len(received) == 1
    assert isinstance(received[0], AbilityPriorityList)
    resolved = received[0].resolve()
    assert resolved[0].entry.skill_name == "Combat Prayer"
    assert resolved[0].effective_priority == 1
