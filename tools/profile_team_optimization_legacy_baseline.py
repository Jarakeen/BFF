from __future__ import annotations

"""Profile the retired Team Optimization constructor chain from another source tree.

This intentionally avoids the full application bootstrap because older detached snapshots
may depend on unrelated later Roster APIs. It installs only the Optimization wrappers that
formed the hidden constructor chain before the Phase 14 lazy-startup cleanup.

Example:
    python tools/profile_team_optimization_legacy_baseline.py \
        --source-root C:\\Dev\\BFF\\FoundryDock-opt-before --repeat 5
"""

import argparse
import statistics
import sys
from pathlib import Path
from time import perf_counter


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--repeat", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = _args()
    root = Path(args.source_root).resolve()
    if not (root / "ui" / "optimization_page.py").is_file():
        raise SystemExit(f"Optimization source tree not found: {root}")
    if args.repeat < 1:
        raise SystemExit("--repeat must be at least 1")

    sys.path.insert(0, str(root))

    from PySide6.QtWidgets import QApplication

    # Import from the requested old tree only after it owns sys.path[0].
    from ui.team_optimization_role_cleanup import install as install_role_cleanup
    from ui.team_optimization_canonical_analysis_support import (
        install as install_canonical_analysis,
    )
    from ui.team_provider_workload_support import install as install_provider_workload
    from ui.raid_plan_optimizer_adviser_support import install as install_raid_plan_adviser
    from ui.team_optimization_phase14_shell_support import install as install_phase14_shell
    from ui.optimization_page import OptimizationPage

    app = QApplication.instance() or QApplication([])

    # Recreate the Optimization-specific part of the old wrapper order without
    # bootstrapping Comp/Roster modules that are irrelevant to this measurement.
    install_role_cleanup()
    install_canonical_analysis()
    install_provider_workload()
    install_raid_plan_adviser()
    install_phase14_shell()

    samples: list[float] = []
    for _ in range(args.repeat):
        started = perf_counter()
        page = OptimizationPage()
        samples.append((perf_counter() - started) * 1000.0)
        page.deleteLater()
        app.processEvents()

    print("LEGACY TEAM OPTIMIZATION CONSTRUCTOR PROFILE")
    print(f"source_root={root}")
    print(f"repeat={args.repeat}")
    print(f"construction_ms_min={min(samples):.3f}")
    print(f"construction_ms_median={statistics.median(samples):.3f}")
    print(f"construction_ms_max={max(samples):.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
