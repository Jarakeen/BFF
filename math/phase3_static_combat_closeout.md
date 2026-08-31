# Phase 3 Static Combat Closeout

Status: **closeout checkpoint on `phase3`**

Purpose: record the verified rules, database coverage, accepted residuals, and deferred boundaries for the Phase 3 Static Combat Rules Engine.

## Governing rule

A mechanic enters the shared combat pipeline only after its formula and activation/application scope are verified.

Required order:

```text
formula
→ activation / applicability verification
→ test
→ eligibility
→ application
→ live-sheet / tooltip / combat validation
```

Correct math takes priority over matching a fixture. No unexplained scale factors are allowed.

---

## Authoritative static damage stage order

```text
raw coefficient/component
→ attacker Damage Done
→ crit eligibility and expected critical damage
→ target Critical Resistance
→ resistance / penetration mitigation
→ target Damage Taken
→ final damage
```

Damage Done and Damage Taken are separate buckets. Protection/Vulnerability are target-side and do not mutate attacker sheet stats. Critical Resistance modifies the crit bonus and does not act as armor resistance.

---

## Skill coefficient rules

### Type 8

Verified formula:

```text
value = (A * MaxStat) + (B * Power) + C
```

`R` from the UESP skill coefficient export is retained as regression-fit metadata and is **not** multiplied into the evaluated game value.

Only the exact UESP empty-slot marker is inactive:

```text
type = -1
A = -1
B = -1
C = -1
R = -1
```

Valid negative coefficient terms are preserved.

The older singular coefficient path was reconciled with the Phase 3 implementation so there is no longer a competing `raw * R` formula.

---

## Critical rules

### Normal skill components

```text
damage → can_crit = True
healing → can_crit = True
shield → can_crit = NULL / not applicable
utility → can_crit = NULL / not applicable
```

Runtime critical observations remain useful as validation/corroboration but are not required to establish ordinary skill damage/healing crit eligibility.

### Proc/set policy foundation

Static eligibility is kept separate from ordinary skill semantics:

```text
offensive-stat-scaled proc → crit eligible
Max-Health-scaled proc → cannot crit
Oblivion damage → cannot crit
escalating/modifier-style proc → cannot crit
flat/unresolved proc → unknown until proven
```

Proc critical eligibility is also separate from the later rule about whether one proc may trigger another proc.

### Critical Resistance

At CP160+ / effective max level:

```text
66 Critical Resistance = 1 percentage point removed from critical-damage bonus
```

The effective critical bonus floors at zero. Critical Resistance cannot make a critical hit weaker than a normal hit.

---

## Damage Done / Damage Taken routing

Damage Done supports distinct categories for:

- generic
- damage type
- Direct Damage
- Damage over Time
- Area of Effect
- Single Target

Applicable categories are combined within the attacker Damage Done bucket.

Damage Taken is applied later as its own target-side bucket. Named Vulnerability and Protection effects route here rather than into attacker stats or armor mitigation.

---

## Block / tank foundation completed during Phase 3

First-class static models now exist for:

- Block Cost
- Block Mitigation
- armor-weight block effects
- Fortress
- Sword and Board
- Defensive Stance
- Sturdy
- Bracing jewelry glyphs
- Tireless Guardian
- Fortification
- Bracing Anchor
- Deflect Bolts as an incoming ranged/projectile damage-family block modifier

Block Cost and Block Mitigation are not treated as generic resistance math.

---

## Named CombatState foundation

Phase 3 can route explicit named active states without pretending selected potions or merely slotted skills are automatically active.

Implemented families include:

- Brutality / Sorcery
- Courage
- Savagery / Prophecy
- Force
- Mending
- Resolve
- Fortitude / Intellect / Endurance
- Toughness
- Berserk
- Protection
- Vulnerability

Standing unconditional effects remain distinct from transient combat-state effects.

---

## Per-coefficient component classification

Canonical key:

```text
skill_rank_id + coefficient_number
```

Stored semantic fields include:

- effect kind
- damage type
- periodicity
- target shape
- crit eligibility
- source / confidence

The classifier is deliberately conservative. It does not infer missing mechanics from ability names, neighboring coefficients, or vague text.

### Current database coverage

```text
Active coefficient rows:       3208
Persisted qualified rows:      2376
Explicit unresolved rows:       824
Missing source fragments:         8
Slot mismatches:                  0
```

The 824 unresolved rows are accepted as explicit gaps rather than guessed values.

Known unresolved families include ambiguous target shape, vague effect-kind fragments, and a small number of missing coefficient fragments. Full resolution is deferred until stronger authoritative evidence exists.

---

## Combat Prayer downstream validation

Combat Prayer was used to validate that the upstream stat/coefficient/modifier architecture can reproduce a real ESO healing tooltip without introducing a skill-specific fudge factor.

Observed tooltip:

```text
9436
```

Closest auditable modeled scenario:

```text
9444.014264
```

Residual:

```text
8.014264 points
≈ 0.085%
```

This residual is accepted for Phase 3. It is small enough to plausibly arise from hidden internal precision, tooltip rounding, exact active state, or saved-build drift. No unexplained correction factor will be added to force an exact historical integer match.

---

## Real-database closeout audit

`tools/audit_phase3_static_damage_pipeline.py` selects one persisted, complete, type-8 damage component from the real `eso.db` and routes it through:

```text
real database coefficient
→ persisted component classification
→ raw coefficient evaluation
→ Major Berserk / Damage Done
→ expected crit
→ target Critical Resistance
→ resistance / penetration mitigation
→ Major Vulnerability / Damage Taken
→ final damage
```

The audit is intentionally a real-database command rather than a normal pytest dependency because `data/eso.db` is a mutable local data artifact.

---

## Deferred beyond Phase 3

The following do **not** block Phase 3 closure:

- exhaustive classification of all 824 unresolved coefficient rows
- full temporal proc/set engine
- proc-to-proc trigger rules in runtime state
- sustain-over-time simulation
- rotation generation
- encounter simulation
- build optimization
- exact integer tooltip reproduction for every skill
- ESO Logs as a canonical static-data dependency
- temporal CombatState with cooldowns/stacks/resources/position

---

## Exit criteria

Phase 3 is complete when all of the following are true:

- [x] one authoritative type-8 coefficient formula
- [x] duplicate `R` multiplier behavior removed
- [x] valid negative coefficient terms preserved
- [x] Damage Done wired to skill/component damage
- [x] Damage Taken wired as a distinct target-side stage
- [x] Critical Resistance implemented and routed
- [x] normal skill damage/healing crit eligibility established
- [x] per-component classification persisted for qualified rows
- [x] unresolved semantic gaps remain explicit
- [x] Block Cost / Block Mitigation first-class models exist
- [x] named combat-state foundation exists
- [x] Combat Prayer downstream validation accepted within ~0.085%
- [ ] real `eso.db` end-to-end closeout audit passes locally
- [ ] final full pytest suite passes after closeout commits

Once the final two checks are green, Phase 3 can be marked complete and development can move to the planned style/UX makeover checkpoint before the next major systems phase.
