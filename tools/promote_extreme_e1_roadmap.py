from __future__ import annotations

from pathlib import Path


ROADMAP = Path(__file__).resolve().parents[1] / "MASTER_ROADMAP.md"

OLD_BLOCK = '''##### E1. Unified runtime snapshot — 🟡 next / advanced

Replace fragmented single-source scenario inputs with one deterministic runtime history plus one exact snapshot time:

```text
Runtime History
  ├── potion activations
  ├── cast buffs
  ├── triggered skills
  ├── gear procs
  ├── cooldown history
  ├── deterministic chance rolls
  ├── condition evidence
  ├── stacking / refresh
  └── target applicability
          +
   exact snapshot time
          ↓
      CombatState
```

The lower runtime infrastructure is already strong: named buffs, potion windows, skill prebuffs, triggered skills, gear procs, `SELF_OR_ALLY`, explicit condition evidence, ordered event streams, cooldowns, stacking, and exact active-window boundaries are implemented. The remaining bridge is orchestration so every role asks one authoritative question: **what is provably true for this candidate at time `t`?**
'''

NEW_BLOCK = '''##### E1. Unified runtime snapshot — 🟢 Complete

E1 now replaces fragmented runtime scenario inputs with one deterministic runtime history plus one exact snapshot time:

```text
Runtime History
  ├── potion activations
  ├── cast buffs
  ├── triggered skills
  ├── gear procs
  ├── cooldown history
  ├── deterministic chance rolls
  ├── condition evidence
  ├── stacking / refresh
  ├── bar provenance / transitions
  ├── source-persistence semantics
  ├── explicit condition windows
  └── target applicability
          +
   exact snapshot time
          ↓
      CombatState
```

Closeout on **2026-09-15** proved one role-neutral runtime contract for named buffs, generic timed effects, potion windows, triggered skills, gear procs, `SELF_OR_ALLY`, explicit condition evidence, ordered event streams, cooldowns, stacking, exact active-window boundaries, bar-tagged activation, coherent bar-transition history, and reviewed source-persistence behavior. Restoration-heavy and Sacred Ground runtime windows now enter the production Extreme healer path through the same snapshot instead of parallel healer-only truth.

The closed Weapon Damage and Spell Damage records also expose machine-readable ownership and deterministic runtime witnesses. E1 owns only ordered player runtime history; target Health / Off Balance remain `target_state`, same-build higher resource remains `structural_state`, Font / Calculated Defense remain `class_runtime`, and Sorcerer slot legality remains `active_bar`.

Real integration used the canonical saved **Margrat → DF Healer** build and reported `snapshot_unresolved_count=0`, `e1_real_integration_ready=True`, `e1_healer_runtime_bridge_closed=True`, `e1_power_runtime_bridge_closed=True`, and `e1_closeout_audit_ready=True`. Focused E1 regression: **45 passed in 8.29s**. Full repository regression: **2970 passed in 198.10s**, failures **0**. Detailed closeout: `docs/extreme_e1_unified_runtime_closeout.md`.

The audit also exposed a separate canonical identity discrepancy: the live healer build is currently owned by `Margrat`, while a distinct `Magrat` character exists with zero builds. That issue belongs to Phase 1 / identity cleanup and does not reopen E1.
'''

OLD_PROGRESS = "| Unified runtime snapshot orchestration | 70% |"
NEW_PROGRESS = "| Unified runtime snapshot orchestration | 100% |"


def main() -> int:
    text = ROADMAP.read_text(encoding="utf-8")

    block_count = text.count(OLD_BLOCK)
    if block_count != 1:
        raise SystemExit(
            f"Expected exactly one old E1 roadmap block, found {block_count}; refusing to edit"
        )

    progress_count = text.count(OLD_PROGRESS)
    if progress_count != 1:
        raise SystemExit(
            f"Expected exactly one E1 progress row, found {progress_count}; refusing to edit"
        )

    updated = text.replace(OLD_BLOCK, NEW_BLOCK, 1).replace(
        OLD_PROGRESS,
        NEW_PROGRESS,
        1,
    )
    ROADMAP.write_text(updated, encoding="utf-8")

    print("Promoted Extreme E1 unified runtime snapshot to complete in MASTER_ROADMAP.md")
    print("Updated planning row: Unified runtime snapshot orchestration 70% -> 100%")
    print("No other Extreme role/objective estimates were changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
