from __future__ import annotations

"""Profile Phase 14 Team Optimization startup without mutating user data.

Run from the FoundryDock repository root:

    python tools/profile_team_optimization_startup.py --repeat 5

Optionally include the first real plan-scoped analysis cost:

    python tools/profile_team_optimization_startup.py --repeat 5 --plan-id <raid-plan-id>

The profiler constructs/disposes the page only. When --plan-id is supplied it reads the
saved Raid Plan and saved builds through normal read paths; it never saves either.
"""

import argparse
import statistics
import sys
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication

from engine.config import get_data_dir
from services.raid_plan_repository import RaidPlanRepository
from ui.application_team_optimization_bootstrap import (
    bootstrap_team_optimization_extensions,
)
from ui.optimization_page import OptimizationPage
from ui.raid_engine_dashboard_support import install as install_raid_engine_dashboard


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=5)
    parser.add_argument("--plan-id", default="")
    return parser.parse_args()


def _load_plan(plan_id: str):
    if not plan_id:
        return None
    repo = RaidPlanRepository(get_data_dir() / "raid_plans.json")
    plan = repo.get(plan_id)
    if plan is None:
        raise SystemExit(f"Raid Plan not found: {plan_id}")
    return plan


def main() -> int:
    args = _parse_args()
    if args.repeat < 1:
        raise SystemExit("--repeat must be at least 1")

    app = QApplication.instance() or QApplication([])
    bootstrap_team_optimization_extensions()
    install_raid_engine_dashboard()
    plan = _load_plan(args.plan_id.strip())

    construction_ms: list[float] = []
    scope_ms: list[float] = []

    for _ in range(args.repeat):
        started = perf_counter()
        page = OptimizationPage()
        construction_ms.append((perf_counter() - started) * 1000.0)

        profile = dict(getattr(page, "_optimizer_startup_profile", {}) or {})
        if profile.get("legacy_constructor_invoked") is not False:
            raise RuntimeError("Phase 14 startup unexpectedly invoked legacy Optimization")

        if plan is not None:
            scope_started = perf_counter()
            page.set_raid_plan_adviser_scope(plan)
            scope_ms.append((perf_counter() - scope_started) * 1000.0)

        page.deleteLater()
        app.processEvents()

    print("TEAM OPTIMIZATION STARTUP PROFILE")
    print(f"repeat={args.repeat}")
    print("legacy_constructor_invoked=False")
    print("saved_build_resolution_at_startup=False")
    print(f"construction_ms_min={min(construction_ms):.3f}")
    print(f"construction_ms_median={statistics.median(construction_ms):.3f}")
    print(f"construction_ms_max={max(construction_ms):.3f}")
    if scope_ms:
        print(f"plan_scope_ms_min={min(scope_ms):.3f}")
        print(f"plan_scope_ms_median={statistics.median(scope_ms):.3f}")
        print(f"plan_scope_ms_max={max(scope_ms):.3f}")
    else:
        print("plan_scope=not_measured")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
