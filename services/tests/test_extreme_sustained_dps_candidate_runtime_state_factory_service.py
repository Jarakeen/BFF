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

def test_factory_builds_poison_consequence_frontier_from_dilution_authority(tmp_path):
    dilution_resolver = object()
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
        database_path=tmp_path / "eso.db",
        capability_service=_CapabilityService(),
        occurrence_provider_resolver=_occurrence_provider,
        supplemental_event_denominator_proven=True,
        supplemental_history_denominator_proven=True,
        weapon_poison_dilution_selection_resolver=dilution_resolver,
    )

    consequence = resolver.scenario_frontier.weapon_poison_consequence_resolver
    assert consequence is not None
    assert consequence.consequence_resolver.dilution_selection_resolver is dilution_resolver


def test_factory_rejects_competing_poison_consequence_authorities(tmp_path):
    with pytest.raises(
        ValueError,
        match="requires exactly one poison consequence authority path",
    ):
        ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
            database_path=tmp_path / "eso.db",
            capability_service=_CapabilityService(),
            occurrence_provider_resolver=_occurrence_provider,
            supplemental_event_denominator_proven=True,
            supplemental_history_denominator_proven=True,
            weapon_poison_consequence_resolver=object(),
            weapon_poison_dilution_selection_resolver=object(),
        )



def test_factory_can_forward_candidate_scoped_poison_consequence_authority(tmp_path):
    authority_resolver = lambda state: object()
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
        database_path=tmp_path / "eso.db",
        capability_service=_CapabilityService(),
        occurrence_provider_resolver=_occurrence_provider,
        supplemental_event_denominator_proven=True,
        supplemental_history_denominator_proven=True,
        weapon_poison_consequence_resolver_resolver=authority_resolver,
    )

    assert (
        resolver.weapon_poison_consequence_resolver_resolver
        is authority_resolver
    )
    assert resolver.scenario_frontier.weapon_poison_consequence_resolver is None


def test_factory_rejects_candidate_scoped_and_global_poison_authorities(tmp_path):
    with pytest.raises(
        ValueError,
        match="requires exactly one poison consequence authority path",
    ):
        ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
            database_path=tmp_path / "eso.db",
            capability_service=_CapabilityService(),
            occurrence_provider_resolver=_occurrence_provider,
            supplemental_event_denominator_proven=True,
            supplemental_history_denominator_proven=True,
            weapon_poison_consequence_resolver=object(),
            weapon_poison_consequence_resolver_resolver=lambda state: object(),
        )


def test_factory_builds_generated_candidate_poison_authority_path(tmp_path):
    item_resolver = object()
    mode_resolver = object()
    resolver = ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
        database_path=tmp_path / "eso.db",
        capability_service=_CapabilityService(),
        occurrence_provider_resolver=_occurrence_provider,
        supplemental_event_denominator_proven=True,
        supplemental_history_denominator_proven=True,
        generated_weapon_poison_item_evidence_resolver=item_resolver,
        generated_weapon_poison_dilution_mode_resolver=mode_resolver,
    )

    candidate_resolver = resolver.weapon_poison_consequence_resolver_resolver
    assert candidate_resolver is not None
    owner = candidate_resolver.__self__
    assert owner.item_evidence_resolver is item_resolver
    assert owner.dilution_mode_resolver is mode_resolver
    assert resolver.scenario_frontier.weapon_poison_consequence_resolver is None


def test_factory_requires_both_generated_poison_witness_resolvers(tmp_path):
    with pytest.raises(
        ValueError,
        match="requires both candidate tier/item evidence and candidate dilution-mode resolvers",
    ):
        ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
            database_path=tmp_path / "eso.db",
            capability_service=_CapabilityService(),
            occurrence_provider_resolver=_occurrence_provider,
            supplemental_event_denominator_proven=True,
            supplemental_history_denominator_proven=True,
            generated_weapon_poison_item_evidence_resolver=object(),
        )


def test_factory_rejects_generated_and_existing_poison_authority_paths(tmp_path):
    with pytest.raises(
        ValueError,
        match="requires exactly one poison consequence authority path",
    ):
        ExtremeSustainedDPSCandidateRuntimeStateFactoryService.build(
            database_path=tmp_path / "eso.db",
            capability_service=_CapabilityService(),
            occurrence_provider_resolver=_occurrence_provider,
            supplemental_event_denominator_proven=True,
            supplemental_history_denominator_proven=True,
            weapon_poison_consequence_resolver=object(),
            generated_weapon_poison_item_evidence_resolver=object(),
            generated_weapon_poison_dilution_mode_resolver=object(),
        )
