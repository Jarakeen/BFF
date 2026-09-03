from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService
from services.paths import RESEARCH
from services.phase11_provider_requirement_audit import Phase11ProviderRequirementAudit


def main() -> int:
    service = EncounterService(EncounterRepository.from_data_root(RESEARCH))
    audit = Phase11ProviderRequirementAudit(service).audit()

    print("=" * 76)
    print(" PHASE 11 PROVIDER REQUIREMENT READINESS AUDIT - READ ONLY")
    print("=" * 76)
    print(f"encounters:              {audit.encounter_count}")
    print(f"requirements:            {audit.requirement_count}")
    print(f"provider requirements:   {audit.provider_requirement_count}")
    print(f"compliance requirements: {audit.compliance_requirement_count}")
    print(f"unknown requirements:    {audit.unknown_requirement_count}")

    if audit.provider_requirement_ids:
        print()
        print("=== PROVIDER REQUIREMENTS ===")
        for requirement_id in audit.provider_requirement_ids:
            print(f"  - {requirement_id}")

    if audit.unknown_requirement_ids:
        print()
        print("=== UNKNOWN REQUIREMENT SEMANTICS ===")
        for requirement_id in audit.unknown_requirement_ids:
            print(f"  - {requirement_id}")

    print()
    if audit.real_provider_validation_ready:
        print("RESULT: READY - canonical provider requirements exist for Phase 11 validation")
        return 0

    print(
        "RESULT: BLOCKED - no canonical provider-capability requirement is currently "
        "available for real Phase 11 assignment validation"
    )
    print(
        "Generic movement, positioning, cleanse, and interrupt requirements remain "
        "execution/compliance demands and are not promoted to provider requirements."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
