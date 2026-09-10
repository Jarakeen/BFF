import json

from services.encounter_projection import EncounterEvidenceFact, EncounterSource
from services.rotation_healer_demand_criteria_service import (
    RotationHealerDemandCriterionSourceKind,
)
from services.rotation_healer_encounter_criteria_provider import (
    RotationHealerEncounterCriteriaProvider,
)


class _EncounterFacts:
    def __init__(self, facts):
        self.facts = tuple(facts)
        self.calls = []

    def evidence_facts(self, encounter_id, fact_type=None):
        self.calls.append((encounter_id, fact_type))
        return self.facts


def _source(name="Reviewed Guide"):
    return EncounterSource(
        url="https://example.test/guide",
        page_title=name,
        revision_id="r1",
        retrieved_at="2026-09-10",
        license="",
    )


def _fact(
    *,
    fact_id="xalvakka:healer_demand_criterion:execute_burn",
    demand_name="execute burn",
    minimum=1250.0,
    status="corroborated",
    value_json=None,
    distinct_sources=2,
):
    if value_json is None:
        value_json = json.dumps(
            {
                "demand_name": demand_name,
                "minimum_modeled_healing_per_demand_second": minimum,
            }
        )
    return EncounterEvidenceFact(
        fact_id=fact_id,
        fact_type="healer_demand_criterion",
        fact_key="execute_burn",
        status=status,
        value_json=value_json,
        distinct_sources=distinct_sources,
        distinct_values=1 if status != "conflicting" else 2,
        evidence=(_source(),),
    )


def test_approved_fact_becomes_verified_encounter_criterion_with_provenance():
    fact = _fact()
    provider = RotationHealerEncounterCriteriaProvider(_EncounterFacts((fact,)))

    result = provider.criteria_for_encounter(
        encounter_id="xalvakka",
        reviewed_fact_ids=(fact.fact_id,),
    )

    assert result.unresolved == ()
    assert len(result.criteria) == 1
    criterion = result.criteria[0]
    assert criterion.demand_name == "execute burn"
    assert criterion.minimum_modeled_healing_per_demand_second == 1250.0
    assert (
        criterion.source_kind
        is RotationHealerDemandCriterionSourceKind.VERIFIED_ENCOUNTER_EVIDENCE
    )
    assert f"encounter_fact={fact.fact_id}" in criterion.provenance
    assert "reconciliation_status=corroborated" in criterion.provenance
    assert "review_status=approved_for_hard_gate" in criterion.provenance


def test_unreviewed_reconciled_fact_remains_non_authoritative():
    fact = _fact(status="corroborated")
    provider = RotationHealerEncounterCriteriaProvider(_EncounterFacts((fact,)))

    result = provider.criteria_for_encounter(encounter_id="xalvakka")

    criterion = result.criteria[0]
    assert (
        criterion.source_kind
        is RotationHealerDemandCriterionSourceKind.CALLER_ASSUMPTION
    )
    assert "review_status=not_promoted" in criterion.provenance


def test_conflicting_fact_never_becomes_criterion_even_if_review_id_is_supplied():
    fact = _fact(status="conflicting", value_json=None)
    provider = RotationHealerEncounterCriteriaProvider(_EncounterFacts((fact,)))

    result = provider.criteria_for_encounter(
        encounter_id="xalvakka",
        reviewed_fact_ids=(fact.fact_id,),
    )

    assert result.criteria == ()
    assert result.unresolved == (
        f"{fact.fact_id}: healer demand criterion value must be an object",
    )


def test_invalid_structured_value_fails_closed_without_inventing_threshold():
    fact = _fact(
        value_json=json.dumps(
            {
                "demand_name": "execute burn",
                "minimum_modeled_healing_per_demand_second": "a lot",
            }
        )
    )
    provider = RotationHealerEncounterCriteriaProvider(_EncounterFacts((fact,)))

    result = provider.criteria_for_encounter(encounter_id="xalvakka")

    assert result.criteria == ()
    assert result.unresolved == (
        f"{fact.fact_id}: healer demand criterion has invalid minimum modeled output",
    )


def test_provider_requests_only_explicit_healer_criterion_fact_type():
    facts = _EncounterFacts((_fact(),))
    provider = RotationHealerEncounterCriteriaProvider(facts)

    provider.criteria_for_encounter(encounter_id="xalvakka")

    assert facts.calls == [("xalvakka", "healer_demand_criterion")]
