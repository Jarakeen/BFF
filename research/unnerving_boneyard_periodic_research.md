# Unnerving Boneyard periodic runtime research

Status: PARKED pending cleaner or controlled evidence.

Canonical component: `unnerving_boneyard`, coefficient 1.
Periodic ESO Logs evidence ID: `117809`.

## Reviewed runtime facts

- Duration: 10.0 seconds.
- Recurrence cadence: 1.0 second.
- Activation anchor: cast / placement.
- Refresh boundary: `replace_before_recast_tick`.

## Cadence evidence

After collapsing same-track events within 10 ms, 162 cast tracks produced 1,388 normalized occurrences and 1,226 adjacent intervals. Median interval was 0.992 seconds, P10 0.955 seconds, P90 1.060 seconds, and 1,181 of 1,226 intervals (96.3%) fell within 1.0 +/- 0.08 seconds. Long gaps are treated as missing or absent observations rather than evidence of a different recurrence cadence.

## Refresh evidence

Across 141 comparable consecutive cast pairs with old/new `117809` evidence, no old-track event survived to or beyond the first new-track event. One old-track event appeared 1 ms after the new cast and 384 ms before the first new-track event. That boundary-only sample is treated as timestamp/event-order jitter rather than durable old-instance survival.

## First-tick offset: unresolved

Across 162 cast tracks, median first observed damage was 0.3585 seconds after cast, but P90 was 3.3282 seconds and the maximum was 7.3440 seconds. The spread is too wide to promote an exact executable first-tick offset.

## Magnitude policy: unresolved

The generic magnitude/state audit excluded 66 ambiguous mixed-amount occurrence clusters and retained 1,266 comparable unambiguous adjacent occurrence pairs:

- state changed + amount changed: 1,191
- state changed + amount constant: 75
- state same + amount changed: 0
- state same + amount constant: 0

Every comparable pair had reconstructed source or target state changes. There are no stable-state controls, so this corpus cannot distinguish `snapshot_at_cast` from `dynamic_at_tick` without inventing causality.

## Park decision

Do not promote `first_tick_offset_seconds` or `magnitude_policy` from the current imported corpus. Further mining of the same corpus is unlikely to resolve either field. Revisit only with one of the following:

1. controlled testing with stable source/target combat state,
2. a cleaner ESO Logs corpus with stable-state controls and known patch provenance, or
3. authoritative runtime evidence that directly establishes first-tick or magnitude semantics.

Until then, preserve the reviewed partial semantics and fail closed for the unresolved executable fields.
