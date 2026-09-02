# Phase 8 Combat-State Architecture Inventory

**Branch baseline:** `phase8` at `6c6844f98563a40801e0c91014dcb3f30f4de90e`  
**Purpose:** establish the smallest canonical snapshot boundary before adding Phase 8 code.

## Existing state models

| Model | Responsibility | Phase 8 disposition |
|---|---|---|
| `CombatState` | Explicit static-calculation inputs: `in_combat`, canonicalized `active_buffs`, and game-update semantics. | Reuse as the static math adapter; do not add mutable/timeline facts to it. |
| `IncomingAttackState` | Properties of the incoming hit currently being evaluated. | Keep caller-provided; it is not persistent player state. |
| `LightAttackState` | Resolved staff-light-attack formula inputs. | Formula-local input, not a general combat snapshot. |
| `StaticResourceState` / `StaticResourcePool` | Build-derived maximum Health/Magicka/Stamina and displayed recovery. | Reuse unchanged as immutable capacity/baseline data. |
| Phase 4 resource timelines and restoration events | Ordered resource costs, recovery, restoration, cap/waste, and failure diagnostics. | Reuse as the authoritative temporal resource arithmetic; snapshot projects current values only. |
| `PotionUseEvent` / `PotionActiveWindow` | Explicit potion use and its currently active named grants at caller-supplied elapsed time. | Reuse as one source of active buffs; do not duplicate potion duration/cadence logic. |
| `RuntimeEvent` | Deterministic event identity, time, target, and same-time sequence. | Reuse as runtime history input. |
| `RuntimeEffectState` | Last activation timestamps, globally and per target, for one `EffectVariant`. | Reuse for cooldown truth. |
| `RuntimeEffectRuntimeState` | Per-`EffectVariant` activation history plus retained active windows. | Reuse as Phase 7 runtime truth; snapshot must not reimplement transitions. |
| `RuntimeEffectActiveWindow` | One concrete bounded successful activation, using `start <= t < end`. | Reuse for active effects at a snapshot time. |
| Runtime stacking/stream results | Ordered immutable runtime transitions, refresh and stacking outcomes. | Preserve as audit/history; snapshot projects their result, not their implementation. |
| Runtime status adapter | Target-scoped status application/query over the canonical effect runtime state. | Reuse for active statuses; retain explicit unresolved duration when applicable. |
| Component health-threshold records | Static threshold requirements such as target/self health below a percentage. | Reuse as requirements evaluated against caller-supplied current values. |

No general `EncounterState` or positional state model currently exists. This is appropriate: encounter geometry belongs to Phase 9 and must remain an explicit caller input in Phase 8.

## Overlap and boundary decisions

1. `CombatState.active_buffs` and `PotionActiveWindow.active_buff_names` overlap only at the **static-consumer boundary**. Potion windows are evidence/history; `CombatState` is the normalized named-buff input to current static math.
2. `RuntimeEffectRuntimeState.windows` and status queries describe the same Phase 7 runtime facts at different views. Phase 8 must project, not store a second activation/window state machine.
3. `StaticResourceState` is maximum/recovery capability; Phase 4 timelines are resource evolution. A Phase 8 snapshot needs current values, never a second cost/recovery engine.
4. Current health does not yet have a canonical general representation. Existing health references are static thresholds or component-specific scaling drivers, not current player/target truth.

## Smallest canonical snapshot contract

Add a new immutable Phase 8 model in a dedicated module (for example `minmax/combat_state_snapshot.py`) rather than expanding the Phase 3 `CombatState`.

```text
CombatStateSnapshot
  time_seconds
  player: CombatantSnapshot
  targets: tuple[CombatantSnapshot, ...]
  active_effects: tuple[ActiveEffectProjection, ...]
  cooldowns / stacks: projections from Phase 7 state
  combat_state: CombatState                 # normalized named buffs for existing consumers
  unresolved: tuple[str, ...]
```

`CombatantSnapshot` should initially contain only:

- stable explicit identity;
- current Health, Magicka, Stamina, and Ultimate when known;
- optional static resource capacities supplied from `StaticResourceState`;
- derived percentage helpers that return unresolved/absent when a current value or maximum is missing;
- active target-scoped statuses projected from Phase 7 windows.

The snapshot should make execute truth a query over a static `SkillComponentCondition` and an explicit combatant health percentage; it should not encode every ability-specific execute rule as a field.

`ActiveEffectProjection` should retain `EffectVariant.name` as the sole effect identity, source, target, active-window interval, magnitude when known, and whether it can be represented as a named buff/status. It must not derive effect sameness from source, magnitude, bar, or other attributes.

## Explicit caller inputs that remain outside the snapshot

- position, distance, range, line of sight, and encounter geometry;
- eligible/selected targets when a capped effect has more candidates than it can affect;
- incoming attack family for mitigation;
- observed runtime events and deterministic chance rolls;
- resource timeline/action history when current resource values need derivation;
- encounter phase and mechanic state;
- unknown durations, target identity, magnitude, cooldown scope, or health values.

## First implementation slice

Implement only the immutable data contract and pure projection/query functions:

1. validate snapshot time, combatant identities, and non-negative current resources;
2. build a player/target snapshot from explicit current values plus optional `StaticResourceState`;
3. project active Phase 7 windows at `time_seconds`, preserving unknown/unrepresentable effects as explicit unresolved entries;
4. merge known named buffs into the existing `CombatState` adapter without changing its meaning;
5. expose health-percentage and execute-threshold queries with explicit unknown results;
6. add focused tests for window boundaries, target-scoped status projection, duplicate logical-effect identity, missing maxima/current values, and named-buff projection.

Do **not** add action selection, a rotation engine, automatic target choice, encounter geometry, automatic potion/proc scheduling, or a second cooldown/stack transition layer.
