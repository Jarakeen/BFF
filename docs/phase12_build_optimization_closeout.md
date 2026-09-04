# Phase 12 · Build Optimization Closeout

**Status:** Complete  
**Closeout date:** 2026-09-03  
**Branch:** `phase12`

## Outcome

Phase 12 establishes the authoritative bounded build-optimization path for BFF.

The optimizer now represents candidate builds immutably, evaluates them through existing canonical calculation and capability services, applies hard constraints separately from objective scoring, ranks only candidates that have enough evidence to be rankable, and explains why a selected candidate wins.

This phase deliberately does **not** create a second ESO combat model. Candidate evaluation delegates to the existing build/context, static combat/healing, sustain, capability, encounter-evaluation, and provider-assignment paths.

## Closed scope

The real saved-build closeout path exercises deterministic one-change candidate families for:

- Mundus;
- armor traits;
- armor enchants;
- food / drink.

The Phase 12 candidate/evaluator contracts are reusable for later candidate families, but closeout does not claim exhaustive combinatorial search across every future dimension. Gear sets, mythics, weapons, skills, morphs, ultimates, CP, potions, and broader configuration remain expansion dimensions rather than fabricated coverage.

The healer/DD role boundary remains explicit. A role-mismatch DD audit is diagnostic only and is not treated as a healer recommendation.

## Authoritative candidate contract

`BuildCandidate` / `BuildChange` provide the immutable candidate representation.

A candidate preserves:

- canonical character identity;
- baseline build identity;
- deterministic candidate identity;
- exact changed field path;
- before/after values;
- candidate source;
- evaluability state.

Build serialization was hardened during Phase 12 so cloned candidates do not share mutable armor or skill-bar structures with the baseline build.

## Deterministic scoring and ranking

Candidate comparisons use explicit named objective metrics. There is no hidden generic fallback score.

Constraint state is represented separately from objective delta:

- `PRESERVED`;
- `IMPROVED`;
- `REPAIRED`;
- `WORSENED`;
- `UNSATISFIED`;
- `UNKNOWN`.

`WORSENED`, `UNSATISFIED`, and `UNKNOWN` are blocking states. A hard constraint is therefore a gate, not a point penalty.

A candidate may be preferred because it improves the objective, repairs a failed hard constraint, or both. Unknown evidence cannot win by being treated as zero.

Ranking is deterministic for identical inputs: descending objective delta followed by deterministic candidate identity. A deterministic ID tie-break is not presented as ESO evidence.

## Sustain boundary

Phase 12 reuses the Phase 4 sustain engine rather than embedding resource math in optimizer code.

The optimizer preserves candidate-specific:

- resource pool;
- recovery;
- action cost modifiers;
- resource timeline;
- first shortfall;
- minimum resource;
- ending resource;
- unresolved sustain evidence.

Named sustain actions are resolved once per stable repository/action-plan snapshot and reused without caching candidate resource results.

The saved healer baseline used for closeout fails the modeled 20-second Magicka sustain requirement. Candidates that still fail remain blocked even when their healing comparison score is higher.

## Capability and provider boundaries

`SavedBuildCapabilityService` remains authoritative for resolved build capability identity. Phase 12 does not infer support coverage from optimizer-local heuristics.

For provider-aware evaluation, `BuildCandidateProviderScope`:

1. audits the baseline roster once;
2. substitutes the candidate audit for the optimized build;
3. reuses the other roster-member audits;
4. reruns the existing Phase 10/11 evaluation path;
5. checks whether baseline primary provider duties owned by the optimized character remain preserved.

A candidate cannot win by quietly transferring a required baseline provider responsibility to another roster member.

Unknown provider state blocks ranking.

## Scribing boundary

Configured crafted abilities remain explicit boundaries rather than guessed effects.

A crafted ability must have a complete canonically compatible configured recipe before the capability audit treats it as a resolved boundary. Missing or incompatible recipe semantics remain capability gaps.

Detailed scripted-effect conversion remains deferred rather than invented.

## Real saved-build integration gate

The representative closeout audit used:

- character: **Magrat**;
- saved build: **DF Healer**;
- active bar: **front**;
- sustain resource: **Magicka**;
- sustain duration: **20 seconds**;
- provider encounter: **Oaxiltso**;
- additional real roster build: **Necro Tank**.

The bounded optimizer completed baseline → candidate generation → authoritative scoring → hard-constraint comparison → deterministic ranking → explanation.

### Winning recommendation

**Food: Witchmother's Potent Brew → Ghastly Eye Bowl**

Evidence from the closeout audit:

- baseline healing comparison score: **57820.516**;
- candidate healing comparison score: **59970.656**;
- delta: **+2150.139**;
- Magicka sustain: **repaired**;
- candidate minimum Magicka: **3573**;
- candidate ending Magicka: **6314**;
- capability coverage: **preserved**;
- provider responsibility: **preserved**;
- selected-candidate unresolved evidence: **none**.

The healing value is explicitly a comparison score for modeled heal components, not HPS.

Several foods with larger raw healing deltas remained correctly blocked because they did not satisfy the Magicka sustain requirement. This demonstrates that hard constraints remain gates rather than score penalties.

## Search-space and performance hardening

Phase 12 also hardened repeated candidate evaluation without changing authoritative semantics.

Reusable instance-scoped caches were added for stable repository/service reads and mechanically stable intermediate results, including skill, CP, encounter, gear, race, provisioning, ability-cost, action-cost, capability-component, sustain-action-plan, and gear-only context inputs.

Cache invalidation follows the actual dependency surface. Fresh repository/service instances see a fresh canonical snapshot.

Provisioning candidates are:

- deduplicated only when canonical static effects and normalized tooltip evidence are exactly equivalent;
- classified from resolved canonical effects rather than item-name folklore;
- pruned against a proven failing resource only when they cannot improve either relevant sustain input relative to the baseline food.

In the final real healer audit, provisioning evaluation fell from **121 discovered candidates to 73 evaluated candidates**, while the winner and all hard-constraint conclusions remained unchanged.

The final provider-aware audit completed in **8.90 seconds** on the user-run checkpoint. Runtime measurements are treated as observational checkpoints, not correctness gates.

## Regression evidence

Focused optimizer/performance checkpoint reported by the user:

```text
117 passed in 8.94s
```

The first full-suite closeout run exposed three legacy tests that bypassed `SavedBuildCapabilityService.__init__` with `__new__`, thereby constructing an invalid half-initialized service after instance caches were introduced. The tests were corrected to construct the service through its public initializer with lightweight dependencies; production behavior was not weakened to support invalid construction.

Final full regression checkpoint reported by the user:

```text
2232 passed in 87.58s
```

## Phase 9 / 10 / 11 dependency gate

The selected provider-aware optimization mode depends on the hardened encounter-evaluation/provider path.

At Phase 12 closeout:

- Phase 9 is hardened complete;
- Phase 10 is hardened complete after retrospective canonical-mechanic revalidation;
- Phase 11 is complete;
- the real Phase 12 recommendation reran Phase 11 provider assignments and preserved the optimized character's baseline provider responsibility.

No Phase 12 shortcut bypasses unresolved/conflicting encounter or provider evidence.

## Hardened exit-criteria result

- [x] one authoritative immutable candidate representation exists;
- [x] candidate generation is deterministic for identical inputs;
- [x] objective metrics are explicit and named;
- [x] ESO math remains delegated to authoritative engine services;
- [x] unsupported / unknown consequences remain explicit and cannot win as zero;
- [x] raid coverage and provider responsibilities are preserved or block/degrade the candidate;
- [x] a real saved build completed baseline → candidates → scoring → ranking → explanation;
- [x] winning reasoning reports changed input, expected improvement, sustain/coverage/provider tradeoffs, and unresolved evidence;
- [x] focused optimizer checkpoint is green: **117 passed in 8.94s**;
- [x] full regression checkpoint is green: **2232 passed in 87.58s**;
- [x] required Phase 9/10/11 dependency path is green.

## Final result

**RESULT: PASS**

Phase 12 exit criteria are met on **2026-09-03**.
