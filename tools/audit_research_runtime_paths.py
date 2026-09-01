from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit_research_data_paths import legacy_references

NON_BLOCKING_PREFIXES = (
    "docs/",
    "old_pages/",
    "minmax/tests/",
    "services/test_",
    "tests/",
)

NON_BLOCKING_PATHS = {
    "CLAUDE.md",
    "packaging/build_test.ps1",
    "tools/apply_research_path_migration.py",
    "tools/audit_research_data_paths.py",
    "tools/audit_research_runtime_paths.py",
}


def is_blocking(path: str) -> bool:
    if path in NON_BLOCKING_PATHS:
        return False
    return not any(path.startswith(prefix) for prefix in NON_BLOCKING_PREFIXES)


def main() -> int:
    matches = legacy_references()
    blocking = [match for match in matches if is_blocking(match[0])]
    informational = [match for match in matches if not is_blocking(match[0])]

    print("=" * 78)
    print(" RESEARCH DATA RUNTIME PATH AUDIT - READ ONLY")
    print("=" * 78)
    print()
    print("=== BLOCKING LEGACY PATH REFERENCES ===")
    if not blocking:
        print("  (none)")
    else:
        for path, line_number, line in blocking:
            print(f"  {path}:{line_number}: {line}")

    print()
    print(f"blocking reference count: {len(blocking)}")
    print(f"informational reference count: {len(informational)}")
    print("No files or database rows were changed.")
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
