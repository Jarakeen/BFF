from services.encounter_service import EncounterTemporalEvidence
from services.encounter_temporal_audit import audit_encounter_temporal_evidence


class StubEncounterService:
    def encounter_ids(self):
        return ("a", "b")

    def temporal_evidence(self, encounter_id):
        if encounter_id == "a":
            return (
                EncounterTemporalEvidence(
                    temporal_id="a:f:duration_seconds",
                    encounter_id="a",
                    fact_id="a:f",
                    fact_type="mechanic_detail",
                    fact_key="duration",
                    value_key="duration_seconds",
                    seconds=6.0,
                    approximate=False,
                    reconciliation_status="single_source",
                    distinct_sources=1,
                    distinct_values=1,
                ),
                EncounterTemporalEvidence(
                    temporal_id="a:g:detonation_seconds_approx",
                    encounter_id="a",
                    fact_id="a:g",
                    fact_type="mechanic_detail",
                    fact_key="detonation",
                    value_key="detonation_seconds_approx",
                    seconds=5.0,
                    approximate=True,
                    reconciliation_status="corroborated",
                    distinct_sources=2,
                    distinct_values=1,
                ),
            )
        return ()


def test_temporal_audit_summarizes_exact_approximate_and_evidence_status():
    audit = audit_encounter_temporal_evidence(StubEncounterService())

    assert audit.temporal_value_count == 2
    assert audit.exact_value_count == 1
    assert audit.approximate_value_count == 1
    assert audit.single_source_value_count == 1
    assert audit.corroborated_value_count == 1
    assert audit.encounter_count == 1
    assert audit.rows[0].value_key == "duration_seconds"
    assert audit.rows[1].value_key == "detonation_seconds_approx"
