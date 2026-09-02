# Phase 7 · Conditional Effects & Proc Engine Closeout

**Status: 🟢 Complete**  
**Exit criteria met: 2026-09-02**

Phase 7 executes the static component/effect relationships established in Phase 6 over deterministic runtime state without creating a parallel effect system. `EffectVariant` remains authoritative for effect identity and static metadata, and Phase 6 trigger relationships remain authoritative for component trigger identity.

## Completed runtime foundation

Phase 7 now provides one composable runtime path for conditional effects and procs:

```text
RuntimeEvent
   ↓
Trigger / condition eligibility
   ↓
Caller-supplied deterministic proc chance
   ↓
Global or per-target cooldown enforcement
   ↓
Activation state transition
   ↓
Explicit duration window
   ↓
Stacking / refresh resolution
   ↓
Ordered runtime stream state
   ↓
Status / healing / restoration / target consequences
```

### Shared event and trigger contract

- one shared `RuntimeEvent` carrier for Phase 6 component triggers and `EffectVariant.trigger`
- no second trigger taxonomy
- deterministic ordering by event time and sequence
- component trigger relationships remain static evidence; Phase 7 executes them at runtime

### Timing and cadence

- timing metadata remains separate from trigger identity
- explicit periodic scheduling with caller-supplied first occurrence
- caller-active windows, explicit state windows, fixed-count duration windows, and stack-count bounds
- fixed-window spacing remains unresolved unless separately verified
- no duration/count interpolation is used as fabricated cadence evidence

### Proc eligibility and cooldown state

- static `EffectVariant.eligible` short-circuits runtime activation when false
- exact trigger matching
- caller-supplied chance rolls; no hidden RNG
- global and per-target cooldown scopes
- failed activations do not mutate runtime state
- successful activations reject backward-time state changes

### Active windows and stacking

- bounded windows are created only from explicit canonical duration
- exact expiration is inactive (`start <= t < end`)
- `UNIQUE` refresh truncates the prior active window at the new application time
- `STACKS` preserves simultaneous active applications
- `HIGHEST_ONLY` preserves competing source windows while selecting the strongest current contributor when magnitude is available
- missing magnitude or stacking policy remains explicitly unresolved instead of guessed

### Complete ordered effect streams

- ordered attempts preserve event/chance-roll association
- complete immutable effect state is carried from event to event
- cooldown, window, and stacking state remain auditable at every step
- unresolved transitions are retained in the audit trail without discarding later events

### Status effects

- status effects reuse canonical `EffectVariant` data and the shared runtime engine
- explicit target-scoped application
- deterministic active-status queries by target and time
- status application can be recorded even when ongoing duration truth is unresolved

### Triggered resource restoration

Phase 7 reuses the Phase 4 `TriggeredRestorationSource` contract rather than recalculating resource amounts.

Verified runtime examples include:

- Restoration Staff: Absorb → 600 Magicka, 0.25-second cooldown
- Warden: Nature's Gift → 250 Magicka + 250 Stamina, 1-second cooldown

Phase 7 determines when the source fires; Phase 4 remains authoritative for resource identity and restore amount.

### Triggered healing

- minimal `TriggeredHealingEvent` contract added for runtime consequence emission
- Phase 7 handles trigger, target, optional cooldown, and timestamp
- healing magnitude remains caller-resolved by canonical component/healing math
- dynamic healing formulas are not flattened into hard-coded runtime values

### Runtime target selection and target counts

- caller supplies the already-eligible target set after range/position/encounter logic
- `EffectVariant.target_count` is enforced as a cap, not interpreted as a target-selection algorithm
- if eligible targets fit within the cap, all are selected deterministically
- if candidates exceed the cap, explicit target selection is required
- explicit selections must be eligible and cannot exceed the canonical cap

## Phase 6 boundary closure

Final Phase 7 closeout audit against the real `data/eso.db` corpus:

- Phase 7 boundary rows: **24**
- need trigger resolution: **0**
- runtime-review rows: **0**
- timing unresolved: **0**

Timing bound kinds:

- caller active window: **12**
- stack count: **4**
- explicit state window: **4**
- fixed count duration: **4**

All current Phase 7 boundary rows therefore have an explicit supported runtime classification and timing representation.

## Verified closeout capability gate

The closeout gate confirmed all required runtime contracts are present:

- shared runtime event contract
- component timing and state binding
- effect trigger eligibility
- deterministic proc chance
- global and target cooldowns
- active duration windows
- stacking and refresh
- ordered effect streams
- status-effect runtime state
- triggered resource restoration
- triggered healing
- target-count and explicit selection

## Regression evidence

User-run Phase 7 closeout checkpoint on **2026-09-02**:

- **105 passed in 48.20s**
- `python tools\check_phase7_closeout.py`
- **RESULT: PASS**

The closeout result is based on the real local `data/eso.db`, not a synthetic-only fixture.

## Explicit boundaries moving forward

Phase 7 intentionally does not become a giant combat simulator. The following remain later-phase responsibilities or explicit caller inputs:

- full current-player/current-target CombatState snapshots
- health percentages and execute truth at arbitrary instants
- positional/range eligibility and encounter geometry
- automatic choice among multiple eligible targets when ESO targeting rules are not canonically represented
- rotation/action scheduling
- encounter phase state
- broad proc-set/enchantment source ingestion where canonical static metadata is still absent
- unresolved status-duration/chance source data where ESO evidence is not authoritative
- arbitrary natural-language condition parsing
- general combat simulation and Monte Carlo modeling

These are not Phase 7 failures. Phase 7 supplies the deterministic conditional runtime contracts that Phase 8 Combat State and later rotation/simulation layers can consume.

## Exit criteria

BFF can calculate deterministic or explicitly probabilistic conditional effect behavior over time without treating procs, conditional buffs, status effects, triggered healing, or runtime restores as permanent sheet stats.

**Phase 7 exit criteria met on 2026-09-02.**
