# Scalding Rune periodic runtime research

Status: PARKED pending cleaner stable-state magnitude evidence.

Canonical component: `scalding_rune`, coefficient 2.
Periodic ESO Logs evidence ID: `40468`.
Trigger ESO Logs evidence ID: `40469`.

## Reviewed runtime facts

- Duration: 22.0 seconds.
- Recurrence cadence: 2.0 seconds.
- Activation anchor: trigger.
- First periodic tick offset: 2.0 seconds after trigger.
- Refresh boundary: `replace_before_recast_tick`.

## Magnitude policy: unresolved

The generic magnitude/state audit retained 697 comparable unambiguous adjacent occurrence pairs. Every comparable pair had reconstructed source or target state changes:

- state changed + amount changed: 578
- state changed + amount constant: 119
- state same + amount changed: 0
- state same + amount constant: 0

The follow-up single-factor audit found no clean one-state amount-changing controls. The reviewed amount-changing transitions were multi-state, so no individual state change could be isolated as a trustworthy magnitude driver.

The multistate-signature review likewise found no repeated or reversible signatures capable of separating `snapshot_at_cast` from `dynamic_at_tick` behavior.

## Park decision

Do not promote `magnitude_policy` from the current imported corpus. More mining of the same entangled state transitions is unlikely to resolve the field without cleaner controls.

Revisit only with one of the following:

1. controlled testing with stable source/target combat state,
2. a cleaner ESO Logs corpus that contains stable-state adjacent ticks or repeated single-factor transitions, or
3. authoritative runtime evidence that directly establishes whether periodic magnitude is snapshotted or evaluated at each tick.

Until then, preserve the reviewed timing/refresh semantics and fail closed for magnitude policy.
