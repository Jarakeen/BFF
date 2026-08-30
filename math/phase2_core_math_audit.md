# Phase 2 Core Math Audit

Status: active audit on `phase3`

Purpose: verify the shared character-stat foundation used by DD, healer, and tank auditing without replacing working Phase 2 code merely because a downstream tooltip disagrees.

## Rules for this audit

1. Treat `ESO_MATH.md` as a reference library, not an ordered recipe.
2. Derive calculation order from stat dependencies, not document order.
3. Preserve existing calculators when their arithmetic is sound; fix missing or misclassified inputs separately.
4. Permanent/unconditional passives that ESO reflects on the character sheet belong in the static/resolved character state. This includes applicable class, weapon, armor, Undaunted, racial, guild/skill-line, and passive Champion Point effects.
5. A passive/effect moves to the conditional combat-state layer only when its text or mechanic requires a trigger/state such as `after a Heavy Attack`, `while in combat`, `while an ability is active`, `when you deal/take damage`, `while below/above X%`, or another explicit activation condition.
6. Do not promote conditional/proc effects into static character state without an explicit active-state model.
7. Every applied source must remain traceable by source label.
8. Every unsupported or unverified source must remain explicit as unresolved rather than silently omitted.
9. Phase 3 skill math consumes the output of this layer; it must not repair bad Phase 2 character stats with skill-specific fudge factors.

## Canonical dependency layers

### Layer A: Primary character resources

Start from the verified max-level baseline currently used by the project:

- Max Health: 16,000
- Max Magicka: 12,000
- Max Stamina: 12,000

Then resolve the inputs that actually affect each resource, including attributes, gear glyphs, static set bonuses, food/drink, race, Mundus where applicable, Champion Points, and all owned/equipped unconditional passive effects that ESO reflects on the sheet.

Current implementation: `minmax/base_character_state.py`

Audit status: **structure retained**. The main remaining risk is missing input sources, not the base arithmetic container.

### Layer B: Shared derived sheet stats

Current implementation: `minmax/derived_stats.py` and `minmax/core_stat_calculator.py`

The generic input buckets are useful and should be retained:

- flat contributions
- percent contributions
- additive-after-percent contributions

However, bucket placement must be verified per ESO stat. The existence of a generic bucket is not evidence that a mechanic belongs there.

Unconditional passive effects from class, weapon, armor, Undaunted, racial, guild/skill-line, and Champion systems belong here when they alter a sheet stat. Conditional versions of those effects do not.

## Stat-by-stat audit matrix

| Stat | Current foundation | Shared role importance | Current audit state | Main remaining work |
|---|---|---|---|---|
| Max Health | 16,000 base + traced inputs | Tank / all | KEEP | audit all unconditional passive %/flat sources |
| Max Magicka | 12,000 base + traced inputs | Healer / mag DD / all | KEEP | audit all unconditional passive %/flat sources |
| Max Stamina | 12,000 base + traced inputs | Stam DD / tank / all | KEEP | audit all unconditional passive %/flat sources |
| Health Recovery | base + traced inputs | Tank / PvP | KEEP WITH AUDIT | verify current base and all unconditional sources |
| Magicka Recovery | base + traced inputs | Healer / mag DD / tank | KEEP WITH AUDIT | unconditional passive sources first; conditional recovery effects stay combat-state |
| Stamina Recovery | base + traced inputs | Stam DD / tank | KEEP WITH AUDIT | unconditional passive sources first; conditional recovery effects stay combat-state |
| Weapon Damage | level baseline + flat/%/post-% buckets | DD / healer / tank utility | FORMULA CONTAINER KEEP | resolver coverage is incomplete |
| Spell Damage | level baseline + flat/%/post-% buckets | DD / healer | FORMULA CONTAINER KEEP | resolver coverage is incomplete |
| Weapon Critical | 10% base ratio + traced additions | DD | KEEP WITH AUDIT | verify rating conversion and unconditional passive sources |
| Spell Critical | 10% base ratio + traced additions | DD / healer | KEEP WITH AUDIT | verify rating conversion and unconditional passive sources |
| Critical Damage | 50% base + additive ratio sources | DD | KEEP WITH AUDIT | verify cap handling and current unconditional/conditional sources |
| Critical Healing | not first-class | Healer | MISSING | add separate stat/model; do not reuse Critical Damage blindly |
| Physical Penetration | zero-base traced stat | DD | KEEP WITH AUDIT | verify all armor/class/CP/set/passive sources |
| Spell Penetration | zero-base traced stat | DD | KEEP WITH AUDIT | verify all armor/class/CP/set/passive sources |
| Physical Resistance | armor/static sources | Tank / all | KEEP WITH AUDIT | verify unconditional passives, buffs, caps/mitigation layer |
| Spell Resistance | armor/static sources | Tank / all | KEEP WITH AUDIT | verify unconditional passives, buffs, caps/mitigation layer |
| Critical Resistance | project has base + item sources | PvP | SEPARATE FROM PVE CORE REVIEW | verify current-era baseline before expanding |
| Healing Done | ratio sources | Healer / tank self-heal | KEEP CONTAINER, AUDIT SEMANTICS | include unconditional passive sheet sources; separate conditional tooltip/actual visibility later |
| Healing Taken | ratio sources | Tank / support | KEEP WITH AUDIT | include unconditional passive sheet sources; keep triggered effects conditional |
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

## Passive classification policy

The build/stat layer should mirror what ESO presents as the character's standing stats.

### Apply to static/resolved character state

When owned/equipped and otherwise applicable, include passive effects that are always on and reflected by the character sheet, including:

- class passives
- weapon passives
- armor passives
- Undaunted passives
- racial passives
- guild/skill-line passives
- non-slottable Champion Point passives
- slotted-skill passive bonuses that are continuously active merely because the relevant skill is slotted

These must still be rank-aware, bar-aware, equipment-aware, and source-labeled where the passive requires a weapon type, armor composition, skill line, or slotted ability.

### Keep in conditional combat state

Do not bake an effect into standing sheet stats when it requires a transient trigger/state, for example:

- after a Heavy Attack
- after casting a specific skill/type
- while in combat
- while an ability/buff is active
- while blocking/sprinting/sneaking
- when dealing/taking damage
- when applying a status effect
- when under/over a resource or Health threshold
- proc/on-hit/on-kill/on-critical conditions

Those effects need an explicit active-state/uptime model and must remain unresolved at the static layer if that state is not supplied.

## High-priority accuracy gaps

### 1. Unconditional passive coverage

There is not yet one general resolver feeding all standing passive effects into the shared stat pipeline. This can make a mathematically correct derived-stat formula produce an incomplete character sheet value.

Required coverage includes class, weapon, armor, Undaunted, racial, guild/skill-line, and passive CP systems.

Required behavior:

- class/skill-line specific where necessary
- rank-aware
- equipment-aware
- armor-weight/count-aware
- bar-aware when the passive depends on equipped weapon or slotted abilities
- source-labeled
- automatically applied when unconditional and the build proves its prerequisites
- routed to conditional combat state when an activation trigger is present

### 2. Slotted-skill passive effects

The saved build knows front/back skill bars, but the shared stat pipeline does not yet generally derive passive sheet-stat effects from those skills. Continuously active `while slotted` effects belong in standing character state; triggered/temporary effects do not.

### 3. Active named buffs

Selected equipment/food/potion is not the same thing as an active timed buff. Major/Minor buffs and proc buffs need an explicit combat-state layer rather than being silently assumed static unless the build has an unconditional source that makes the named buff permanently active.

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
4. Unit-test unconditional passive prerequisites (class, weapon, armor composition, Undaunted, slotted skill where relevant).
5. Unit-test that explicitly conditional passives are not applied without active state.
6. Trace a saved real build.
7. Compare against an in-game character-sheet observation where available.
8. Do not adjust unrelated formulas to force a match.
9. If a mismatch remains, identify the unresolved contributor before changing arithmetic.

## Immediate implementation sequence

1. Expand diagnostics to show all shared primary/derived stats. **Done on phase3.**
2. Inventory passive-skill data and classify unconditional versus triggered effects.
3. Build shared unconditional-passive resolution for class, weapon, armor, Undaunted, racial/guild lines, and slotted-skill standing bonuses.
4. Route triggered passive effects to an explicit conditional combat-state model rather than the standing sheet.
5. Reconcile W/SD source coverage.
6. Reconcile crit/penetration source coverage for DD auditing.
7. Add verified tank block-cost/block-mitigation models.
8. Add Critical Healing as a separate audited stat.
9. Only then use skill-tooltip fixtures as downstream validation of the completed character state.
