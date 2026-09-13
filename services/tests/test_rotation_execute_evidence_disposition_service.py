from minmax.skill_component_conditional_consequence import (
    SkillComponentConditionalConsequenceType,
)
from services.rotation_execute_candidate_evidence_service import (
    RotationExecuteCandidateEvidence,
    RotationExecuteComponentEvidence,
)
from services.rotation_execute_evidence_disposition_service import (
    RotationExecuteEvidenceDisposition,
    RotationExecuteEvidenceDispositionService,
)


class _EvidenceService:
    def __init__(self, result):
        self.result = result

    def resolve(self, skill_name):
        return self.result


def _component(kind, *, skill_name="Execute", maximum_bonus_fraction=None):
    if maximum_bonus_fraction is None and kind is SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE:
        maximum_bonus_fraction = 3.0
    return RotationExecuteComponentEvidence(
        skill_name=skill_name,
        entity_id="skill:1",
        skill_rank_id=1,
        coefficient_number=1,
        threshold=0.5,
        consequence_type=kind,
        maximum_bonus_fraction=maximum_bonus_fraction,
        condition_evidence="target below 50% Health",
        consequence_evidence="reviewed",
    )


def test_threshold_activation_is_scheduler_supported() -> None:
    evidence = RotationExecuteCandidateEvidence(
        requested_skill_name="Execute",
        resolved_skill_name="Execute",
        entity_id="skill:1",
        components=(_component(SkillComponentConditionalConsequenceType.ACTIVATES_COMPONENT),),
    )
    result = RotationExecuteEvidenceDispositionService(
        evidence_service=_EvidenceService(evidence)
    ).resolve("Execute")

    assert result.disposition is RotationExecuteEvidenceDisposition.THRESHOLD_ACTIVATION_SUPPORTED
    assert result.scheduler_supported is True
    assert result.unresolved == ()


def test_reviewed_continuous_amplification_is_scheduler_supported() -> None:
    evidence = RotationExecuteCandidateEvidence(
        requested_skill_name="Killer's Blade",
        resolved_skill_name="Killer's Blade",
        entity_id="skill:1",
        components=(
            _component(
                SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
                skill_name="Killer's Blade",
                maximum_bonus_fraction=4.0,
            ),
        ),
    )
    result = RotationExecuteEvidenceDispositionService(
        evidence_service=_EvidenceService(evidence)
    ).resolve("Killer's Blade")

    assert result.disposition is RotationExecuteEvidenceDisposition.CONTINUOUS_AMPLIFICATION_SUPPORTED
    assert result.scheduler_supported is True
    assert result.unresolved == ()


def test_unreviewed_continuous_amplification_is_positive_but_unresolved() -> None:
    evidence = RotationExecuteCandidateEvidence(
        requested_skill_name="Execute",
        resolved_skill_name="Execute",
        entity_id="skill:1",
        components=(_component(SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE),),
    )
    result = RotationExecuteEvidenceDispositionService(
        evidence_service=_EvidenceService(evidence)
    ).resolve("Execute")

    assert result.disposition is RotationExecuteEvidenceDisposition.CONTINUOUS_AMPLIFICATION_UNRESOLVED
    assert result.scheduler_supported is False
    assert "source-verified" in result.unresolved[0]


def test_reviewed_continuous_amplification_without_maximum_stays_unresolved() -> None:
    component = RotationExecuteComponentEvidence(
        skill_name="Killer's Blade",
        entity_id="skill:1",
        skill_rank_id=1,
        coefficient_number=1,
        threshold=0.5,
        consequence_type=SkillComponentConditionalConsequenceType.AMPLIFIES_DAMAGE,
        maximum_bonus_fraction=None,
        condition_evidence="target below 50% Health",
        consequence_evidence="reviewed",
    )
    evidence = RotationExecuteCandidateEvidence(
        requested_skill_name="Killer's Blade",
        resolved_skill_name="Killer's Blade",
        entity_id="skill:1",
        components=(component,),
    )
    result = RotationExecuteEvidenceDispositionService(
        evidence_service=_EvidenceService(evidence)
    ).resolve("Killer's Blade")

    assert result.disposition is RotationExecuteEvidenceDisposition.CONTINUOUS_AMPLIFICATION_UNRESOLVED
    assert result.scheduler_supported is False
    assert "maximum bonus evidence is incomplete" in result.unresolved[0]


def test_no_threshold_evidence_is_not_negative_execute_classification() -> None:
    evidence = RotationExecuteCandidateEvidence(
        requested_skill_name="Ordinary",
        resolved_skill_name="Ordinary",
        entity_id="skill:2",
    )
    result = RotationExecuteEvidenceDispositionService(
        evidence_service=_EvidenceService(evidence)
    ).resolve("Ordinary")

    assert result.disposition is RotationExecuteEvidenceDisposition.NO_THRESHOLD_EVIDENCE
    assert result.scheduler_supported is False


def test_identity_failure_is_explicitly_unresolved() -> None:
    evidence = RotationExecuteCandidateEvidence(
        requested_skill_name="Unknown",
        resolved_skill_name=None,
        entity_id=None,
        unresolved=("identity unresolved",),
    )
    result = RotationExecuteEvidenceDispositionService(
        evidence_service=_EvidenceService(evidence)
    ).resolve("Unknown")

    assert result.disposition is RotationExecuteEvidenceDisposition.IDENTITY_OR_SOURCE_UNRESOLVED
    assert result.unresolved == ("identity unresolved",)
