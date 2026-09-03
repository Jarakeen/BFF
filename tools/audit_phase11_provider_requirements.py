from __future__ import annotations

from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.encounter_repository import EncounterRepository
from services.encounter_service import EncounterService
from services.paths import DATA
from services.phase11_provider_requirement_audit import Phase11ProviderRequirementAudit


def main() -> int:
    service = EncounterService(EncounterRepository.from_data_root(DATA))
    audit = Phase11ProviderRequirementAudit(service).audit()

    print("=" * 76)
    print(" PHASE 11 BOSS-CORPUS PROVIDER REQUIREMENT AUDIT - READ ONLY")
    print("=" * 76)
    print(f"encounters:              {audit.encounter_count}")
    print(f"requirements:            {audit.requirement_count}")
    print(f"provider requirements:   {audit.provider_requirement_count}")
    print(f"compliance requirements: {audit.compliance_requirement_count}")
    print(f"unknown requirements:    {audit.unknown_requirement_count}")

    if audit.provider_requirement_ids:
        print()
        print("=== BOSS-DERIVED PROVIDER REQUIREMENTS ===")
        for requirement_id in audit.provider_requirement_ids:
            print(f"  - {requirement_id}")

    if audit.unknown_requirement_ids:
        print()
        print("=== UNKNOWN REQUIREMENT SEMANTICS ===")
        for requirement_id in audit.unknown_requirement_ids:
            print(f"  - {requirement_id}")

    print()
    if audit.real_provider_validation_ready:
        print("RESULT: BOSS PROVIDER ROWS PRESENT - canonical boss requirements include provider capability")
        return 0

    print(
        "RESULT: BOSS PROVIDER ROWS ABSENT - the canonical boss corpus currently "
        "contains compliance requirements only"
    )
    print(
        "This is not a Phase 11 failure: raid-support coverage requirements are an "
        "analysis/strategy layer and are evaluated separately from boss mechanics."
    )
    print(
        "Generic movement, positioning, cleanse, and interrupt requirements remain "
        "execution/compliance demands and are not promoted to provider requirements."
    )
    print("Configured provider validation: python tools\\evaluate_phase11_default_coverage.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
