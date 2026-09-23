from __future__ import annotations

from types import SimpleNamespace

from services.extreme_sustained_dps_potion_cooldown_resolution_service import (
    ExtremePotionPassiveGrantEvidence,
    ExtremeSustainedDPSPotionCooldownResolutionService,
    ExtremeSustainedDPSPotionCooldownScenarioEvidence,
)


class _BuildAdapter:
    def __init__(self, *, build=object(), unresolved=()):
        self.build = build
        self.unresolved = tuple(unresolved)
        self.calls = []

    def adapt(self, player_build, *, character_id=None):
        self.calls.append((player_build, character_id))
        return SimpleNamespace(build=self.build, unresolved=self.unresolved)


class _ItemService:
    def resolve(self, player_build):
        return SimpleNamespace(player_build=player_build)


class _CooldownService:
    def __init__(self, *, cooldown=43.0, unresolved=()):
        self.cooldown = cooldown
        self.unresolved = tuple(unresolved)
        self.calls = []

    def resolve(self, **kwargs):
        self.calls.append(kwargs)
        effective = SimpleNamespace(
            complete=self.cooldown is not None and not self.unresolved,
            effective_cooldown_seconds=self.cooldown,
            unresolved=self.unresolved,
        )
        return SimpleNamespace(effective=effective)


def test_resolves_effective_cooldown_from_canonical_build_evidence() -> None:
    cooldown = _CooldownService(cooldown=41.0)
    passive_calls = []

    def passive_resolver(player_build, progression):
        passive_calls.append((player_build, progression))
        return ("passive-grant",)

    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(build="canonical-build"),
        item_service=_ItemService(),
        cooldown_service=cooldown,
        passive_grant_resolver=passive_resolver,
    )
    scenario = ExtremeSustainedDPSPotionCooldownScenarioEvidence(
        effects=("scenario-effect",),
        complete=True,
    )

    result = service.resolve(
        player_build="saved-build",
        progression="progression",
        scenario=scenario,
    )

    assert result.complete
    assert result.cooldown_seconds == 41.0
    assert passive_calls == [("saved-build", "progression")]
    assert cooldown.calls[0]["character_build"] == "canonical-build"
    assert cooldown.calls[0]["passives"] == ("passive-grant",)
    assert cooldown.calls[0]["scenario_effects"] == ("scenario-effect",)
    assert cooldown.calls[0]["scenario_inventory_complete"] is True


def test_progression_without_passive_inventory_fails_closed() -> None:
    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(build="canonical-build"),
        item_service=_ItemService(),
        cooldown_service=_CooldownService(cooldown=45.0),
        passive_grant_resolver=lambda build, progression: (_ for _ in ()).throw(
            ValueError("Extreme potion cooldown PassiveGrant derivation requires explicit passive ranks")
        ),
    )

    result = service.resolve(
        player_build="saved-build",
        progression="progression",
        scenario=ExtremeSustainedDPSPotionCooldownScenarioEvidence(complete=True),
    )

    assert not result.complete
    assert result.cooldown_seconds is None
    assert any("PassiveGrant derivation" in item for item in result.unresolved)


def test_incomplete_scenario_inventory_does_not_emit_effective_cooldown() -> None:
    cooldown = _CooldownService(
        cooldown=None,
        unresolved=("canonical non-item potion cooldown effect inventory is not proven complete",),
    )
    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(build="canonical-build"),
        item_service=_ItemService(),
        cooldown_service=cooldown,
        passive_grant_resolver=lambda build, progression: ExtremePotionPassiveGrantEvidence(
            complete=True
        ),
    )

    result = service.resolve(player_build="saved-build", progression="progression")

    assert not result.complete
    assert result.cooldown_seconds is None
    assert result.resolution is None
    assert cooldown.calls == []
    assert any("not proven complete" in item for item in result.unresolved)


def test_failed_canonical_build_adaptation_fails_closed_before_cooldown_math() -> None:
    cooldown = _CooldownService()
    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(
            build=None,
            unresolved=("canonical build adaptation failed",),
        ),
        item_service=_ItemService(),
        cooldown_service=cooldown,
    )

    result = service.resolve(player_build="saved-build")

    assert not result.complete
    assert result.cooldown_seconds is None
    assert "canonical build adaptation failed" in result.unresolved
    assert cooldown.calls == []



def test_missing_progression_and_passive_evidence_fails_closed() -> None:
    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(build="canonical-build"),
        item_service=_ItemService(),
        cooldown_service=_CooldownService(cooldown=45.0),
    )

    result = service.resolve(
        player_build="saved-build",
        scenario=ExtremeSustainedDPSPotionCooldownScenarioEvidence(complete=True),
    )

    assert not result.complete
    assert result.cooldown_seconds is None
    assert any("requires passive progression" in item for item in result.unresolved)
    assert result.resolution is None



def test_competing_progression_and_explicit_passives_fail_closed() -> None:
    cooldown = _CooldownService(cooldown=44.0)
    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(build="canonical-build"),
        item_service=_ItemService(),
        cooldown_service=cooldown,
    )

    result = service.resolve(
        player_build="saved-build",
        progression="progression",
        passives=(object(),),
        passive_inventory_complete=True,
        scenario=ExtremeSustainedDPSPotionCooldownScenarioEvidence(complete=True),
    )

    assert not result.complete
    assert result.resolution is None
    assert cooldown.calls == []
    assert any("choose one authority" in item for item in result.unresolved)


def test_explicit_complete_empty_passive_inventory_can_resolve() -> None:
    cooldown = _CooldownService(cooldown=45.0)
    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(build="canonical-build"),
        item_service=_ItemService(),
        cooldown_service=cooldown,
    )

    result = service.resolve(
        player_build="saved-build",
        passive_inventory_complete=True,
        scenario=ExtremeSustainedDPSPotionCooldownScenarioEvidence(complete=True),
    )

    assert result.complete
    assert result.cooldown_seconds == 45.0


def test_explicit_passive_grants_require_complete_inventory_proof() -> None:
    cooldown = _CooldownService(cooldown=44.0)
    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(build="canonical-build"),
        item_service=_ItemService(),
        cooldown_service=cooldown,
    )
    passive = object()

    result = service.resolve(
        player_build="saved-build",
        passives=(passive,),
        scenario=ExtremeSustainedDPSPotionCooldownScenarioEvidence(complete=True),
    )

    assert not result.complete
    assert result.resolution is None
    assert cooldown.calls == []
    assert any("PassiveGrant inventory is not proven complete" in item for item in result.unresolved)


def test_incomplete_empty_passive_inventory_fails_closed() -> None:
    cooldown = _CooldownService(cooldown=45.0)
    service = ExtremeSustainedDPSPotionCooldownResolutionService(
        build_adapter=_BuildAdapter(build="canonical-build"),
        item_service=_ItemService(),
        cooldown_service=cooldown,
        passive_grant_resolver=lambda build, progression: ExtremePotionPassiveGrantEvidence(),
    )

    result = service.resolve(
        player_build="saved-build",
        progression="progression",
        scenario=ExtremeSustainedDPSPotionCooldownScenarioEvidence(complete=True),
    )

    assert not result.complete
    assert result.resolution is None
    assert cooldown.calls == []
    assert any("passive-grant inventory is not proven complete" in item for item in result.unresolved)
