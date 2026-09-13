# Skeletal Archer periodic runtime research

Status: PARKED pending a corpus with explicit pet-to-owner linkage.

Canonical component: `skeletal_archer`, coefficient 1.
Strong observational ESO Logs candidate: `122774`.

## Reviewed runtime facts

- Duration: 20.0 seconds.
- Recurrence cadence: 2.0 seconds.
- Successive-hit multiplier: 1.15.
- Runtime source classification: pet-owned.

## Candidate evidence

Pet-aware ESO Logs discovery identified `122774` as the dominant friendly non-player candidate inside reviewed Skeletal Archer windows:

- observed in 233 of 238 reviewed cast windows,
- 1,784 candidate events in the original discovery pass,
- 82 friendly non-player source actors in that discovery,
- 1,800 intervals matching the reviewed 2-second cadence,
- median first observed offset approximately 2.023 seconds after the player cast.

The candidate is therefore retained as strong observational evidence, not canonical ownership proof.

## Owner-linkage adequacy audit

A later linkage-specific audit over the current imported runtime database reviewed candidate `122774` directly and found:

- 1,947 candidate damage events,
- 12 distinct candidate source actors,
- `log_actor` columns: `report_code`, `fight_id`, `actor_id`, `guid`, `name`, `display_name`, `actor_type`, `role`, `anonymous`, `raw_json`,
- no explicit linkage-like actor columns,
- no owner/master/parent/summon/pet/companion relationship paths in candidate-event raw JSON.

Imported linkage evidence present: **NO**.

The difference between the earlier 82-source discovery count and the later 12-source linkage-audit count reflects different audit scopes/selection logic and is not interpreted as contradictory ownership evidence. Neither audit establishes pet-to-owner identity.

## Unresolved executable fields

- `activation_anchor`
- `first_tick_offset_seconds`
- `refresh_boundary`
- `magnitude_policy`

Even though the observed first offset is close to the reviewed 2-second attack cadence, the engine must not infer those missing semantics from timing/window co-occurrence alone.

## Park decision

Do not promote candidate `122774` as executable Skeletal Archer ownership from the current imported corpus.

Revisit only when at least one of the following is available:

1. ESO Logs/imported metadata with explicit pet owner/master/parent linkage,
2. a deterministic external actor relationship source that can be joined to the reviewed report/fight/source actors, or
3. controlled evidence that independently establishes the missing runtime semantics without relying on unlinked pet identity.

Until then, preserve reviewed partial semantics and fail closed for unresolved executable fields.
