import json

from services.comp_builder_build_candidates import CompBuildCandidate
from services.comp_builder_provider_evidence import CompBuilderProviderEvidenceService


class _UnusedCapabilityService:
    def audit_build(self, _build):
        raise AssertionError("label mapping test must not audit builds")


def _reference_candidate(*, complete_build: bool) -> CompBuildCandidate:
    return CompBuildCandidate(
        candidate_id="template:healer-template",
        name="Reference Healer",
        source_kind="reference_template",
        source_name="Test Catalog",
        source_url="https://example.invalid/template",
        eso_class="Warden",
        role="Healer",
        gear_sets=("Spell Power Cure",),
        skills=("Combat Prayer",),
        mundus="The Ritual",
        complete_build=complete_build,
        unresolved=() if complete_build else ("back bar unresolved",),
        score=100.0,
        score_reasons=("test fixture",),
    )


def _write_template_catalog(tmp_path, *, complete_build: bool) -> None:
    payload = {
        "schema_version": 1,
        "catalog_version": "test-v1",
        "game_update": "U51",
        "templates": [
            {
                "template_id": "healer-template",
                "name": "Reference Healer",
                "source_name": "Test Catalog",
                "source_url": "https://example.invalid/template",
                "retrieved_at": "2026-09-05T00:00:00Z",
                "base_score": 1,
                "slot_scores": {},
                "goal_scores": {},
                "complete_build": complete_build,
                "unresolved": [] if complete_build else ["back bar unresolved"],
                "build": {
                    "Name": "Reference Healer",
                    "BuildName": "Reference Healer",
                    "EsoClass": "Warden",
                    "Role": "Healer",
                },
            }
        ],
    }
    (tmp_path / "team_prescription_templates.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_provider_requirement_mapping_enforces_only_proven_profile_rows(tmp_path) -> None:
    service = CompBuilderProviderEvidenceService(
        tmp_path,
        capability_service=_UnusedCapabilityService(),
    )

    result = service.resolve_requirement_labels(
        (
            "War Horn",
            "Major Courage",
            "Minor Brittle",
            "Minor Maim",
            "Major Slayer",
            "Crusher",
        )
    )

    assert result.provider_ids == (
        "force",
        "major_courage",
        "minor_brittle",
        "minor_maim",
        "major_slayer",
    )
    assert result.unresolved == (
        "provider requirement has no proven canonical capability mapping yet: Crusher",
    )


def test_unknown_provider_requirement_stays_unresolved_instead_of_being_guessed(tmp_path) -> None:
    service = CompBuilderProviderEvidenceService(
        tmp_path,
        capability_service=_UnusedCapabilityService(),
    )

    result = service.resolve_requirement_labels(("Some Future Buff",))

    assert result.provider_ids == ()
    assert result.unresolved == (
        "provider requirement is not in the canonical raid coverage profile: Some Future Buff",
    )


def test_complete_reference_template_can_use_canonical_provider_audit(tmp_path) -> None:
    _write_template_catalog(tmp_path, complete_build=True)
    service = CompBuilderProviderEvidenceService(
        tmp_path,
        capability_service=_UnusedCapabilityService(),
    )
    audited_builds = []

    def _provider_ids_for_build(build):
        audited_builds.append(build)
        return ("major_courage",)

    service.provider_ids_for_build = _provider_ids_for_build

    result = service.provider_ids_for_candidate(
        _reference_candidate(complete_build=True)
    )

    assert result == ("major_courage",)
    assert len(audited_builds) == 1
    assert audited_builds[0].EsoClass == "Warden"
    assert audited_builds[0].Role == "Healer"


def test_partial_reference_template_never_receives_provider_credit(tmp_path) -> None:
    _write_template_catalog(tmp_path, complete_build=False)
    service = CompBuilderProviderEvidenceService(
        tmp_path,
        capability_service=_UnusedCapabilityService(),
    )

    def _must_not_audit(_build):
        raise AssertionError("partial reference template must not be audited as complete")

    service.provider_ids_for_build = _must_not_audit

    assert service.provider_ids_for_candidate(
        _reference_candidate(complete_build=False)
    ) == ()
