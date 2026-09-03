# BFF instructions for Claude

## Current development
- Repository: `Jarakeen/BFF`.
- Primary development branch: `phase12`.
- Local project path: `C:\Dev\BFF\FoundryDock`.
- Phase 12 theme: **Build Optimization**.
- Do not create or switch to throwaway branches unless explicitly requested.
- The user explicitly permits direct work on `phase12`.
- Preserve unrelated concurrent work. This is a shared branch and other chats/processes may advance it.
- Recheck the branch head before every write.
- Make small focused commits. Never force-push.
- Preserve the existing architecture and use authoritative services rather than duplicating ESO math.
- The ESO database (`data/eso.db`) is the mechanical source of truth.
- `math/` contains collected ESO math references. Treat them as evidence; do not replace them with guessed formulas.
- `data/eso_info/` is the canonical UESP encounter corpus.
- Do not remove or rewrite raw provenance/source evidence merely to simplify an implementation.

## Working rules
- English only.
- Deterministic/canonical behavior is preferred over heuristic guesses.
- Unsupported or unknown ESO mechanics must stay explicit and fail closed. Do not silently treat unknown as zero, free, or harmless.
- Do not weaken healer/DD/tank role boundaries.
- Do not weaken hard sustain constraints.
- Do not weaken Phase 10/11 capability, coverage, or provider-assignment semantics.
- Do not claim tests pass unless actual pytest output is available.
- Prefer direct implementation over prolonged planning, but do not broaden a focused task into an architecture rewrite without evidence.

## Phase 12 architecture and boundaries
The current pipeline is:

`REAL ESO DATA -> CANONICAL BUILD -> RULES/EFFECT ENGINE -> STATIC COMBAT MATH -> COMBAT STATE -> ENCOUNTER ENGINE -> ROSTER/COVERAGE -> PROVIDER ASSIGNMENT -> BUILD OPTIMIZATION -> ENCOUNTER OPTIMIZATION -> EXPLANATION -> LOG VALIDATION`

Phase 12 is **build optimization**, not rotation generation and not full encounter optimization.

The optimizer may vary bounded build inputs such as gear, sets, mythics, weapons, traits, enchants, skills/morphs/ultimates, Champion Points, Mundus, food, potions, and configuration. It must delegate ESO math to existing authoritative services.

Hard constraints are ranking gates, not point deductions. A higher-scoring candidate does not rank if it fails required sustain, capability, provider responsibility, or other hard constraints.

Unknown consequences block ranking. A candidate may not win because BFF lacked evidence about one of its effects.

## Candidate representation and ranking
Relevant modules include:
- `minmax/build_candidate.py`
- `minmax/build_candidate_comparison.py`
- `minmax/build_candidate_evaluator.py`
- `minmax/build_candidate_provider_scope.py`
- `minmax/build_candidate_capability.py`
- `minmax/build_candidate_plain_language.py`

`BuildCandidate` is immutable.

Constraint statuses include:
- `PRESERVED`
- `IMPROVED`
- `REPAIRED`
- `WORSENED`
- `UNSATISFIED`
- `UNKNOWN`

Blocking statuses include `WORSENED`, `UNSATISFIED`, and `UNKNOWN`.

Ranking is deterministic: objective delta first, then candidate ID as a deterministic tie-break. Candidate-ID order is not ESO evidence.

## Current real saved-build audit
The active healer audit is:

```powershell
python tools\audit_phase12_saved_build_candidates.py `
  --build "DF Healer" `
  --active-bar front `
  --resource magicka `
  --duration 20 `
  --provider-encounter oaxiltso `
  --provider-roster-build "Necro Tank"
```

The real saved build is:
- Character: `Magrat`
- Build: `DF Healer`
- Saved role: `Healer`

Do not reinterpret this healer build as a DD recommendation. A separate DD audit has a diagnostic `--allow-role-mismatch` mode, but that override must never weaken the role boundary.

The healer objective is **modeled healing-component potency**, not actual HPS. Expected critical healing and observed rotation behavior are not implied unless explicitly modeled.

Candidate families currently include:
- Mundus
- one armor-trait change
- one armor-enchant change
- food

Each candidate is deliberately bounded to one changed field.

## Provider responsibility semantics
Phase 11 provider assignments are hard constraints in Phase 12.

If the baseline build is assigned a requirement such as War Horn, a candidate does not get to rank by silently transferring that job to another roster member.

`BuildCandidateProviderScope` audits the baseline roster, substitutes exactly one candidate build for the optimized member, keeps the rest of the roster fixed, and recomputes authoritative provider assignments.

Provider results must remain fail closed:
- missing assignment evidence -> `UNKNOWN`
- unresolved selection/capability/suitability -> `UNKNOWN`
- responsibility lost or reassigned away from the optimized member -> `WORSENED`
- preserved primary duty -> `PRESERVED`

Do not weaken these rules for performance.

## Current performance investigation
The real Phase 12 healer audit evaluates many near-identical candidates. Repeated candidate evaluation has exposed a sequence of static SQLite reads. We have deliberately fixed only observed hot paths and preserved repository/service-lifetime snapshot semantics.

Observed and cached hot paths include:
- skill coefficient entity resolution
- skill coefficient name resolution
- skill component classification
- Champion Point skill relationships
- canonical encounter definitions/mechanics
- potion availability/formula catalog
- skill-line resolution
- passive max-rank resolution
- armor glyph effects
- static Champion Point records
- saved-build capability ability-name -> `ability_id` resolution
- gear-set metadata and gear-set bonuses
- `ability.is_crafted` checks

The latest verified focused cache checkpoint is:

```text
51 passed in 3.70s
```

Do not claim the full suite is green from that checkpoint.

The recent tracebacks have progressed farther through the same food-candidate family each time, which is evidence that the caches are removing real repeated work rather than masking one stuck lookup.

### Important architectural question now
We may be reaching the point where the dominant cost is no longer isolated uncached repository reads, but repeated reconstruction of candidate-independent context.

When analyzing performance, trace one candidate through:

`evaluate_healing_candidate -> candidate context -> sustain -> capability audit -> provider assignments`

For each candidate family, distinguish what truly changes from what can safely be reused:
- Mundus candidate
- one armor-trait candidate
- one armor-enchant candidate
- food candidate

Pay particular attention to `SavedBuildCapabilityService.audit_build()` and `BuildCandidateProviderScope.assignments_for()`.

Do not introduce a broad higher-level cache unless the key precisely prevents:
- stale candidate-dependent stats
- cross-build contamination
- provider responsibility drift
- hidden role mismatch
- unresolved state becoming resolved accidentally

If a higher-level reuse strategy is recommended, define the cache key and invalidation/snapshot semantics explicitly and require focused regression tests before implementation.

## Scribed skills
Preserve the existing scribed-skill boundary.

The capability service currently:
1. resolves the saved skill name to canonical `ability_id`;
2. checks whether the ability is crafted/scribed;
3. if crafted, resolves the configured saved recipe;
4. requires a complete recipe;
5. validates canonical Grimoire/Focus/Signature/Affix compatibility;
6. refuses to invent detailed scripted effect semantics that are not yet modeled.

Do not shortcut a scribed skill into ordinary skill-effect resolution merely for speed.

The recent `is_crafted` hotspot was a repeated static database check, not evidence that scribing semantics themselves should be removed.

## Skills and ability identity
- Base skill and both morphs are distinct selectable abilities.
- `base_ability_id` identifies the skill family.
- `ability_id` identifies the exact selected ability/morph.
- Never use a base skill name in place of a morph name when the selected `ability_id` is a morph.
- Do not hard-code skill or morph names; resolve them from canonical data.
- ESO tooltip/source formatting may contain inline color markup. Do not infer mechanics from formatting artifacts. Preserve canonical/raw evidence when normalizing text.

## Ability scaling
Keep these scaling rules distinct:
- explicit Health scaling
- explicit Magicka scaling
- explicit Stamina scaling
- `HIGHEST_RESOURCE`: highest of Magicka and Stamina
- `HIGHEST_ATTRIBUTE`: highest of Health, Magicka, and Stamina
- fixed/non-attribute scaling

Do not assume every damage or healing ability uses the same scaling rule. Resolve special cases from ability data/reference evidence.

## Champion Points
- Character level and Champion Points are separate progression concepts.
- CP earning/progression speed is out of scope for MinMax; current CP state is what matters.
- Champion Points cap at 3600.
- Only four slottable CP abilities may be active in each of Blue, Red, and Green at once; purchased passive CP remains separate from active slots.
- Do not invent or hard-code unverified CP mechanics.

## Combat environment
- PvE is the current optimization target.
- PvP optimization is out of scope for now, but the data model must not assume all effects are universally active.
- Preserve effects restricted to monsters, players, PvE, PvP, or campaign-specific environments.
- Vengeance/campaign-specific content is an environment restriction, not an ordinary universal effect.

## Testing
- Prefer focused tests for the code being changed, followed by an appropriate wider regression checkpoint.
- Never report a green test result that was not actually run.
- Do not broaden a Phase 12 performance task into unrelated test repair.
- Cache tests must prove semantic behavior, not merely that a dictionary exists.
- For repository/service-lifetime static caches, test both resolved and missing/unresolved results where relevant.
- When returning mutable containers from cached immutable snapshots, return fresh containers so caller mutation cannot corrupt the cache.
- Cache normalization must mirror the underlying SQL semantics exactly. Do not add fuzzy matching or whitespace/case behavior that the authoritative query did not have.

## Search scope
For Phase 12 build-optimization work, start with:
- `minmax/`
- directly relevant `services/`
- `tools/audit_phase12_saved_build_candidates.py`
- relevant `tools/tests/`, `minmax/tests/`, and `services/tests/`
- `models/` where candidate/build identity requires it
- `data/eso.db`
- `math/` only when combat-math evidence is required

Expand to encounter/provider modules when provider scope is active.

Do not perform broad archaeology through backups, raw logs, obsolete UI, or historical branches unless the active code proves a dependency exists or the user explicitly asks for it.
