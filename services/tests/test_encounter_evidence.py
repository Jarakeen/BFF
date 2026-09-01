from services.encounter_evidence import EncounterEvidence, reconcile_encounter_evidence


def _evidence(*, value, source_name, source_type="guide"):
    return EncounterEvidence(
        encounter_id="lylanar_turlassil",
        fact_type="phase",
        fact_key="phase_4",
        value=value,
        source_type=source_type,
        source_name=source_name,
        confidence="high",
    )


def test_single_source_fact_remains_single_source():
    result = reconcile_encounter_evidence(
        [_evidence(value="Brothers Reunited", source_name="Nilandia vDSR guide")]
    )

    assert len(result) == 1
    assert result[0].status == "single_source"
    assert result[0].value == "Brothers Reunited"
    assert result[0].distinct_sources == 1
    assert result[0].distinct_values == 1
    assert result[0].safe_for_review is True


def test_independent_sources_agreeing_are_corroborated():
    result = reconcile_encounter_evidence(
        [
            _evidence(value={"both_brothers_active": True}, source_name="Nilandia vDSR guide"),
            _evidence(
                value={"both_brothers_active": True},
                source_name="UESP dialogue",
                source_type="uesp",
            ),
        ]
    )

    assert len(result) == 1
    assert result[0].status == "corroborated"
    assert result[0].value == {"both_brothers_active": True}
    assert result[0].distinct_sources == 2
    assert result[0].distinct_values == 1


def test_conflicting_sources_do_not_choose_a_winner():
    result = reconcile_encounter_evidence(
        [
            _evidence(value={"threshold": "65%"}, source_name="Nilandia vDSR guide"),
            _evidence(
                value={"threshold": "70%"},
                source_name="Combat Alerts",
                source_type="combat_addon",
            ),
        ]
    )

    assert len(result) == 1
    assert result[0].status == "conflicting"
    assert result[0].value is None
    assert result[0].distinct_sources == 2
    assert result[0].distinct_values == 2
    assert result[0].safe_for_review is False
