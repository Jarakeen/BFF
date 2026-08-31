# Phase 4 Resource & Sustain Engine

## Status

- **4A Static resource foundation:** complete
- **4B Action costs:** complete for verified static cost behavior
- **4C Recovery timing:** complete
- **4D Restoration events:** complete foundation
- **4E Deterministic timeline:** complete
- **4F Sustain result:** complete
- **Real saved-build integration / audit:** complete

**Phase 4 exit criteria met on 2026-08-31.**

BFF can now determine whether a saved build sustains a modeled activity sequence using canonical action costs, deterministic recovery ticks, explicit restoration events, and an auditable resource timeline. Unsupported or unverified mechanics remain explicit rather than being silently guessed.

## Authoritative Phase 4 flow

```text
Saved Character / Build
        ↓
Audited static resource state
        ↓
Named action → canonical ability rank
        ↓
Base resource cost + verified build modifiers
        ↓
Deterministic cost events
        ↓
2-second recovery ticks + explicit suppression
        ↓
Timed recovery modifiers
        ↓
Explicit restoration events
        ↓
Single-resource deterministic timeline
        ↓
Sustain result / first failure / remaining margin
```

## 4A Static resource foundation

`StaticResourceState` adapts the already-audited character-sheet calculation into explicit Health, Magicka, and Stamina pools. It does not recalculate character stats or infer timing.

Each primary resource retains:

- maximum resource
- displayed recovery
- canonical resource identity

Ultimate remains outside the primary static resource-pool contract.

## 4B Action-cost closeout

Phase 4 has a canonical per-resource action-cost path:

1. Resolve the exact saved ability rank/morph and `base_cost`.
2. Resolve the resource identity from `base_mechanic`, including compound costs.
3. Resolve eligible static modifiers with source/resource/skill-line scope intact.
4. Apply flat reductions before percentage reductions.
5. Round the final resource charge with nearest-half-up rounding.
6. Keep unsupported cost behavior explicit.

Verified live behavior includes:

- Breton Magicka Mastery: 7% Magicka ability-cost reduction.
- Light Armor Evocation: current live Xbox/U50 observations are canonical only for measured piece counts. Combat Prayer (base 4590) produced 4269 at 0 Light, 4223 at 1 Light, 4131 at 2 Light, and 3764 at 6 Light on the tested Breton configuration. Unmeasured positive Light counts remain unresolved rather than extrapolated.
- Medium Armor Wind Walker: Echoing Vigor (base 2984) was measured at every 0-7 Medium piece count and exactly matches 2% Stamina ability-cost reduction per equipped Medium piece: 2984, 2924, 2865, 2805, 2745, 2686, 2626, 2566.
- CP160 Truly Superb jewelry cost glyphs feed the same modifier path.
- Live Magicka glyph tests verified flat-before-percentage ordering and nearest-half-up final rounding.
- Compound resource costs are resolved independently per resource.

### Deliberate action-cost boundary

Percentage **cost increases** remain represented but are rejected by the final static-cost calculator because their ordering relative to reductions has not been verified by current live evidence. Conditional, escalating, toggled, and combat-state cost behavior must not be guessed into the static path.

## 4C Recovery timing

Canonical in-combat recovery behavior now uses:

- ordinary recovery tick interval: **2.0 seconds**
- no invented tick at time zero
- explicit first-tick phase when needed
- character-sheet displayed recovery as the amount restored on each ordinary tick
- Stamina recovery suppressed while blocking, sprinting, or sneaking at the tick instant
- Health and Magicka unaffected by those ordinary activity flags
- maximum-pool clamping and wasted-recovery accounting

Activity state is evaluated independently at every tick. Exceptional effects that replace ordinary suppression rules remain outside this baseline until explicitly modeled.

### Standing vs temporary recovery modifiers

Standing percentage recovery passives remain upstream in the character-sheet calculation. Example: Warden Flourish is applied to Magicka/Stamina Recovery before the scheduler receives the static pool.

Temporary additive recovery modifiers are resolved at each tick instant. Enlivening Overflow is modeled as:

```text
min(0.5% × Max Magicka, 150)
```

added to Health, Magicka, and Stamina Recovery for its verified active window. The scheduler records base recovery, additive temporary bonus, effective recovery, and whether the tick was suppressed.

## 4D Restoration events

Restoration is a separate event family from ordinary recovery.

Canonical restoration contracts include:

- flat resource restoration events with source/time/resource identity
- maximum clamping and wasted-restore accounting
- heavy-attack restoration calculation from a caller-supplied verified weapon base
- Restoration Staff Cycle of Life as a weapon-specific multiplicative modifier
- Heavy Armor Revitalize as a verified heavy-attack restoration modifier
- Restoration Staff Absorb as a triggered Magicka restoration source
- Warden Nature's Gift as simultaneous Magicka/Stamina triggered restoration events

### Heavy-attack base-value boundary

Historical weapon-specific base restoration constants are **not** promoted automatically into the canonical engine. Restoration Staff live-video validation strongly supports the historical ~3219 base candidate once Cycle of Life is separated from ordinary recovery, but the rounded Xbox HUD is not precise enough to promote that integer as universally verified canonical data.

The heavy-attack contract therefore continues to require an explicit verified base value supplied by the caller. This is deliberate and prevents historical constants from silently becoming current truth.

## 4E Deterministic resource timeline

The Phase 4 timeline evaluates one primary resource pool at a time and combines:

- action cost events
- recovery ticks
- restoration events

Events at the same timestamp use deterministic ordering:

```text
action cost → recovery tick → restoration event
```

The timeline records, for every event:

- before amount
- attempted change
- applied change
- after amount
- cost shortfall
- wasted restoration

When a planned cost exceeds the current pool, the resource floors at zero and the shortfall is recorded. The timeline does not invent negative resource values.

## 4F Sustain result

The sustain interpreter summarizes the deterministic event trace without recalculating combat math.

It exposes:

- whether the modeled activity sustains
- first failure time
- failure source
- shortfall
- resource available immediately before failure
- minimum resource reached
- ending resource / margin
- total attempted cost
- total paid cost
- total restoration applied
- total restoration wasted

This layer is intentionally interpretive only.

## Saved-build integration

Phase 4 now consumes real saved builds rather than only synthetic fixtures.

The integration path resolves:

```text
saved skill name
   ↓
canonical rank / numeric ability ID
   ↓
ability.base_cost + base_mechanic
   ↓
verified build cost modifiers
   ↓
resource timeline event
```

`BuildCalculationContext` supplies the audited static character state and progression. `BuildActionCostModifierResolver` supplies saved-build-specific cost modifiers. Name-to-cost resolution remains a repository concern rather than being embedded in the sustain calculator.

A deterministic saved-bar activity planner exists for integration/audit use. It repeats the five ordinary active-bar skills at a fixed cadence and deliberately excludes the Ultimate slot. It is **not** claimed to be a realistic rotation.

## Real saved-build validation

Phase 4 was validated end-to-end against the saved build:

- Character: **Magrat**
- Build: **DF Healer**
- Class/Race: **Warden / Breton**
- Active bar: **front**
- Resource: **Magicka**
- Audit window: **20 seconds**
- Max Magicka: **31,629**
- displayed Magicka Recovery: **2,533 per recovery tick**

The deterministic audit sequence resolved the saved front-bar skills directly from `data/eso.db` and applied verified build cost behavior.

Resolved per-cast Magicka costs in that audit:

- Budding Seeds: **1,993**
- Race Against Time: **3,100**
- Combat Prayer: **3,764**
- Illustrious Healing: **2,878**
- Energy Orb: **3,100**

Ten ordinary recovery ticks restored **25,330** total Magicka across the 20-second window.

The deliberately aggressive one-cast-per-second audit sequence did **not** sustain:

- starting Magicka: **31,629**
- attempted action cost: **59,340**
- paid action cost: **54,426**
- ordinary recovery applied: **25,330**
- explicit restoration events: **0**
- first failure: **18.0s Combat Prayer**
- resource before failure: **2,295**
- attempted cost: **3,764**
- shortfall: **1,469**

This result validates the pipeline, **not** the realism of the synthetic activity plan. The audit explicitly does not auto-schedule heavy attacks, potion resource events, conditional recovery windows, or triggered restoration procs.

## Explicit Phase 4 boundaries carried forward

The following remain explicit unresolved/deferred behavior rather than hidden assumptions:

- unverified percentage cost-increase ordering
- unmeasured Light Armor Evocation piece counts
- exact current weapon-specific heavy-attack base restoration values where live precision is insufficient
- automatic triggering/scheduling of heavy attacks
- potion resource events and potion effects
- conditional proc activation / cooldown scheduling
- Enlivening Overflow trigger timing from actual overheal events
- Warden Nature's Gift trigger timing from actual Green Balance overheal events
- Restoration Staff Absorb trigger timing from actual block events
- exceptional recovery suppression/remapping rules such as Stormweaver's Cavort
- persisted character-level skill-line ownership in the canonical character catalog
- dynamic or currently unmapped Champion Point effects

These are later real-build/conditional/temporal concerns. They do not invalidate the Phase 4 core resource model.

## Phase 4 exit criteria

Phase 4 required BFF to determine whether a build sustains modeled activity rather than merely displaying recovery numbers.

Exit criteria satisfied:

- canonical primary resource state exists
- canonical named action cost path exists
- verified static cost modifiers are applied deterministically
- ordinary recovery timing and suppression exist
- temporary recovery modifiers are time-aware
- explicit restoration events exist
- deterministic resource timeline exists
- sustain failure/margin interpretation exists
- real saved build traverses the complete pipeline
- unsupported mechanics remain explicit
- full regression suite green at closeout: **1,444 passed**

**Phase 4 closed on 2026-08-31.**
