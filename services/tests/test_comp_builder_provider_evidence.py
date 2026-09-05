from services.comp_builder_provider_evidence import CompBuilderProviderEvidenceService


class _UnusedCapabilityService:
    def audit_build(self, _build):
        raise AssertionError("label mapping test must not audit builds")


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
