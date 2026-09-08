from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.canonical_knowledge_gap import (
    CanonicalKnowledgeDomain,
    CanonicalKnowledgeGap,
)
from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage


def _gap() -> CanonicalKnowledgeGap:
    return CanonicalKnowledgeGap(
        domain=CanonicalKnowledgeDomain.ASSIGNMENT_POLICY,
        key="xalvakka_hm:major_brittle",
        summary="Owned encounter assignment has no explicit rotation policy disposition: major_brittle",
        needed_evidence=(
            "Provide exact effect identity, source skill, bar if required, minimum uptime, "
            "and provenance, or a verified non-effect disposition."
        ),
        consumers=("comp_maker", "rotation_maker", "optimizer"),
        source_context="encounter=xalvakka_hm; provider_member=char-a",
    )


def test_evidence_bundle_research_filter_exposes_cross_system_consumers() -> None:
    from ui.rotation_canonical_evidence_bundle_support import RotationCanonicalEvidenceBundle

    gap = _gap()
    bundle = RotationCanonicalEvidenceBundle(
        encounter_id="xalvakka_hm",
        encounter_name="Xalvakka",
        demands=(),
        options=(),
        requirements=(),
        passives=(),
        evaluator_resolver=object(),
        scorecard_resolver=object(),
        resource=object(),
        maximum_amount=32000,
        trigger_fraction=0.35,
        restoration_resolver=object(),
        knowledge_gaps=(gap,),
    )

    assert bundle.ready is False
    assert bundle.research_for("comp_maker") == (gap,)
    assert bundle.research_for("rotation_maker") == (gap,)
    assert bundle.research_for("optimizer") == (gap,)
    assert bundle.research_for("unrelated") == ()


def test_dashboard_refuses_knowledge_gap_and_explains_what_to_bring_back() -> None:
    page = SimpleNamespace()
    bundle = SimpleNamespace(
        ready=False,
        unresolved=(),
        knowledge_gaps=(_gap(),),
    )

    with pytest.raises(ValueError) as exc_info:
        CanonicalRotationDashboardPage.evaluate_canonical_evidence_bundle(page, bundle)

    message = str(exc_info.value)
    assert "not ready" in message
    assert "major_brittle" in message
    assert "Bring back:" in message
    assert "source skill" in message


def test_knowledge_gap_normalizes_duplicate_consumer_labels() -> None:
    gap = CanonicalKnowledgeGap(
        domain=CanonicalKnowledgeDomain.RESOURCE_RECOVERY,
        key="restoration_staff:heavy_restore",
        summary="Verified heavy restoration amount is unavailable.",
        needed_evidence="Provide completed heavy base restore and applicable modifiers.",
        consumers=("Rotation_Maker", "rotation_maker", "optimizer"),
        source_context="weapon=restoration_staff",
    )

    assert gap.consumers == ("rotation_maker", "optimizer")
