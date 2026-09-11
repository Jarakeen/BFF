# BFF System Architecture Rules

These rules apply across the whole BFF / FoundryDock system. They are not feature-specific notes.

## One system, shared mechanics

Extreme Builder, Comp Maker, Team Optimization, Rotation Builder, Performance / Raid Review, roster and provider assignment, encounter logic, and future role-specific tools are different consumers of the same canonical ESO mechanics and runtime-state model.

Do not create parallel versions of the same ESO rule merely because a feature has a different UI or optimization objective.

The intended direction is:

`canonical ESO data -> shared mechanics / runtime contracts -> role- and feature-specific evaluation -> explanation / UI`

Role-specific logic belongs above shared mechanics. Healer, tank, and damage-dealer objectives may interpret or rank the same canonical state differently, but they should not fork the underlying truth.

## Canonical service registry

Before adding a new service, mechanic implementation, evaluator, resolver, repository, orchestration path, or other architectural responsibility, consult the canonical service registry in `services/service_catalog.py` first.

Use the registry to determine whether a canonical service already owns the responsibility, what inputs and outputs it declares, which dependencies it uses, its lifecycle and authority, and which implementation path is authoritative.

If a canonical service already owns the responsibility, reuse or extend that service rather than creating a parallel implementation.

If a genuinely new architectural responsibility is introduced, add an explicit descriptor to the appropriate registry family so it is discoverable through `SERVICE_CATALOG` and covered by registry-integrity tests.

The registry is discovery metadata, not a dynamic service locator. Application code should continue to use normal typed imports and explicit dependency wiring rather than instantiate or execute implementations by string identity.

Registry consultation is a required architectural discovery step, not an optional convenience. This applies across Extreme Builder, Rotation Builder, Comp Maker, Team Optimization, Performance / Raid Review, encounter/provider systems, and future engines.

## Project knowledge capture

BFF keeps durable project knowledge in shared indexes. Development work should update them when the corresponding kind of knowledge is discovered or created.

### Game mechanics field notes

Whenever development, testing, real-build validation, encounter research, or data reconciliation reveals something mechanically odd or noteworthy, add a short layman's note to `GAME_MECHANICS_FIELD_NOTES.md`.

Use this for ESO behavior that is easy to misunderstand, surprising in practice, version-sensitive, or likely to cause future implementation drift. Capture the practical rule and why it matters. Do not turn ordinary refactoring, architecture cleanup, or routine implementation details into game-mechanics field notes.

### Feature index

Whenever a new user-visible capability or feature is created, add or update its entry in `FEATURES.md` so the application has a durable index of what it can do.

Keep the index descriptive rather than sales-oriented. Internal correctness work, tests, caches, audits, and implementation plumbing do not need feature entries unless they create or materially change a user-visible capability.

### Useful source registry

Whenever research uncovers a useful external source for ESO mechanics, data, logs, calibration, validation, or implementation reference, add it to `useful_resources.md`.

`useful_resources.md` is a working source registry for BFF / FoundryDock research and combat-math validation. It is not merely a link collection. Each source entry should say what the source is useful for and how much confidence should be placed in it before turning information into hardcoded game math. Record version, date, provenance, or limitations when those materially affect interpretation.

### ESO numeric ID registry

Whenever development, log analysis, historical research, data reconciliation, or external-source review identifies a reusable ESO numeric ID, alias, display ID, effect ID, source ability ID, raw ESO Logs ID, or other numeric handle, consult and update `ESO_ID_REFERENCE.md`.

The registry is deliberately evidence-oriented. Stable BFF skill/effect identity remains semantic `lower_snake_case`; numeric ESO IDs are aliases, source handles, or observations and may vary by component, morph, caster, target, event type, bundle, update, or source system.

When adding an ID, preserve its exact role/context, provenance, confidence, and update/year when version-sensitive. If a second numeric ID appears for the same semantic identity, add it rather than silently replacing the earlier observation. Unknown or contradictory IDs stay explicit until reviewed.

The bulk Major/Minor effect alias corpus remains in `docs/major_minor_effect_ids.md`, and detailed raw ESO Logs event-tag research remains in `ESO_LOGS_RAW_TAG_REFERENCE.md`; `ESO_ID_REFERENCE.md` is the shared cross-system index and rule-of-use document.

## Gameplay-practice policy is a separate layer

BFF must distinguish between **what ESO mechanically permits** and **how organized players normally choose to play**.

Canonical mechanics remain the authority for coefficients, costs, durations, targets, triggers, cooldowns, range, combat events, and other engine truth. Gameplay-practice policy may rank, discourage, prefer, require, or explain choices made from those mechanically legal options, but it must not rewrite the underlying mechanic.

The shared gameplay-practice registry lives in `data/gameplay_policy/` with human-readable rationale in `ENDGAME_PLAY_PRACTICES.md` and read-only access through `services/gameplay_policy_service.py`.

The intended decision order is:

`mechanical legality -> normal role/content practice -> encounter/assignment context -> explainable override`

Do not hardcode the same raid convention independently into Extreme Builder, Rotation Builder, Comp Maker, Team Optimization, or Performance. Consumers should query the shared policy layer and apply their own feature-specific objective above it.

Practice rules are contextual defaults, not universal laws. Encounter assignments may override them when the assignment materially changes support access, survival obligations, positioning, role responsibilities, or other conditions that made the default sensible.

## Testing rule: prove reusable contracts

When work in one engine exposes or verifies a reusable mechanic, state, timing rule, legality rule, candidate rule, or optimization invariant, tests should be written with downstream reuse in mind.

In particular, findings from Extreme Builder development should be usable to strengthen Comp Maker and Team Optimization rather than remaining trapped inside Extreme-specific assumptions.

For shared behavior, tests should answer both questions:

1. Does the originating feature behave correctly?
2. Is the underlying contract sufficiently role-neutral and deterministic that another BFF engine can safely consume it?

Prefer shared contract tests plus thin feature-specific tests over duplicating the same mechanic independently in Extreme, Comp Maker, Team Optimization, Rotation, or Performance.

## Runtime state

There must be one authoritative runtime truth for a given evaluation snapshot. Consumers should use canonical projection properties/services rather than maintaining feature-local copies of attempts, buff windows, potion timing, proc state, or encounter state.

Compatibility fields may exist during migrations, but they are bridges, not competing sources of truth.

## Optimization and composition

Extreme optimization is a useful proving ground for exhaustive candidate mechanics, but its findings are part of the larger system.

When an Extreme rule is validated and is not inherently role-specific, prefer making it reusable by:

- Comp Maker candidate construction and legality,
- Team Optimization candidate comparison and constraints,
- Rotation Builder timing/state evaluation,
- provider and coverage evaluation,
- Performance / Raid Review explanation and validation.

Do not copy the result into those engines as hard-coded conclusions. Reuse the canonical mechanic or shared service that produced the result.

## Shared candidate-plan boundary

Comp Maker, Team Optimization, Extreme Builder, and Rotation Builder must converge on one shared candidate-plan boundary rather than exchange feature-local conclusions.

The intended ownership is:

`canonical Character / Build -> Extreme candidate evidence -> Rotation execution evidence -> complete candidate plan -> Comp Maker selection -> Team Optimization improvement`

A **complete candidate plan** represents one exact proposed player/chair configuration and preserves the structured evidence needed by downstream consumers. At minimum, where applicable, that includes canonical character/build identity, exact build changes, candidate/source identity, role and class, gear and skills, runtime assumptions, rotation/execution evidence, support/provider effects, recipient and temporal coverage, sustain/resource evidence, encounter scope, unresolved/unsupported evidence, and provenance/confidence.

The boundary follows these rules:

1. **Upstream engines resolve mechanics once.** Extreme Builder and Rotation Builder may discover or evaluate mechanics through canonical shared services. Their downstream output must retain the evidence/result needed by consumers rather than requiring Comp Maker or Team Optimization to rediscover the mechanic independently.
2. **Comp Maker chooses complete plans.** Comp Maker may compare suitability, composition fit, role/assignment constraints, provider coverage, workload, and encounter relevance, but it must not rebuild Extreme math or Rotation mechanics from display text, heuristics, or duplicate formulas.
3. **Team Optimization improves the same plans.** Optimization starts from the exact selected candidate plan and proposes explicit changes while preserving its canonical identities and evidence boundaries. It may call the authoritative upstream/shared evaluator again for a changed candidate, but it must not substitute a local approximation for an already-owned mechanic.
4. **No prose reconstruction.** Human-readable explanations, score reasons, UI labels, and report text are presentation outputs. Application state must travel through structured typed fields/contracts, not by parsing those strings back into mechanics, gear, skills, assignments, or assumptions.
5. **No silent evidence loss.** Unknown, unsupported, conflicting, partial, or assumption-bound evidence remains attached when a candidate crosses Extreme -> Rotation -> Comp Maker -> Optimization -> Roster. A downstream consumer may reject or defer the candidate, but it may not erase the boundary and treat it as proven.
6. **Identity is stable across the round trip.** Character, baseline Build, candidate Build, team, chair/slot, source/template, rotation plan, and encounter identity must remain distinguishable. Generated-plan persistence may be an implementation detail, but it must not create a second competing user-facing team/build identity.
7. **Results are reusable, not frozen conclusions.** A downstream change to gear, skills, assignment, encounter, runtime assumptions, or rotation invalidates only the evidence that depends on that change. The appropriate authoritative service should recompute that evidence; unaffected canonical evidence should be preserved rather than rediscovered wholesale.
8. **Ranking is consumer-owned; mechanics are not.** Extreme Builder may optimize an Extreme objective, Rotation Builder may optimize execution, Comp Maker may optimize composition, and Team Optimization may optimize the assigned team. Those rankings can differ. They must still consume the same underlying mechanic/evidence truth.

Tests for this boundary should prove that an exact candidate can move between engines without silent identity mutation, evidence loss, favorable UNKNOWN coercion, or mechanics being reconstructed from presentation strings.

## Fail closed

Unknown, unsupported, or mechanically ambiguous ESO behavior stays explicit. No BFF engine may turn missing evidence into a favorable optimization assumption.

This rule is system-wide.

## Practical development rule

Be exhaustive about mechanical coverage, but do not spend development time polishing already-sufficient infrastructure merely because it can be made prettier. Prioritize closing real coverage gaps, proving shared contracts, and moving executable behavior toward completion.