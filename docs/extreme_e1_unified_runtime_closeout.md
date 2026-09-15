# Extreme E1 · Unified Runtime Snapshot Closeout

**Status:** 🟢 Complete  
**Closeout date:** 2026-09-15  
**Branch:** `phase13.5`

## Scope

E1 replaces fragmented runtime scenario inputs with one deterministic runtime history plus one exact snapshot time. Its responsibility is to answer the role-neutral question:

> What is provably true for this candidate at time `t`?

E1 owns ordered player runtime evidence. It does **not** absorb target-state, structural-state, class-runtime, or active-bar facts that already have separate canonical owners.

## Completed runtime contract

The unified runtime snapshot now carries and/or projects:

- potion activations;
- skill and gear runtime events;
- named buffs and generic timed effects;
- deterministic chance-roll and condition evidence;
- cooldown/runtime state through the shared Phase 7 machinery;
- explicit external group-buff applications with provenance;
- bar-tagged runtime attempts;
- deterministic bar-transition history;
- source-persistence semantics across bar swaps;
- role-neutral explicit condition windows;
- exact snapshot-time evaluation;
- shared projection into canonical `CombatState`.

### Skill / gear parity

Skill and gear runtime projection now share the important temporal semantics required by E1:

- triggered effects can remain named buffs or generic timed effects;
- bar provenance is preserved for activation;
- mixed tagged/untagged skill history fails closed instead of silently normalizing ambiguity;
- explicit `EffectSourcePersistence` rules are honored across swaps;
- complete bar-transition histories must form one deterministic contiguous chain.

### Healer runtime bridge

The production Extreme healer route no longer requires separate healer-only truth for the two reviewed E1 condition windows that remained outside the shared timeline:

- `restoration_staff_heavy_post_completion_window`;
- `sacred_ground_window`.

Those conditions are now supplied by `ExtremeRuntimeSnapshot` and consumed through the snapshot-aware conditional-heal adapter while the existing mechanic-specific services continue to own build/passive/weapon legality.

### Closed power-record bridge

The closed Weapon Damage and Spell Damage records use machine-readable ownership plus deterministic runtime witnesses.

Each objective has **9 reviewed requirements** distributed across explicit canonical owners. E1 owns only the runtime-history subset:

- Armor of Truth activation;
- potion use;
- external Minor Brutality / Minor Sorcery application.

The remaining facts stay outside E1:

- target Health and Off Balance → `target_state`;
- same-build higher resource → `structural_state`;
- Font of Power and Calculated Defense → `class_runtime`;
- six Sorcerer ability legality → `active_bar`.

This boundary is intentional and is part of E1 closeout.

## Real integration proof

Closeout audit:

```powershell
python tools/audit_extreme_e1_unified_runtime_closeout.py `
  --character "Margrat" `
  --build "DF Healer"
```

Observed result:

```text
build_source=canonical_catalog
character='Margrat'
build='DF Healer'
real_saved_build_loaded=True
shared_snapshot_projection_clean=True
healer_condition_windows_active=True
production_uses_snapshot_adapter=True
restoration_heavy_window_consumed=True
sacred_ground_window_consumed=True
snapshot_unresolved_count=0

objective=weapon_damage | requirement_count=9 | witness_closed=True | history_entry_count=3
objective=spell_damage | requirement_count=9 | witness_closed=True | history_entry_count=3
power_runtime_contracts_closed=True

e1_unresolved_count=0
e1_real_integration_ready=True
e1_healer_runtime_bridge_closed=True
e1_power_runtime_bridge_closed=True
e1_closeout_audit_ready=True
```

The audit used the real canonical saved healer build from `data/characters.json`.

## Regression proof

Focused E1 regression gate reported by the user:

```text
45 passed in 8.29s
```

Full repository regression checkpoint reported by the user after the shared runtime changes:

```text
2970 passed in 198.10s (0:03:18)
```

Failures: **0**.

## Unresolved boundary

E1 closeout has **0 unresolved runtime items** in its stated scope.

A separate canonical identity issue was exposed during the real-build audit:

- the live healer build is currently owned by character name `Margrat`;
- a separate canonical `Magrat` character exists with zero builds.

This is **not an E1 runtime defect** and was not modified during closeout. It belongs to canonical Character → Build identity cleanup under Phase 1 / integration work. The E1 audit remained read-only and did not repair or rewrite user state.

## Completion judgment

E1 satisfies the applicable roadmap closeout gates:

- architecture: one shared runtime snapshot path and explicit adjacent ownership boundaries;
- real integration: real saved healer build traversed the production-compatible snapshot path;
- regression: focused and full-suite checkpoints green;
- unresolved boundary: zero E1 runtime unresolved items, with unrelated identity drift explicitly separated;
- downstream safety: Weapon/Spell and healer consumers use the same shared runtime contract without moving foreign-owner facts into E1.

**E1 · Unified Runtime Snapshot is complete as of 2026-09-15.**

This does **not** close the broader Extreme Engine. E2–E7, exhaustive mechanic/search coverage, role-complete validation, sustained objectives, and later simulation/encounter-aware work remain open.