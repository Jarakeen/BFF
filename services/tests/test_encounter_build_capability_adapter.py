from __future__ import annotations

import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from services.encounter_build_capability_adapter import (
    EncounterCapabilityIdentityMap,
    SavedBuildEncounterCapabilityAdapter,
)
from services.encounter_requirement_evaluation import CapabilityAssessment
from services.saved_build_capability_service import SavedBuildCapabilityAudit


def _audit(
    *,
    name: str = "Healer",
    effects: tuple[EffectVariant, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name=name,
        build_name=f"{name} Build",
        character_id=f"id-{name}",
        resolved_effects=effects,
        unresolved=unresolved,
    )


def _effect(name: str, *, eligible: bool = True, source: str = "Skill") -> EffectVariant:
    return EffectVariant(
        name=name,
        layer=EffectLayer.CAST,
        source=source,
        eligible=eligible,
    )


def test_exact_mapped_effect_proves_capability_without_source_name_guessing():
    adapter = SavedBuildEncounterCapabilityAdapter(
        (
            EncounterCapabilityIdentityMap(
                capability_type="cleanse",
                effect_names=frozenset({"remove_negative_effects"}),
            ),
        )
    )
    audit = _audit(
        effects=(
            _effect("remove_negative_effects", source="Efficient Purge"),
            _effect("major_resolve", source="Definitely Contains Cleanse In Its Source Name"),
        )
    )

    row = adapter.evidence_for((audit,), ("cleanse",))[0]

    assert row.assessment == CapabilityAssessment.SUPPORTED
    assert row.source == "Efficient Purge"


def test_resolved_build_without_mapped_effect_is_explicitly_unsupported():
    adapter = SavedBuildEncounterCapabilityAdapter(
        (
            EncounterCapabilityIdentityMap(
                capability_type="cleanse",
                effect_names=frozenset({"remove_negative_effects"}),
            ),
        )
    )
    audit = _audit(effects=(_effect("major_resolve"),))

    row = adapter.evidence_for((audit,), ("cleanse",))[0]

    assert row.assessment == CapabilityAssessment.UNSUPPORTED


def test_unresolved_build_without_match_stays_unknown_not_unsupported():
    adapter = SavedBuildEncounterCapabilityAdapter(
        (
            EncounterCapabilityIdentityMap(
                capability_type="cleanse",
                effect_names=frozenset({"remove_negative_effects"}),
            ),
        )
    )
    audit = _audit(
        effects=(_effect("major_resolve"),),
        unresolved=("skill not found",),
    )

    row = adapter.evidence_for((audit,), ("cleanse",))[0]

    assert row.assessment == CapabilityAssessment.UNKNOWN


def test_ineligible_mapped_effect_stays_unknown():
    adapter = SavedBuildEncounterCapabilityAdapter(
        (
            EncounterCapabilityIdentityMap(
                capability_type="cleanse",
                effect_names=frozenset({"remove_negative_effects"}),
            ),
        )
    )
    audit = _audit(effects=(_effect("remove_negative_effects", eligible=False),))

    row = adapter.evidence_for((audit,), ("cleanse",))[0]

    assert row.assessment == CapabilityAssessment.UNKNOWN


def test_unmapped_capability_type_stays_unknown_even_for_resolved_build():
    adapter = SavedBuildEncounterCapabilityAdapter(())

    row = adapter.evidence_for((_audit(),), ("cleanse",))[0]

    assert row.assessment == CapabilityAssessment.UNKNOWN


def test_duplicate_capability_maps_are_rejected():
    entry = EncounterCapabilityIdentityMap("cleanse", frozenset({"x"}))
    with pytest.raises(ValueError, match="duplicate"):
        SavedBuildEncounterCapabilityAdapter((entry, entry))
