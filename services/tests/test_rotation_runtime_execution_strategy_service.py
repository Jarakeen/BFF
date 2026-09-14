from models.build_model import PlayerBuild
from services.rotation_runtime_execution_strategy_service import (
    RotationRuntimeExecutionStrategyService,
)
from services.rotation_runtime_trigger_condition_service import RotationRuntimeActivatedIntent
from services.rotation_runtime_triggered_intent_service import RotationRuntimeTriggeredIntent
from services.saved_build_utility_capability_service import (
    SavedBuildUtilityProviderSource,
    SavedBuildUtilityProviderSourceResolution,
)


class _CapabilityService:
    def __init__(self, resolution):
        self.resolution = resolution
        self.calls = []

    def provider_sources_for(self, *, build, capability_type):
        self.calls.append((build, capability_type))
        return self.resolution


def _activated(*, capability="taunt") -> RotationRuntimeActivatedIntent:
    return RotationRuntimeActivatedIntent(
        intent=RotationRuntimeTriggeredIntent(
            intent_id="xalvakka:pack_encounter_adds:iron_atronach",
            trigger_key="encounter_actor_active:iron_atronach",
            directive="acquire_and_maintain_owned_add_when_active",
            source_plan_id="performance-mode-rg",
            source_seat_id="off-tank",
            encounter_id="xalvakka",
            target_key="Iron Atronach",
            required_capability_type=capability,
            source="reviewed Tank add activity",
        ),
        activated_at_seconds=37.25,
        trigger_source="authoritative runtime actor activity",
    )


def test_activated_taunt_intent_resolves_exact_slotted_skill_and_bar_candidates() -> None:
    resolution = SavedBuildUtilityProviderSourceResolution(
        capability_type="taunt",
        sources=(
            SavedBuildUtilityProviderSource(
                capability_type="taunt",
                skill_name="Pierce Armor",
                bar="front",
            ),
            SavedBuildUtilityProviderSource(
                capability_type="taunt",
                skill_name="Inner Rage",
                bar="back",
            ),
        ),
    )
    capability = _CapabilityService(resolution)
    service = RotationRuntimeExecutionStrategyService(capability)
    build = PlayerBuild(Name="Rylonia", BuildName="Tank Build", Role="Tank")

    result = service.resolve(activated_intent=_activated(), build=build)

    assert result.resolved is True
    assert capability.calls == [(build, "taunt")]
    assert [(row.skill_name, row.bar) for row in result.candidates] == [
        ("Pierce Armor", "front"),
        ("Inner Rage", "back"),
    ]
    assert all(row.activated_at_seconds == 37.25 for row in result.candidates)
    assert all(row.target_key == "Iron Atronach" for row in result.candidates)
    assert all(not hasattr(row, "time_seconds") for row in result.candidates)


def test_missing_required_capability_fails_closed_without_querying_build() -> None:
    capability = _CapabilityService(
        SavedBuildUtilityProviderSourceResolution(capability_type="taunt")
    )
    service = RotationRuntimeExecutionStrategyService(capability)

    result = service.resolve(
        activated_intent=_activated(capability=None),
        build=PlayerBuild(Name="Rylonia", BuildName="Tank Build"),
    )

    assert result.candidates == ()
    assert "no required capability type" in result.unresolved[0]
    assert capability.calls == []


def test_no_slotted_provider_remains_unresolved() -> None:
    capability = _CapabilityService(
        SavedBuildUtilityProviderSourceResolution(capability_type="taunt")
    )
    service = RotationRuntimeExecutionStrategyService(capability)

    result = service.resolve(
        activated_intent=_activated(),
        build=PlayerBuild(Name="Rylonia", BuildName="Tank Build"),
    )

    assert result.resolved is False
    assert result.candidates == ()
    assert result.unresolved == ("saved build has no slotted canonical taunt provider",)


def test_unknown_canonical_skill_evidence_remains_unresolved_even_with_no_candidate() -> None:
    capability = _CapabilityService(
        SavedBuildUtilityProviderSourceResolution(
            capability_type="taunt",
            unresolved=("Mystery Skill: canonical skill rank is unresolved",),
        )
    )
    service = RotationRuntimeExecutionStrategyService(capability)

    result = service.resolve(
        activated_intent=_activated(),
        build=PlayerBuild(Name="Rylonia", BuildName="Tank Build"),
    )

    assert result.resolved is False
    assert result.candidates == ()
    assert result.unresolved == (
        "Mystery Skill: canonical skill rank is unresolved",
    )


def test_strategy_candidate_does_not_become_rotation_action() -> None:
    capability = _CapabilityService(
        SavedBuildUtilityProviderSourceResolution(
            capability_type="taunt",
            sources=(
                SavedBuildUtilityProviderSource(
                    capability_type="taunt",
                    skill_name="Pierce Armor",
                    bar="front",
                ),
            ),
        )
    )
    result = RotationRuntimeExecutionStrategyService(capability).resolve(
        activated_intent=_activated(),
        build=PlayerBuild(Name="Rylonia", BuildName="Tank Build"),
    )

    candidate = result.candidates[0]
    assert candidate.skill_name == "Pierce Armor"
    assert candidate.bar == "front"
    assert not hasattr(candidate, "kind")
    assert not hasattr(candidate, "sequence")
    assert not hasattr(candidate, "time_seconds")
