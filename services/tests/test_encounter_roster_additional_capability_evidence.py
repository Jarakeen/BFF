from types import SimpleNamespace

from services.encounter_requirement_evaluation import (
    CapabilityAssessment,
    RequirementSemantics,
    RosterCapabilityEvidence,
)
from services.encounter_roster_evaluation import EncounterRosterEvaluator
from services.encounter_service import EncounterRequirement


class _EncounterService:
    def requirements(self, encounter_id):
        return (
            EncounterRequirement(
                requirement_id=f"{encounter_id}:tank:boss_taunt",
                encounter_id=encounter_id,
                mechanic_id="raid-tank-responsibility",
                mechanic_name="Boss Taunt Ownership",
                requirement_type="taunt",
                target_count=None,
                interpretation_status="configured_raid_tank_responsibility",
            ),
        )

    def get(self, encounter_id):
        return SimpleNamespace(
            encounter_id=encounter_id,
            mechanics=(),
            phases=(),
        )


class _EffectAdapter:
    @staticmethod
    def member_id(audit):
        return audit.character_id

    def evidence_for(self, audits, capability_types):
        return tuple(
            RosterCapabilityEvidence(
                member_id=audit.character_id,
                capability_type=capability_type,
                assessment=CapabilityAssessment.UNKNOWN,
                source="no EffectVariant mapping",
            )
            for audit in audits
            for capability_type in capability_types
        )


class _Execution:
    def evaluate(self, encounter_id, difficulty):
        return SimpleNamespace(is_fully_evaluable=True, is_fully_ready=True)


class _Methods:
    def methods(self, encounter_id):
        return ()


def _evaluator():
    evaluator = EncounterRosterEvaluator(
        _EncounterService(),
        _EffectAdapter(),
        requirement_semantics={"taunt": RequirementSemantics.PROVIDER_CAPABILITY},
    )
    evaluator._execution_evaluator = _Execution()
    evaluator._cleanse_methods = _Methods()
    evaluator._interrupt_methods = _Methods()
    return evaluator


def test_additional_utility_evidence_can_resolve_provider_capability():
    audit = SimpleNamespace(character_id="tank-a")
    evidence = RosterCapabilityEvidence(
        member_id="tank-a",
        capability_type="taunt",
        assessment=CapabilityAssessment.SUPPORTED,
        source="canonical slotted utility: Pierce Armor (front)",
    )

    report = _evaluator().evaluate_saved_build_audits(
        "xalvakka",
        (audit,),
        additional_capability_evidence=(evidence,),
    )

    result = report.provider_results[0]
    assert result.providers == ("tank-a",)
    assert result.is_satisfied is True
    assert evidence in report.capability_evidence


def test_additional_evidence_rejects_non_roster_member():
    audit = SimpleNamespace(character_id="tank-a")
    evidence = RosterCapabilityEvidence(
        member_id="tank-b",
        capability_type="taunt",
        assessment=CapabilityAssessment.SUPPORTED,
        source="test",
    )

    try:
        _evaluator().evaluate_saved_build_audits(
            "xalvakka",
            (audit,),
            additional_capability_evidence=(evidence,),
        )
    except ValueError as exc:
        assert "non-roster members" in str(exc)
    else:
        raise AssertionError("foreign additional capability evidence should fail closed")
