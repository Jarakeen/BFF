from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from minmax.character_build.effect_instance import EffectVariant
from minmax.character_build.effect_layer import EffectLayer
from minmax.coverage_classification import CoverageClassification
from services.encounter_build_capability_adapter import (
    EncounterCapabilityIdentityMap,
    SavedBuildEncounterCapabilityAdapter,
)
from services.encounter_cleanse_method import CleanseMethod
from services.encounter_repository import EncounterRepository
from services.encounter_requirement_evaluation import RequirementSemantics
from services.encounter_roster_evaluation import EncounterRosterEvaluator
from services.encounter_service import EncounterService
from services.saved_build_capability_service import SavedBuildCapabilityAudit


ROOT = Path(__file__).resolve().parents[2]


def _encounter_service() -> EncounterService:
    return EncounterService(EncounterRepository.from_data_root(ROOT / "data"))


def _audit(
    name: str,
    effects: tuple[EffectVariant, ...] = (),
    unresolved: tuple[str, ...] = (),
) -> SavedBuildCapabilityAudit:
    return SavedBuildCapabilityAudit(
        character_name=name,
        build_name=f"{name} Build",
        character_id=f"id-{name}",
        resolved_effects=tuple(effects),
        unresolved=tuple(unresolved),
    )


def _effect(name: str, source: str) -> EffectVariant:
    return EffectVariant(name=name, layer=EffectLayer.CAST, source=source)


def test_real_oaxiltso_saved_build_audits_do_not_overclaim_generic_cleanse_coverage():
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

    # The raw generic requirement remains compliance, not provider coverage.
    # Efficient Purge is therefore not promoted into a provider for Noxious Sludge.
    assert cleanse.semantics == RequirementSemantics.COMPLIANCE
    assert cleanse.classification == CoverageClassification.UNKNOWN
    assert cleanse.providers == ()
    assert cleanse.unknown_members == ("id-Tank", "id-Healer", "id-DD")

    # The integrated report can still be capability-ready because Phase 10 has
    # independent source-backed execution semantics for the encounter mechanic.
    assert result.is_fully_covered is True

    # The same report explains *how* the current source evidence says the cleanse
    # happens, without pretending the healer's Purge is therefore the solution.
    assert len(result.cleanse_methods) == 1
    method = result.cleanse_methods[0]
    assert method.method == CleanseMethod.ENCOUNTER_INTERACTION
    assert method.interaction == "cleanse_pool"
    assert method.requires_player_build_capability is False
    assert method.player_skill_effectiveness_known is False

    execution_cleanse = next(
        row for row in result.execution_evaluation.results
        if row.requirement_type == "cleanse"
    )
    assert execution_cleanse.classification == CoverageClassification.COVERED
    assert execution_cleanse.requires_player_build_capability is False
    assert result.execution_evaluation.unknown == ()
    assert result.execution_evaluation.is_fully_ready is True


def test_distinct_multi_member_roster_evaluates_one_encounter_once():
    evaluator = EncounterRosterEvaluator(
        _encounter_service(),
        SavedBuildEncounterCapabilityAdapter(()),
    )
    audits = (
        _audit("Tank"),
        _audit("Healer"),
        _audit("DD1"),
        _audit("DD2"),
    )

    result = evaluator.evaluate_saved_build_audits("achelir", audits)

    assert result.encounter_id == "achelir"
    assert result.execution_evaluation.is_fully_ready is True
    interrupt = next(
        row for row in result.execution_evaluation.results
        if row.requirement_type == "interrupt"
    )
    assert interrupt.classification == CoverageClassification.COVERED
    assert interrupt.handling_method == "core_bash"
    assert result.is_fully_covered is True


def test_multiple_selected_builds_for_same_character_are_rejected():
    evaluator = EncounterRosterEvaluator(
        _encounter_service(),
        SavedBuildEncounterCapabilityAdapter(()),
    )
    first = _audit("Magrat")
    second = replace(first, build_name="Magrat Alternate")

    with pytest.raises(ValueError, match="one authoritative build per roster member"):
        evaluator.evaluate_saved_build_audits("achelir", (first, second))
