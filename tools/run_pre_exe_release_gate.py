from __future__ import annotations

"""One-command pre-EXE release gate for FoundryDock Phase 14."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COMMANDS = (
    (
        "Persistence hardening tests",
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "services/tests/test_personnel_pydantic_persistence_gate.py",
            "services/tests/test_roster_assignment_context_service.py",
            "services/tests/test_comp_build_persistence_service.py",
            "services/tests/test_roster_player_identity_service.py",
            "services/tests/test_roster_duplicate_player_merge_service.py",
            "services/tests/test_build_profile_service.py",
            "services/tests/test_encounter_raid_map_store.py",
            "services/tests/test_finch_shared_provenance_service.py",
            "services/tests/test_raid_plan_repository.py",
            "services/tests/test_raid_plan_repository_revisions.py",
            "services/tests/test_phase14_planning_workflow_roundtrip.py",
            "minmax/tests/test_build_catalog_service.py",
        ],
    ),
    (
        "Release contract tests",
        [sys.executable, "-m", "pytest", "-q", "packaging/tests/test_release_contract.py"],
    ),
    (
        "Strict release data audit",
        [sys.executable, "tools/audit_release_candidate.py", "--strict-data"],
    ),
    (
        "Saved Build read-only gate",
        [sys.executable, "tools/verify_saved_build_persistence_gate.py", "--expect", "12"],
    ),
    (
        "User-data read-only Pydantic gate",
        [sys.executable, "tools/audit_user_data_persistence_gate.py"],
    ),
)


def main() -> int:
    print("FOUNDRYDOCK PRE-EXE RELEASE GATE")
    print("=" * 72)
    for label, command in COMMANDS:
        print(f"\n[{label}]")
        print(" ".join(command))
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode != 0:
            print(f"\nPRE-EXE RELEASE GATE: FAIL ({label})")
            return result.returncode or 1
    print("\n" + "=" * 72)
    print("PRE-EXE RELEASE GATE: PASS")
    print("Persistence, release classification, and read-only user-data checks are green.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
