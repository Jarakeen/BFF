from minmax.rotation_plan import RotationActionKind
from services.encounter_evidence import EncounterEvidence, ReconciledEncounterFact
from services.rotation_tank_encounter_defensive_obligation_service import (
    RotationTankEncounterDefensiveObligationService,
    RotationTankEncounterDefensiveWindowBinding,
)


def _evidence(*, value, source_name="Reviewed Guide") -> EncounterEvidence:
    return EncounterEvidence(
        encounter_id="test_boss",
        fact_type="mechanic_detail",
        fact_key="heavy_attack_response",
        value=value,
        source_type="guide",
        source_name=source_name,
        source_locator="Heavy Attack",
        confidence="high",
    )


def _fact(*, value, status="single_source") -> ReconciledEncounterFact:
    evidence = (_evidence(value=value),)
    return ReconciledEncounterFact(
        encounter_id="test_boss",
        fact_type="mechanic_detail",
        fact_key="heavy_attack_response",
        status=status,
        value=None if status == "conflicting" else value,
        evidence=evidence,
        distinct_sources=1,
        distinct_values=2 if status == "conflicting" else 1,
    )


def _binding(**overrides) -> RotationTankEncounterDefensiveWindowBinding:
    values = {
        "fact_type": "mechanic_detail",
        "fact_key": "heavy_attack_response",
        "window_start_seconds": 10.0,
        "window_end_seconds": 10.8,
        "minimum_responses": 1,
        "bar": "front",
    }
    values.update(overrides)
    return RotationTankEncounterDefensiveWindowBinding(**values)


def test_projects_explicit_block_and_dodge_fields_into_obligation() -> None:
    projection = RotationTankEncounterDefensiveObligationService.project(
        fact=_fact(value={"blockable": True, "dodgeable": True}),
        binding=_binding(),
    )

    assert projection.resolved is True
    assert projection.unresolved == ()
    assert projection.obligation is not None
    assert projection.obligation.allowed_actions == (
        RotationActionKind.BLOCK,
        RotationActionKind.DODGE,
    )
    assert projection.obligation.window_start_seconds == 10.0
    assert projection.obligation.window_end_seconds == 10.8
    assert projection.obligation.bar == "front"
    assert projection.obligation.provenance == ("Reviewed Guide", "Heavy Attack")


def test_projects_explicit_response_list_without_interpreting_prose() -> None:
    projection = RotationTankEncounterDefensiveObligationService.project(
        fact=_fact(value={"responses": ["dodge", "block"], "notes": "very dangerous"}),
        binding=_binding(bar=None),
    )

    assert projection.resolved is True
    assert projection.obligation is not None
    assert projection.obligation.allowed_actions == (
        RotationActionKind.DODGE,
        RotationActionKind.BLOCK,
    )


def test_fails_closed_when_structured_fact_has_no_explicit_block_or_dodge_field() -> None:
    projection = RotationTankEncounterDefensiveObligationService.project(
        fact=_fact(value={"target": "taunt_target", "warning": "tank should react"}),
        binding=_binding(),
    )

    assert projection.obligation is None
    assert projection.unresolved == (
        "heavy_attack_response: structured encounter evidence does not explicitly permit block or dodge",
    )


def test_conflicting_encounter_evidence_does_not_become_obligation() -> None:
    projection = RotationTankEncounterDefensiveObligationService.project(
        fact=_fact(value={"blockable": True}, status="conflicting"),
        binding=_binding(),
    )

    assert projection.obligation is None
    assert projection.unresolved == (
        "heavy_attack_response: encounter defensive evidence is conflicting",
    )


def test_binding_must_match_exact_reviewed_fact_identity() -> None:
    projection = RotationTankEncounterDefensiveObligationService.project(
        fact=_fact(value={"blockable": True}),
        binding=_binding(fact_key="different_mechanic"),
    )

    assert projection.obligation is None
    assert projection.unresolved == (
        "tank defensive encounter binding does not match reviewed fact identity",
    )


def test_false_blockable_and_dodgeable_fields_do_not_create_permission() -> None:
    projection = RotationTankEncounterDefensiveObligationService.project(
        fact=_fact(value={"blockable": False, "dodgeable": False}),
        binding=_binding(),
    )

    assert projection.obligation is None
    assert projection.unresolved
