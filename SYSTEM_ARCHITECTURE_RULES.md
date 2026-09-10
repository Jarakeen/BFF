# BFF System Architecture Rules

These rules apply across the whole BFF / FoundryDock system. They are not feature-specific notes.

## One system, shared mechanics

Extreme Builder, Comp Maker, Team Optimization, Rotation Builder, Performance / Raid Review, roster and provider assignment, encounter logic, and future role-specific tools are different consumers of the same canonical ESO mechanics and runtime-state model.

Do not create parallel versions of the same ESO rule merely because a feature has a different UI or optimization objective.

The intended direction is:

`canonical ESO data -> shared mechanics / runtime contracts -> role- and feature-specific evaluation -> explanation / UI`

Role-specific logic belongs above shared mechanics. Healer, tank, and damage-dealer objectives may interpret or rank the same canonical state differently, but they should not fork the underlying truth.

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

## Fail closed

Unknown, unsupported, or mechanically ambiguous ESO behavior stays explicit. No BFF engine may turn missing evidence into a favorable optimization assumption.

This rule is system-wide.

## Practical development rule

Be exhaustive about mechanical coverage, but do not spend development time polishing already-sufficient infrastructure merely because it can be made prettier. Prioritize closing real coverage gaps, proving shared contracts, and moving executable behavior toward completion.
