from services.encounter_requirement_evaluation import (
    EncounterRequirementEvaluator,
    RequirementSemantics,
)
from services.encounter_service import EncounterRequirement
from services.phase11_provider_requirement_audit import Phase11ProviderRequirementAudit


class _EncounterService:
    def __init__(self, rows: dict[str, tuple[EncounterRequirement, ...]]) -> None:
        self._rows = rows

    def encounter_ids(self) -> tuple[str, ...]:
        return tuple(self._rows)

    def requirements(self, encounter_id: str) -> tuple[EncounterRequirement, ...]:
        return self._rows[encounter_id]


def _requirement(requirement_type: str, suffix: str = "1") -> EncounterRequirement:
    return EncounterRequirement(
        requirement_id=f"mechanic-{suffix}:requirement:{requirement_type}",
        encounter_id="encounter-1",
        mechanic_id=f"mechanic-{suffix}",
        mechanic_name=f"Mechanic {suffix}",
        requirement_type=requirement_type,
        target_count=None,
        interpretation_status="structured",
    )


def test_audit_does_not_promote_generic_compliance_to_provider_requirement():
    service = _EncounterService(
        {
            "encounter-1": (
                _requirement("movement", "1"),
                _requirement("cleanse", "2"),
                _requirement("interrupt", "3"),
            )
        }
    )

    result = Phase11ProviderRequirementAudit(service).audit()

    assert result.encounter_count == 1
    assert result.requirement_count == 3
    assert result.provider_requirement_count == 0
    assert result.compliance_requirement_count == 3
    assert result.unknown_requirement_count == 0
    assert result.real_provider_validation_ready is False


def test_audit_counts_only_explicit_provider_semantics_as_validation_ready():
    service = _EncounterService(
        {"encounter-1": (_requirement("major_force"),)}
    )
    evaluator = EncounterRequirementEvaluator(
        service,
        requirement_semantics={
            "major_force": RequirementSemantics.PROVIDER_CAPABILITY,
        },
    )

    result = Phase11ProviderRequirementAudit(service, evaluator).audit()

    assert result.provider_requirement_ids == (
        "mechanic-1:requirement:major_force",
    )
    assert result.provider_requirement_count == 1
    assert result.real_provider_validation_ready is True


def test_audit_preserves_unmapped_requirement_semantics_as_unknown():
    service = _EncounterService(
        {"encounter-1": (_requirement("source_specific_capability"),)}
    )

    result = Phase11ProviderRequirementAudit(service).audit()

    assert result.provider_requirement_count == 0
    assert result.compliance_requirement_count == 0
    assert result.unknown_requirement_ids == (
        "mechanic-1:requirement:source_specific_capability",
    )
    assert result.real_provider_validation_ready is False
