from types import SimpleNamespace

import pytest

from services.extreme_sustained_dps_candidate_runtime_state_factory_service import (
    ExtremeSustainedDPSCandidateRuntimeStateFactoryService,
)


class _CapabilityService:
    def resolve_effect_variants(self, _build):
        return SimpleNamespace(
            effects=(),
            unresolved=(),
            boundaries=(),
        )


def _occurrence_provider(_state):
    return object()


def test_factory_wires_canonical_weapon_enchantment_runtime_stack(tmp_path):
    poison_consequence_resolver = object()
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
        database_path=tmp_path / "eso.db",
        capability_service=_CapabilityService(),
        occurrence_provider_resolver=_occurrence_provider,
        supplemental_event_denominator_proven=True,
        supplemental_history_denominator_proven=True,
        weapon_poison_consequence_resolver=poison_consequence_resolver,
    )

    scenario = resolver.scenario_frontier
    universe = scenario.runtime_effect_universe
    cooldown = scenario.weapon_enchantment_cooldown_policy_resolver

    assert resolver.occurrence_provider_resolver is _occurrence_provider
    assert resolver.supplemental_event_denominator_proven is True
    assert resolver.supplemental_history_denominator_proven is True
    assert universe.weapon_enchantment_runtime_source_service is not None
    assert universe.weapon_enchantment_runtime_variant_service is not None
    assert scenario.runtime_effect_scaling is not None
    assert scenario.weapon_enchantment_activation_service is not None
    assert scenario.weapon_poison_activation_service is not None
    assert scenario.weapon_poison_consequence_resolver is poison_consequence_resolver
    assert cooldown is not None
    assert (
        cooldown.runtime_source_service
        is universe.weapon_enchantment_runtime_source_service
    )
    assert (
        cooldown.cooldown_rule_resolver
        is universe.weapon_enchantment_runtime_source_service.effect_service
    )


def test_factory_requires_capability_service(tmp_path):
    with pytest.raises(
        ValueError,
        match="canonical saved-build capability service",
    ):
        ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
            database_path=tmp_path / "eso.db",
            capability_service=None,
            occurrence_provider_resolver=_occurrence_provider,
            supplemental_event_denominator_proven=True,
            supplemental_history_denominator_proven=True,
        )


def test_factory_requires_pre_runtime_occurrence_authority(tmp_path):
    with pytest.raises(
        ValueError,
        match="pre-runtime exact damage-occurrence authority",
    ):
        ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
            database_path=tmp_path / "eso.db",
            capability_service=_CapabilityService(),
            occurrence_provider_resolver=None,
            supplemental_event_denominator_proven=True,
            supplemental_history_denominator_proven=True,
        )

def test_factory_leaves_poison_consequence_authority_unset_when_not_supplied(tmp_path):
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
        database_path=tmp_path / "eso.db",
        capability_service=_CapabilityService(),
        occurrence_provider_resolver=_occurrence_provider,
        supplemental_event_denominator_proven=True,
        supplemental_history_denominator_proven=True,
    )

    assert resolver.scenario_frontier.weapon_poison_consequence_resolver is None

