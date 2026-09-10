import json

from minmax.rotation_demand_window import (
    RotationDemandKind,
    RotationDemandPattern,
    RotationDemandWindow,
)
from minmax.rotation_plan import RotationPlan
from services.encounter_projection import EncounterEvidenceFact, EncounterSource
from services.rotation_candidate_generation_service import GeneratedRotationCandidate
from services.rotation_candidate_healer_multi_demand_role_output_service import (
    RotationCandidateHealerDemandWindowOutput,
    RotationCandidateHealerMultiDemandOutput,
)
from services.rotation_healer_demand_criteria_service import (
    RotationCandidateHealerCriteriaHardObligationService,
)
from services.rotation_healer_demand_healing_evidence_service import (
    RotationHealerDemandHealingEvidence,
)
from services.rotation_healer_encounter_criteria_provider import (
    RotationHealerEncounterCriteriaProvider,
)


_DEMAND = RotationDemandWindow(
    name="execute burn",
    start_seconds=30.0,
    end_seconds=35.0,
    kind=RotationDemandKind.HEALING,
    pattern=RotationDemandPattern.SUSTAINED,
)


class _EncounterFacts:
    def __init__(self, fact):
        self.fact = fact

    def evidence_facts(self, encounter_id, fact_type=None):
        return (self.fact,)


class _WindowOutputService:
    def __init__(self, modeled_rate):
        self.modeled_rate = float(modeled_rate)

    def evaluate_windows(self, candidate):
        total = self.modeled_rate * _DEMAND.duration_seconds
        evidence = RotationHealerDemandHealingEvidence(
            demand=_DEMAND,
            direct_events=(),
            periodic_events=(),
            delayed_events=(),
            modeled_direct_healing=total,
            modeled_periodic_healing=0.0,
            modeled_delayed_healing=0.0,
            unresolved=(),
        )
        return RotationCandidateHealerMultiDemandOutput(
            candidate_id=candidate.candidate_id,
            windows=(
                RotationCandidateHealerDemandWindowOutput(
                    evidence=evidence,
                    modeled_healing_per_demand_second=self.modeled_rate,
                ),
            ),
            unresolved=(),
        )


def _candidate():
    return GeneratedRotationCandidate(
        candidate_id="healer",
        plan=RotationPlan(
            character_name="Healer Tester",
            build_name="Encounter Criteria Healer",
            duration_seconds=45.0,
            actions=(),
        ),
        refresh_leads=(),
        action_claims=(),
    )


def _fact():
    return EncounterEvidenceFact(
        fact_id="xalvakka:healer_demand_criterion:execute_burn",
        fact_type="healer_demand_criterion",
        fact_key="execute_burn",
        status="corroborated",
        value_json=json.dumps(
            {
                "demand_name": "execute burn",
                "minimum_modeled_healing_per_demand_second": 1250.0,
            }
        ),
        distinct_sources=2,
        distinct_values=1,
        evidence=(
            EncounterSource(
                url="https://example.test/source-a",
                page_title="Source A",
                revision_id="1",
                retrieved_at="2026-09-10",
                license="",
            ),
            EncounterSource(
                url="https://example.test/source-b",
                page_title="Source B",
                revision_id="2",
                retrieved_at="2026-09-10",
                license="",
            ),
        ),
    )


def test_reviewed_encounter_fact_can_fail_healer_hard_gate():
    fact = _fact()
    projection = RotationHealerEncounterCriteriaProvider(
        _EncounterFacts(fact)
    ).criteria_for_encounter(
        encounter_id="xalvakka",
        reviewed_fact_ids=(fact.fact_id,),
    )
    hard_gate = RotationCandidateHealerCriteriaHardObligationService(
        multi_demand_output_service=_WindowOutputService(1000.0),
        criteria=projection.criteria,
    )

    result = hard_gate.evaluate_plan(_candidate())

    assert result.satisfied is False
    assert len(result.reasons) == 1
    assert "execute burn" in result.reasons[0]
    assert "modeled 1000 < required 1250" in result.reasons[0]
    assert f"encounter_fact={fact.fact_id}" in result.reasons[0]
    assert "review_status=approved_for_hard_gate" in result.reasons[0]


def test_same_reconciled_fact_cannot_hard_fail_before_review_promotion():
    fact = _fact()
    projection = RotationHealerEncounterCriteriaProvider(
        _EncounterFacts(fact)
    ).criteria_for_encounter(encounter_id="xalvakka")
    hard_gate = RotationCandidateHealerCriteriaHardObligationService(
        multi_demand_output_service=_WindowOutputService(1000.0),
        criteria=projection.criteria,
    )

    result = hard_gate.evaluate_plan(_candidate())

    assert result.satisfied is True
    assert result.reasons == ()
