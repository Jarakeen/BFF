# Rotation Execute Continuous Amplification Research

## Status

**PARKED — source evidence is insufficient for exact runtime interpolation.**

Threshold-gated execute activation is implemented and production-boundary proven. This note covers the separate execute form represented by canonical consequences such as `AMPLIFIES_DAMAGE` with source wording like `up to N% more damage` below a target-Health threshold.

## What is already canonical

The Phase 6 conditional-consequence model preserves:

- the target-Health threshold condition;
- the consequence type `AMPLIFIES_DAMAGE`;
- the reviewed maximum bonus fraction;
- the source wording that establishes the maximum bonus.

The runtime execute layer already fails closed when this amplification is active because the exact interpolation across target Health is unresolved.

## What is missing

A production formula needs source-backed evidence for the exact relationship between target Health and bonus damage inside the execute range. The current canonical evidence does **not** establish whether the bonus is:

- linear from the threshold to zero Health;
- stepped or piecewise;
- rounded at intermediate stages;
- based on current Health before or after the hit;
- clamped at another hidden boundary; or
- calculated by some other game-specific rule.

Public tooltip wording and the currently reviewed repository evidence establish the maximum bonus but do not, by themselves, define that interpolation law.

## Production rule

Until exact interpolation semantics are source-verified:

1. Above the execute threshold, the ordinary base damage component may resolve normally.
2. When continuous execute amplification is active, canonical damage remains unresolved rather than applying the maximum bonus or inventing a curve.
3. Missing exact runtime Health continues to fail closed.
4. This evidence block does not affect threshold-gated execute activation, which is separately supported.

## Closure requirement

This lane may move from PARKED only when reviewed evidence establishes an exact runtime interpolation formula precise enough to implement deterministic tests at multiple Health fractions, including the threshold boundary and at least one interior point.
