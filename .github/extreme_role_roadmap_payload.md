#### Extreme Builds role-complete completion roadmap

Extreme Builds is one shared legal-character optimization engine with role-specific objective packages for **Healer, Tank, and Damage Dealer**. It must not fork into separate competing build engines. All roles reuse the same canonical Character → Build identity, legal class/subclass search, static combat math, runtime/effect evidence, candidate pruning, unresolved-boundary handling, and search-space audit contracts.

Current engineering estimate toward a role-complete Extreme product is approximately **55–60% overall**. Architecture is farther along than exhaustive ESO mechanic/corpus coverage. Percentages below are planning estimates, not phase-closeout claims.

##### E1. Unified runtime snapshot — 🟡 next / advanced

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

##### E2. Complete shared legal-character search — 🟡 partial

The universal candidate generator must eventually cover, search, safely prune, or explicitly block every relevant legal dimension:

- race;
- base class and legal subclass route;
- character progression and class passives;
- attributes;
- Mundus;
- food / drink;
- potion capability and explicit use state;
- armor weights and armor passives;
- gear sets, mythics, monster sets, arena weapons, and proc mechanics;
- armor, jewelry, and weapon traits;
- glyphs / enchantments;
- front/back weapon configuration and weapon passives;
- active skills, morphs, ultimates, and standing/slotted effects;
- Champion Points;
- Class Mastery where legally available;
- exact event/runtime state required by the selected objective.

The existing Extreme catalog already provides the legal class/subclass structural universe, independent bars, active-bar/either-bar scope, reviewed passive families, memoization, and structural pruning. Remaining work is primarily exhaustive dimension integration and mechanic coverage rather than a replacement combinatorial engine.

##### E3. Mechanic-coverage audit — 🟡 continuous requirement

For every candidate mechanic, Extreme must preserve one of four states:

```text
SUPPORTED
CONDITIONAL + PROVABLE
UNRESOLVED
UNSUPPORTED
```

Unknown mechanics never silently become zero. Exhaustive audits must cover class/racial/armor/weapon passives, sets and procs, mythics, arena weapons, skills/morphs/ultimates, CP, Mundus, consumables, traits/enchants, and Class Mastery. Inventory coverage is not mechanic coverage.

##### Healer objective package

**H1. MOST Actual Heal — ~80% engineering estimate.** This is the most mature role objective. Existing coverage includes legal heal discovery, HEAL-only component math, mixed damage/heal exclusion, Critical Healing and cap behavior, Healing Done and ability-family modifiers, conditional/passive modifiers, low-health scenarios, Major Mending, named buffs, potion/skill source discovery, triggered skills, gear procs, runtime conditions, self-or-ally targeting, ordered runtime history, and exact expiration. Remaining work is unified snapshot orchestration plus exhaustive race/attributes/gear/CP/traits/glyphs/weapon/skill/mechanic search and denominator proof.

**H2. MOST Emergency Heal — ~70%.** Reuse H1 with explicit low-health and emergency-state assumptions. Complete the same exhaustive character/mechanic dimensions before claiming a global maximum.

**H3. MOST Sustained Healer — ~30–35%.** Requires rotations, HoTs, burst healing, resources, cooldowns, proc windows, recipient/target-count policy, overheal interpretation, and fight duration. This depends materially on Phase 13 Rotation Engine and later Phase 14 Combat Simulation rather than static snapshot optimization alone.

**H4. MOST Raid-Support Healer — ~50%.** Multi-objective search across healing adequacy, buff/debuff coverage and uptime, provider workload, sustain, and survivability. Reuse Phase 11/12.5 provider evidence rather than inventing a healer-specific support score.

##### Tank objective package

**T1. MOST Raw Physical Resistance — ~65%.** Finish exhaustive race, attributes, armor, traits, enchants, Mundus, sets, skills/passives, CP, temporary buffs, and active-bar state. Keep raw stat maximum separate from effective mitigation/cap interpretation.

**T2. MOST Raw Spell Resistance — ~60%.** Reuse T1 architecture with spell-resistance-specific modifier coverage.

**T3. MOST Health — ~55%.** Exhaustively search race, attributes, food, enchants, gear, CP, passives, and temporary Max Health effects.

**T4. MOST Blocky — ~40%.** Treat largest block mitigation, lowest block cost, and longest sustainable block as distinct objectives. Model block mitigation, block cost, stamina state, recovery constraints, weapon legality, CP, sets, passives, and runtime buffs without collapsing them into one arbitrary tank score.

**T5. MOST Survivable Tank — ~25–30%.** Combine incoming-damage sequence, resistance/mitigation, block, shields, self-healing, health, recovery, and sustain. A true survivability maximum depends on Phase 14 temporal combat simulation.

**T6. MOST Support Tank — ~45%.** Optimize raid buffs/debuffs and provider coverage subject to tank legality, sustain, survivability, recipient reach, and uptime. Encounter-specific conclusions belong later to Phase 15.

##### Damage Dealer objective package

**D1. MOST Single Hit — ~55%.** DD snapshot counterpart to MOST Actual Heal. Search the complete legal character plus target state, buffs/debuffs, proc state, resistance/penetration, and exact damage-event semantics to find the largest legal single damage event.

**D2. MOST Critical Hit — ~50%.** Find the largest legally crittable event without multiplying by critical chance. Preserve crit eligibility and target Critical Resistance semantics.

**D3. MOST Execute Hit — ~40%.** Add explicit target-health state, execute scaling, execute passives/skills, target debuffs, and runtime conditions.

**D4. MOST AoE Event — ~35%.** Keep largest hit to one target separate from aggregate damage across an explicit target count. Never silently convert multi-target aggregation into a single-target objective.

**D5. MOST Bash Damage — 🟡 existing novelty lane.** Fold existing MOST Bashy infrastructure into the shared DD/tank objective framework rather than maintaining a separate build engine. Outstanding bash-channel and dual-bar One Hand + Shield legality/mechanic gaps remain explicit blockers.

**D6. MOST Sustained DPS — ~25–30%.** Requires build + deterministic rotation + DoT/proc/cooldown/resource/execute state + simulation duration. This is intentionally downstream of the snapshot Extreme core and depends on Phases 13–14.

##### E4. Search-space proof — 🔴 required before “global maximum”

Every definitive Extreme result must report the legal search denominator and disposition of candidates. At minimum expose counts for class routes, races, attribute configurations, Mundus choices, gear combinations discovered/pruned, CP configurations, skills, unsupported mechanics, and unresolved mechanics. The solver must demonstrate that every relevant legal category was searched, safely pruned, or explicitly unresolved before the UI may label a result a **global maximum**. Otherwise the result remains a **best reviewed lower bound**.

##### E5. Search-performance engineering — 🟡 partial

Continue objective-aware dominance pruning, safe upper-bound pruning, memoization, equivalent-state deduplication, branch-and-bound, and staged candidate expansion. Existing Extreme catalog memoization/structural pruning is the foundation; exhaustive gear/CP/skill search must not become a blind Cartesian product.

##### E6. Real-build validation — 🔴 required closeout gate

Validate at least one real saved character/build for each role through baseline → Extreme search → winning build → explanation → unresolved audit → comparison:

- Healer: **Magrat → DF Healer** is the primary real validation path;
- Tank: use a real canonical saved tank build;
- Damage Dealer: use a real canonical saved DD build.

Synthetic fixtures remain necessary but cannot satisfy the real-integration gate by themselves.

##### E7. Role-complete Extreme product surface — 🔴 planned

The final Extreme UI should select **role**, **objective**, **scenario**, target/runtime assumptions, and reviewed-vs-exhaustive search depth, then show the complete winning build, exact objective result, why it won, runtime/buff proof, search coverage, candidates eliminated, unresolved mechanics, and proof/confidence status. No unexplained maximum number may be presented as authoritative.

##### Cross-role constrained optimization

After single-objective role packages are trustworthy, add constrained multi-objective searches rather than arbitrary universal scores. Examples:

- healer: maximize healing subject to required support effects, minimum sustain, and survivability;
- tank: maximize survivability subject to taunt/support obligations and minimum sustain;
- DD: maximize damage subject to sustain, assigned raid support, and mechanic compliance.

These constrained builds are the bridge from laboratory Extreme objectives to raid-usable recommendations and ultimately Phase 15 encounter-aware optimization.

##### Planned completion order from current state

```text
1. Unified runtime snapshot orchestration
2. Finish Healer single-event snapshot objectives
3. Generalize exact-event optimizer to DD single-hit / crit / execute
4. Finish Tank static/snapshot objectives
5. Complete shared race / attributes / gear / CP / traits / glyphs / weapon search
6. Run exhaustive mechanic-corpus and search-space denominator audits
7. Validate one real saved build per role
8. Close snapshot Extreme Engine
9. Use Phase 13 rotations for sustained role objectives
10. Use Phase 14 simulation for sustained DPS / healing / survivability
11. Use Phase 15 encounter context for raid-usable Extreme recommendations
```

Planning snapshot from 2026-09-09:

| Extreme area | Approximate engineering progress |
| --- | ---: |
| Shared legal class/subclass architecture | 90% |
| Static character calculation infrastructure | 90% |
| Runtime/proc architecture | 85% |
| Unified runtime snapshot orchestration | 70% |
| Whole-character exhaustive candidate dimensions | 55% |
| Mechanic corpus coverage | 50% |
| Search-space proof / exhaustive audit | 30% |
| Healer snapshot Extreme | 80% |
| Tank snapshot Extreme | 55% |
| DD snapshot Extreme | 50% |
| Sustained/temporal Extreme | 25–30% |
| Encounter-aware Extreme | 20% |
| **Role-complete Extreme product** | **55–60%** |

These estimates track engineering readiness only. They do not supersede the roadmap completion standard, corpus audits, real-integration gates, or regression requirements above.
