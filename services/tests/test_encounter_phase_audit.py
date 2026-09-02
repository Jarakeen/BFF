from types import SimpleNamespace

from services.encounter_phase_audit import audit_encounter_phases


class _StubEncounterService:
    def __init__(self, encounters):
        self._encounters = encounters

    def encounter_ids(self):
        return tuple(sorted(self._encounters))

    def get(self, encounter_id):
        return self._encounters[encounter_id]


def test_phase_audit_parses_only_unambiguous_single_percent_thresholds():
    service = _StubEncounterService(
        {
            "sample": SimpleNamespace(
                phases=(
                    SimpleNamespace(
                        phase_id="sample:phase:1",
                        label="First",
                        threshold=" 75% ",
                    ),
                    SimpleNamespace(
                        phase_id="sample:phase:2",
                        label="Repeated summons",
                        threshold="90%/75%/50%/25%",
                    ),
                ),
                evidence_facts=(),
            )
        }
    )

    audit = audit_encounter_phases(service)

    assert len(audit.phases) == 2
    assert audit.parsed_phase_count == 1
    assert audit.unresolved_phase_count == 1
    assert audit.phases[0].threshold_percent == 75
    assert audit.phases[0].resolution == "parsed"
    assert audit.phases[1].threshold_percent is None
    assert audit.phases[1].resolution == "unresolved"


def test_phase_audit_preserves_transition_evidence_status_without_choosing_winner():
    service = _StubEncounterService(
        {
            "sample": SimpleNamespace(
                phases=(),
                evidence_facts=(
                    SimpleNamespace(
                        fact_type="transition",
                        fact_id="sample:transition:phase_2",
                        fact_key="phase_2",
                        status="corroborated",
                        value_json='{"threshold": "75%"}',
                    ),
                    SimpleNamespace(
                        fact_type="Transition",
                        fact_id="sample:transition:phase_3",
                        fact_key="phase_3",
                        status="conflicting",
                        value_json=None,
                    ),
                    SimpleNamespace(
                        fact_type="timer",
                        fact_id="sample:timer:ability",
                        fact_key="ability",
                        status="corroborated",
                        value_json="12.0",
                    ),
                ),
            )
        }
    )

    audit = audit_encounter_phases(service)

    assert tuple(row.fact_key for row in audit.transitions) == ("phase_2", "phase_3")
    assert audit.corroborated_transition_count == 1
    assert audit.conflicting_transition_count == 1
    assert audit.transitions[1].value_json is None
