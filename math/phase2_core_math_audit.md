# Phase 2 Core Math Audit

Status: active audit on `phase3`

Purpose: verify the shared character-stat foundation used by DD, healer, and tank auditing without replacing working Phase 2 code merely because a downstream tooltip disagrees.

## Rules for this audit

1. Treat `ESO_MATH.md` as a reference library, not an ordered recipe.
2. Derive calculation order from stat dependencies, not document order.
3. Preserve existing calculators when their arithmetic is sound; fix missing or misclassified inputs separately.
4. Do not promote conditional/proc effects into static character state without an explicit active-state model.
5. Every applied source must remain traceable by source label.
6. Every unsupported or unverified source must remain explicit as unresolved rather than silently omitted.
7. Phase 3 skill math consumes the output of this layer; it must not repair bad Phase 2 character stats with skill-specific fudge factors.

## Canonical dependency layers

### Layer A: Primary character resources

Start from the verified max-level baseline currently used by the project:

- Max Health: 16,000
- Max Magicka: 12,000
- Max Stamina: 12,000

Then resolve the inputs that actually affect each resource, including attributes, gear glyphs, static set bonuses, food/drink, race, Mundus where applicable, Champion Points, and verified skill/class percentage modifiers.

Current implementation: `minmax/base_character_state.py`

Audit status: **structure retained**. The main remaining risk is missing input sources, not the base arithmetic container.

### Layer B: Shared derived sheet stats

Current implementation: `minmax/derived_stats.py` and `minmax/core_stat_calculator.py`

The generic input buckets are useful and should be retained:

- flat contributions
- percent contributions
- additive-after-percent contributions

However, bucket placement must be verified per ESO stat. The existence of a generic bucket is not evidence that a mechanic belongs there.

## Stat-by-stat audit matrix

| Stat | Current foundation | Shared role importance | Current audit state | Main remaining work |
|---|---|---|---|---|
| Max Health | 16,000 base + traced inputs | Tank / all | KEEP | audit class/skill/passive % sources |
| Max Magicka | 12,000 base + traced inputs | Healer / mag DD / all | KEEP | audit class/skill/passive % sources |
| Max Stamina | 12,000 base + traced inputs | Stam DD / tank / all | KEEP | audit class/skill/passive % sources |
| Health Recovery | base + traced inputs | Tank / PvP | KEEP WITH AUDIT | verify current base and all static sources |
| Magicka Recovery | base + traced inputs | Healer / mag DD / tank | KEEP WITH AUDIT | class/passive and conditional recovery sources |
| Stamina Recovery | base + traced inputs | Stam DD / tank | KEEP WITH AUDIT | class/passive and conditional recovery sources |
| Weapon Damage | level baseline + flat/%/post-% buckets | DD / healer / tank utility | FORMULA CONTAINER KEEP | resolver coverage is incomplete |
| Spell Damage | level baseline + flat/%/post-% buckets | DD / healer | FORMULA CONTAINER KEEP | resolver coverage is incomplete |
| Weapon Critical | 10% base ratio + traced additions | DD | KEEP WITH AUDIT | verify rating conversion and current passive sources |
| Spell Critical | 10% base ratio + traced additions | DD / healer | KEEP WITH AUDIT | verify rating conversion and current passive sources |
| Critical Damage | 50% base + additive ratio sources | DD | KEEP WITH AUDIT | verify cap handling and current sources |
| Critical Healing | not first-class | Healer | MISSING | add separate stat/model; do not reuse Critical Damage blindly |
| Physical Penetration | zero-base traced stat | DD | KEEP WITH AUDIT | verify all armor/class/CP/set sources |
| Spell Penetration | zero-base traced stat | DD | KEEP WITH AUDIT | verify all armor/class/CP/set sources |
| Physical Resistance | armor/static sources | Tank / all | KEEP WITH AUDIT | verify passives, buffs, caps/mitigation layer |
| Spell Resistance | armor/static sources | Tank / all | KEEP WITH AUDIT | verify passives, buffs, caps/mitigation layer |
| Critical Resistance | project has base + item sources | PvP | SEPARATE FROM PVE CORE REVIEW | verify current-era baseline before expanding |
| Healing Done | ratio sources | Healer / tank self-heal | KEEP CONTAINER, AUDIT SEMANTICS | separate source-specific tooltip/actual visibility later |
| Healing Taken | ratio sources | Tank / support | KEEP WITH AUDIT | verify all static/conditional sources |
| Block Cost | not first-class | Tank | MISSING | add after verified current formula/source model |
| Block Mitigation | not first-class | Tank | MISSING | add after verified current formula/source model |
| Damage Done categories | not a single sheet stat | DD | PHASE 3/COMBAT LAYER | model direct/DoT/AoE/single-target/type-specific/slayer separately |
| Damage Taken categories | not a single sheet stat | Tank/support | COMBAT LAYER | keep separate from armor resistance |

## Confirmed structural strengths

### Resource provenance

`ResourceInputs` already separates item, set, food, Mundus, Champion Point, skill/race/other contributions and preserves named item/set traces. Keep this.

### Weapon/Spell Damage arithmetic container

`DerivedStatCalculator` already supports the required structure:

`(level baseline + flat sources) * (1 + summed percent sources) + post-percent sources`

Do not replace this merely to solve one observed skill tooltip. The immediate problem is incomplete source resolution into those buckets.

### Gear/source resolution

`GearStatInputResolver`, `BaseItemStatResolver`, and `StaticBuildInputResolver` already provide a useful separation between:

- set/glyph/trait inputs
- deterministic CP160 item bases/traits
- Mundus, CP, food, and other static build choices

Retain that separation.

## High-priority accuracy gaps

### 1. Class passives

There is not yet one general class-passive resolver feeding the shared stat pipeline. This can make a mathematically correct derived-stat formula produce an incomplete character sheet value.

Required behavior:

- class-specific
- rank-aware where necessary
- condition-aware
- source-labeled
- bar-aware when the passive depends on slotted abilities
- unresolved when activation requirements cannot be proven from the build

### 2. Slotted-skill passive effects

The saved build knows front/back skill bars, but the shared stat pipeline does not yet generally derive passive sheet-stat effects from those skills. This is required for reliable DD, healer, and tank auditing.

### 3. Active named buffs

Selected equipment/food/potion is not the same thing as an active timed buff. Major/Minor buffs and proc buffs need an explicit combat-state layer rather than being silently assumed static.

Example: a selected Spell Power potion may imply which buffs can be produced, but it does not prove they are active at an arbitrary snapshot.

### 4. Tank-specific foundational stats

Block cost and block mitigation need first-class audited models before tank optimization can be considered complete. Resistance alone is not a tank model.

### 5. Critical Healing

Critical Healing must be represented separately from ordinary Healing Done and from damage Critical Damage unless current-game evidence proves a shared source/mechanic.

## Constants/rules requiring re-verification before modification

Do not change these solely from old reference prose:

- dual-wield off-hand weapon-power ratio (`0.177` currently in `item_base_stats.py`)
- current critical rating conversion
- current Critical Resistance baseline
- armor/weapon trait values where the DB or current-game source can supersede a hardcoded constant
- Mundus/Divines displayed rounding versus internal value
- role-specific caps and mitigation formulas

## Current implementation policy for Champion Points

Temporary profile behavior on `phase3`: all non-slottable Champion Point passives are treated as maxed and included in calculations, with the UI explicitly noting `(all Champion Passives included)`.

This is temporary. It is not a universal player assumption. The future build editor should expose passive Champion Point ownership/levels so team members with incomplete passive trees can be modeled accurately.

## Required validation strategy

For each foundational stat:

1. Unit-test naked/base state.
2. Unit-test one source per bucket.
3. Unit-test combined stacking/order.
4. Trace a saved real build.
5. Compare against an in-game character-sheet observation where available.
6. Do not adjust unrelated formulas to force a match.
7. If a mismatch remains, identify the unresolved contributor before changing arithmetic.

## Immediate implementation sequence

1. Expand diagnostics to show all shared primary/derived stats. **Done on phase3.**
2. Audit class-passive data availability and build a source resolver without hardcoding per-build values.
3. Audit slotted-skill passive data availability and bar conditions.
4. Reconcile W/SD source coverage.
5. Reconcile crit/penetration source coverage for DD auditing.
6. Add verified tank block-cost/block-mitigation models.
7. Add Critical Healing as a separate audited stat.
8. Only then use skill-tooltip fixtures as downstream validation of the completed character state.
