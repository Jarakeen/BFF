import pytest

from services.rotation_detonating_siphon_spatial_evidence_service import (
    DetonatingSiphonAreaAnchor,
    RotationDetonatingSiphonSpatialEvidenceService,
)
from services.rotation_runtime_output_eligibility_service import (
    DETONATING_SIPHON_GEOMETRY_CONDITION,
)
from services.rotation_runtime_spatial_condition_context_service import (
    RotationRuntimeSpatialCircleClause,
    RotationRuntimeSpatialSegmentClause,
)


def test_reviewed_siphon_spatial_evidence_keeps_disputed_geometry_unresolved() -> None:
    evidence = RotationDetonatingSiphonSpatialEvidenceService().evidence()

    assert evidence.radius_meters == 5.0
    assert evidence.maximum_range_meters == 28.0
    assert evidence.area_anchor is None
    assert evidence.tether_half_width_meters is None
    assert evidence.executable is False
    assert any("area anchor" in item for item in evidence.unresolved)
    assert any("corridor width" in item for item in evidence.unresolved)


def test_siphon_rule_fails_closed_until_anchor_and_tether_width_are_explicit() -> None:
    service = RotationDetonatingSiphonSpatialEvidenceService()

    assert service.rule(area_anchor=None, tether_half_width_meters=None) is None
    assert (
        service.rule(
            area_anchor=DetonatingSiphonAreaAnchor.CORPSE,
            tether_half_width_meters=None,
        )
        is None
    )
    assert service.rule(area_anchor=None, tether_half_width_meters=1.0) is None


def test_explicit_corpse_anchor_builds_reviewed_radius_plus_tether_rule() -> None:
    rule = RotationDetonatingSiphonSpatialEvidenceService().rule(
        area_anchor=DetonatingSiphonAreaAnchor.CORPSE,
        tether_half_width_meters=0.75,
    )

    assert rule is not None
    assert rule.condition == DETONATING_SIPHON_GEOMETRY_CONDITION
    assert len(rule.clauses) == 2
    circle, segment = rule.clauses
    assert isinstance(circle, RotationRuntimeSpatialCircleClause)
    assert circle.center_entity_id == "corpse"
    assert circle.target_entity_id == "target"
    assert circle.maximum_distance == 5.0
    assert isinstance(segment, RotationRuntimeSpatialSegmentClause)
    assert segment.start_entity_id == "caster"
    assert segment.end_entity_id == "corpse"
    assert segment.target_entity_id == "target"
    assert segment.half_width == 0.75


def test_explicit_caster_anchor_is_supported_without_claiming_it_as_default() -> None:
    rule = RotationDetonatingSiphonSpatialEvidenceService().rule(
        area_anchor="caster",
        tether_half_width_meters=1.25,
        caster_entity_id="player",
        corpse_entity_id="corpse-a",
        target_entity_id="boss",
    )

    assert rule is not None
    circle = rule.clauses[0]
    segment = rule.clauses[1]
    assert isinstance(circle, RotationRuntimeSpatialCircleClause)
    assert circle.center_entity_id == "player"
    assert circle.target_entity_id == "boss"
    assert isinstance(segment, RotationRuntimeSpatialSegmentClause)
    assert segment.start_entity_id == "player"
    assert segment.end_entity_id == "corpse-a"
    assert segment.target_entity_id == "boss"
    assert "area anchor=caster" in rule.source


def test_negative_explicit_tether_width_is_rejected() -> None:
    with pytest.raises(ValueError, match="half-width"):
        RotationDetonatingSiphonSpatialEvidenceService().rule(
            area_anchor="corpse",
            tether_half_width_meters=-0.1,
        )
