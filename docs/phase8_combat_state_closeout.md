# Phase 8 Combat State Closeout

## Result: PASS

Phase 8 provides an immutable, auditable answer to **what is true at a specific instant**.

## Delivered

- snapshot time, explicit player and named-target state;
- current Health/Magicka/Stamina/Ultimate inputs and known Phase 4 capacities;
- health percentages and target-specific execute thresholds;
- active Phase 7 runtime windows projected only when matching canonical `EffectVariant.name` metadata is supplied;
- target-scoped statuses and retained-application counts;
- cooldown/chance eligibility delegated to Phase 7 rather than reimplemented;
- known active self buffs bridged into existing static `CombatState`;
- real saved-build validation: **Magrat → DF Healer**, front bar, capacities **21,700 / 31,109 / 13,096**;
- focused snapshot tests: **8 passed**; full regression checkpoint: **2023 passed**.

## Explicit caller inputs / later phases

Position, range, line of sight, encounter phase, target selection, observed event history, chance rolls, current resource values, and unknown effect metadata/durations remain explicit. Phase 8 does not schedule actions, infer rotations, simulate encounters, or choose targets.

## Invariant

`EffectVariant.name` remains the sole logical effect identity. Unknown window metadata becomes explicit unresolved state; no category, stack meaning, or static modifier is guessed.
