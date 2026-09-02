from __future__ import annotations

from pathlib import Path

import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.coverage_classification import CoverageClassification
from services.encounter_build_capability_adapter import (
    EncounterCapabilityIdentityMap,
    SavedBuildEncounterCapabilityAdapter,
)
from services.encounter_repository import EncounterRepository
from services.encounter_roster_evaluation import EncounterRosterEvaluator
from services.encounter_service import EncounterService
from services.saved_build_capability_service import SavedBuildCapabilityAudit


ROOT = Path(__file__).resolve().parents[2]


def _encounter_service() -> EncounterService:
    return EncounterService(EncounterRepository.from_data_root(ROOT / "data"))


def _audit(name: str, effects=(), unresolved=()) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name=name,
        build_name=f"{name} Build",
        character_id=f"id-{name}",
        resolved_effects=tuple(effects),
        unresolved=tuple(unresolved),
    )


def _effect(name: str, source: str) -> EffectVariant:
    return EffectVariant(name=name, layer=EffectLayer.CAST, source=source)


def test_real_oaxiltso_saved_build_audits_flow_into_requirement_evaluation():
    adapter = SavedBuildEncounterCapabilityAdapter(
        (
            EncounterCapabilityIdentityMap(
                "cleanse",
                frozenset({"remove_negative_effects"}),
            ),
        )
    )
    evaluator = EncounterRosterEvaluator(_encounter_service(), adapter)
    audits = (
        _audit("Tank", (_effect("major_resolve", "Armor"),)),
        _audit("Healer", (_effect("remove_negative_effects", "Efficient Purge"),)),
        _audit("DD", (_effect("minor_force", "Skill"),)),
    )

    result = evaluator.evaluate_saved_build_audits("oaxiltso", audits)
    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.classification == CoverageClassification.COVERED
    assert cleanse.providers == ("Healer",)
    assert any(row.classification == CoverageClassification.UNKNOWN for row in result.results)
    assert result.is_fully_covered is False


def test_unmapped_provider_capability_remains_unknown_through_full_orchestration():
    evaluator = EncounterRosterEvaluator(
        _encounter_service(),
        SavedBuildEncounterCapabilityAdapter(()),
    )

    result = evaluator.evaluate_saved_build_audits(
        "oaxiltso",
        (_audit("Healer"),),
    )
    cleanse = next(row for row in result.results if row.requirement_type == "cleanse")

    assert cleanse.classification == CoverageClassification.UNKNOWN


def test_duplicate_roster_member_identity_is_rejected_before_evaluation():
    evaluator = EncounterRosterEvaluator(
        _encounter_service(),
        SavedBuildEncounterCapabilityAdapter(()),
    )

    with pytest.raises(ValueError, match="one authoritative build"):
        evaluator.evaluate_saved_build_audits(
            "oaxiltso",
            (_audit("Same"), _audit("Same")),
        )
