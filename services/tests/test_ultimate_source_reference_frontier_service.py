from services.ultimate_source_reference_frontier_service import (
    UltimateSourceReferenceFrontierService,
    UltimateSourceRouteStatus,
)


_FIXTURE = """
<span class="uc-section-title">Skills</span>
<div data-source="exhilarating_drain">
  <span class="hx-tip-trigger__label">Exhilarating Drain</span>
  <span class="uc-val">5<span>/1s</span></span>
</div>
<span class="uc-section-title">Other</span>
<div data-source="light_attack">
  <span class="uc-name">Base Ultimate Regen</span>
  <span class="uc-val">3<span>/1s</span></span>
</div>
<button data-class-source="blessing_peak">
  <span class="hx-tip-trigger__label">Blessing at the Peak</span>
</button>
<div id="uc-decisive"></div>
"""


def test_parses_displayed_sources_and_preserves_rates():
    rows = UltimateSourceReferenceFrontierService.parse(_FIXTURE)
    by_id = {row.source_id: row for row in rows}

    assert by_id["exhilarating_drain"].label == "Exhilarating Drain"
    assert by_id["exhilarating_drain"].displayed_rate == "5/1s"
    assert by_id["light_attack"].displayed_rate == "3/1s"


def test_classifies_model_route_conflicts_and_search_mutations():
    rows = UltimateSourceReferenceFrontierService.parse(_FIXTURE)
    by_id = {row.source_id: row for row in rows}

    assert by_id["light_attack"].route_status is UltimateSourceRouteStatus.MODELED
    assert by_id["exhilarating_drain"].route_status is UltimateSourceRouteStatus.SEARCH_STATE_MUTATION
    assert by_id["blessing_peak"].route_status is UltimateSourceRouteStatus.EXACT_REVIEW_REQUIRED
    assert by_id["decisive"].route_status is UltimateSourceRouteStatus.SEARCH_STATE_MUTATION


def test_duplicate_source_cards_are_deduplicated_by_semantic_identity():
    rows = UltimateSourceReferenceFrontierService.parse(
        _FIXTURE + '<div data-source="light_attack"></div>'
    )

    assert [row.source_id for row in rows].count("light_attack") == 1
