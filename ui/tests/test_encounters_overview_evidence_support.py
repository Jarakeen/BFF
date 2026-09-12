from types import SimpleNamespace

from ui.encounters_evidence_guide_support import _render_overview_evidence


class _LabelStub:
    def __init__(self):
        self.text = ""

    def setText(self, value):
        self.text = value


def _page():
    return SimpleNamespace(
        encounter_overview_summary=_LabelStub(),
        encounter_overview_evidence=_LabelStub(),
        encounter_overview_timeline=_LabelStub(),
        encounter_overview_mechanics=_LabelStub(),
        encounter_overview_callouts=_LabelStub(),
        encounter_overview_roles=_LabelStub(),
    )


def test_overview_projects_reviewed_encounter_intelligence_without_packet_aliases():
    page = _page()
    projection = SimpleNamespace(
        evidence_rows=27,
        brief=("At 80%, 50%, 20%: boss is untargetable and raid damage continues.",),
        role_impact=(
            "Tanks — Acid Reflux targets the taunt target.",
            "Healers — Reviewed boss downtime still has active raid damage.",
        ),
        strategy=(
            SimpleNamespace(mechanic="Acid Reflux", mitigation="Keep the cone away from the group."),
            SimpleNamespace(mechanic="Replication", mitigation="Swap targets as clones split."),
        ),
        callouts=("Acid Reflux: face away.", "Replication: swap targets."),
    )
    timeline = (
        ("80%", "Replication", "Main guardian creates a medium clone."),
        ("50%", "Replication", "Main guardian creates another medium clone."),
    )

    _render_overview_evidence(
        page,
        "Reef Guardian",
        timeline,
        projection,
        timeline_source="reviewed evidence fallback",
    )

    assert "Reef Guardian" in page.encounter_overview_summary.text
    assert "boss is untargetable and raid damage continues" in page.encounter_overview_summary.text
    assert "27 underlying evidence row(s)" in page.encounter_overview_summary.text
    assert "Tanks — Acid Reflux" in page.encounter_overview_roles.text
    assert "Healers — Reviewed boss downtime" in page.encounter_overview_roles.text
    assert "80%  Replication" in page.encounter_overview_timeline.text
    assert "Acid Reflux: Keep the cone away" in page.encounter_overview_mechanics.text
    assert "Replication: swap targets." in page.encounter_overview_callouts.text
    assert "Candidate review-packet aliases remain hidden" in page.encounter_overview_evidence.text


def test_overview_states_missing_reviewed_material_explicitly():
    page = _page()
    projection = SimpleNamespace(evidence_rows=0, strategy=(), callouts=())

    _render_overview_evidence(
        page,
        "Unreviewed Encounter",
        (),
        projection,
        timeline_source="reviewed evidence fallback",
    )

    assert "No canonical phase timeline" in page.encounter_overview_timeline.text
    assert "No reviewed mechanic strategy" in page.encounter_overview_mechanics.text
    assert "No reviewed raid-lead callouts" in page.encounter_overview_callouts.text
    assert "No reviewed role-specific implications" in page.encounter_overview_roles.text
