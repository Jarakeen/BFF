# Flawless Dawnbreaker periodic runtime research

Status: PARKED pending a corpus with materially more Flawless Dawnbreaker observations.

Canonical component: `flawless_dawnbreaker`, coefficient 2.

## Reviewed runtime facts

- Duration: 6.0 seconds.
- Tooltip shape: additional Physical Damage over 6 seconds.

## Current ESO Logs evidence adequacy

The reviewed imported ESO Logs corpus contains only **two** Flawless Dawnbreaker cast observations.

Secondary-effect discovery found multiple nearby repeated-damage candidates inside the reviewed windows, but **zero candidate events were cast-track linked to the Flawless Dawnbreaker casts**.

With only two cast anchors and no exact cast-track-linked periodic candidate, the corpus cannot reliably establish:

- periodic ownership,
- recurrence cadence,
- activation anchor,
- first-tick offset,
- refresh-boundary behavior, or
- magnitude policy.

Timing similarity or nearby repeated damage is not sufficient identity evidence, particularly with this sample size.

## Park decision

Do not promote any numeric ESO Logs candidate or missing executable periodic field for Flawless Dawnbreaker from the current corpus.

Further mining of these same two casts is unlikely to resolve the missing semantics without overfitting incidental nearby damage.

Revisit only when one of the following is available:

1. a corpus containing substantially more Flawless Dawnbreaker casts,
2. exact same-track or otherwise authoritative periodic ownership evidence,
3. controlled observations establishing recurrence/refresh behavior, or
4. authoritative runtime data that directly establishes the missing periodic semantics.

Until then, preserve the reviewed 6-second duration and fail closed for all unresolved executable periodic fields.
