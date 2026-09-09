from ui.rotation_dashboard_canonical_page import CanonicalRotationDashboardPage


class _SelectedEvidence:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def build(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class _PageState:
    def __init__(self, *, encounter_id, result) -> None:
        self.encounter_id = encounter_id
        self.rotation_selected_encounter_evidence = _SelectedEvidence(result)

    def selected_encounter_id(self):
        return self.encounter_id


def test_page_resolves_evidence_for_exact_selected_encounter() -> None:
    bundle = object()
    inputs = object()
    page = _PageState(encounter_id="xalvakka_hm", result=bundle)

    result = CanonicalRotationDashboardPage.selected_encounter_evidence_bundle(
        page,
        inputs,  # type: ignore[arg-type]
    )

    assert result is bundle
    assert page.rotation_selected_encounter_evidence.calls == [
        {"encounter_id": "xalvakka_hm", "inputs": inputs}
    ]


def test_page_preserves_missing_selection_for_provider_to_reject() -> None:
    bundle = object()
    inputs = object()
    page = _PageState(encounter_id=None, result=bundle)

    CanonicalRotationDashboardPage.selected_encounter_evidence_bundle(
        page,
        inputs,  # type: ignore[arg-type]
    )

    assert page.rotation_selected_encounter_evidence.calls == [
        {"encounter_id": None, "inputs": inputs}
    ]
