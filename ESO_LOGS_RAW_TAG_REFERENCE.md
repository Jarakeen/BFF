# ESO Logs Raw Tag / Numeric ID Reference

Purpose: keep a durable research index of raw ESO Logs numeric ids and event tags that BFF has encountered, so we do not have to rediscover the same aliases repeatedly.

## Boundary rule

**These numeric ids are observational evidence handles only. They are not BFF canonical skill/effect identities.**

BFF canonical identity remains semantic lower_snake_case. Raw ESO Logs ids can vary by morph, caster, context, effect row, log representation, or other runtime conditions. Never replace canonical semantic identity with a numeric id from this file.

Use this file as a research cheat sheet, not as mechanics authority.

## Confidence labels

- **REVIEWED** — meaning is supported by repeated log evidence and/or an external authoritative/reference source.
- **STRONG OBSERVATION** — repeated pattern is compelling, but the underlying mechanic/name has not been fully verified.
- **SUSPECTED** — plausible interpretation from timing/context; requires more evidence.
- **UNKNOWN** — observed id retained specifically so we do not waste time rediscovering that it exists.
- **DISPROVEN FOR THIS USE** — id meaning may be known, but an earlier hypothesis about what it represented was wrong.

---

# Staff heavy attacks

## Heavy-attack action aliases

These ids identify raw ESO Logs staff-heavy event families in the reviewed Lokkestiiz corpus.

| Raw id | Working meaning | Confidence | Notes |
|---:|---|---|---|
| `15383` | Flame Staff heavy attack | REVIEWED | Charge/release log shape. `begincast` is charge start; later `cast` is release/completion. |
| `18396` | Shock Staff heavy attack | REVIEWED | Channeled log shape. `cast` starts the channel; `damage tick=True` records ticks; `removedebuff` marks channel end. |
| `16212` | Restoration Staff heavy attack | REVIEWED | Channeled log shape. `cast` starts the channel; `damage tick=True` records ticks; `removedebuff` marks channel end. |
| `16261` | Frost Staff heavy attack | REVIEWED | Charge/release log shape. `begincast` is charge start; later `cast` is release/completion. |

### Completion grammar seen in logs

- **Restoration / Shock:** `cast -> channel tick(s) -> removedebuff`
- **Frost / Flame:** `begincast -> cast`

Do not count every raw row as a heavy attack. A single completed heavy can emit multiple ESO Logs rows.

## Weapon-specific heavy restore aliases

These ids appear as self-targeted positive `resourcechange` events associated with completed staff heavies.

| Raw id | Working meaning | Confidence | Observed evidence |
|---:|---|---|---|
| `32760` | Restoration Staff heavy-attack resource return | STRONG OBSERVATION | Repeated at HA completion, usually `+0ms`; common values `4247` and exact double `8494`, plus smaller clipped/conditional-looking values. |
| `60762` | Frost Staff heavy-attack resource return | STRONG OBSERVATION | Observed `2425` after a completed Frost HA in reviewed corpus. Small sample. |
| `60764` | Shock Staff heavy-attack resource return | STRONG OBSERVATION | Observed `2970` after a completed Shock HA in reviewed corpus. Small sample. |

### Restoration Staff observed amounts for `32760`

Current reviewed corpus has included:

- `4247` — common full-looking return.
- `8494` — exactly `2 x 4247`; consistent with an Off Balance double-resource case, but keep this as an evidence interpretation until the exact target state is verified per event.
- `3138`, `1967`, `1799`, `974`, `727`, `646` — occur at normal-looking full channel durations too, so **do not classify these as partial channels merely from duration**. Current investigation is checking whether ESO Logs reports an effective/capped resource gain rather than the attempted full return.

Important: `4247` is an **observed final return**, not a verified base restore. `minmax/heavy_attack_restoration.py` expects a pre-modifier `verified_base_restore` and applies modifiers itself. Feeding `4247` directly into that base field could double-apply Cycle of Life / CP / Revitalize / other modifiers.

---

# Synergy/resource events that were initially mistaken for HA evidence

| Raw id | Meaning / working label | Confidence | Notes |
|---:|---|---|---|
| `95042` | Healing Combustion | REVIEWED | Produced repeated `3960` resource returns. **DISPROVEN FOR THIS USE:** not staff HA restoration. |
| `63507` | Healing Combustion / Orb-related synergy | REVIEWED | Synergy/resource event. **DISPROVEN FOR THIS USE:** not staff HA restoration. |
| `26832` | Blessed Shards | REVIEWED | Synergy/resource event. **DISPROVEN FOR THIS USE:** not staff HA restoration. |

The repeated `3960` value looked temptingly like a fixed heavy restore until event correlation showed it was synergy-related. Keep this entry so we never make that mistake again.

---

# Nearby self-resource events seen around heavy attacks

These frequently appear inside a short time window after a completed HA but currently **do not look like the weapon's own HA-return event**.

| Raw id | Observed values / pattern | Confidence | Current interpretation |
|---:|---|---|---|
| `93072` | commonly `250`, resource type `0` | UNKNOWN | Recurrent self-resource proc/noise near HA events. Not the Resto/Frost/Shock weapon-specific restore alias. |
| `93073` | commonly `250`, resource type `1` | UNKNOWN | Paired with `93072` in some events; likely companion resource-side effect/proc. |
| `99781` | commonly `224`, resource type `1` | UNKNOWN | Recurrent nearby self-resource event. |
| `131489` | commonly `224`, resource type `0` | UNKNOWN | Sometimes paired with `99781`. |
| `190584` | commonly `225`, resource type `0` | UNKNOWN | Recurrent nearby self-resource event. |
| `190583` | commonly `225`, resource type `1` | UNKNOWN | Paired resource-side event in some rows. |
| `263829` | commonly `125`, resource type `0` | UNKNOWN | Nearby self-resource event. |
| `263830` | commonly `125`, resource type `1` | UNKNOWN | Paired with `263829` in some rows. |
| `215651` | observed `200`, resource type `0` | UNKNOWN | Seen after Frost HA, but does not match the stronger Frost restore alias `60762`. |
| `45050` | observed `635`, resource type `0` | UNKNOWN | Seen after Frost HA, not yet identified. |
| `45146` | observed `4`, resource type `2`, max resource `500` | UNKNOWN | Almost certainly a different resource system, not Magicka HA restore. |
| `215726` | observed `65`, resource type `0` | UNKNOWN | Nearby Resto self-resource event; not `32760`. |

Do not infer mechanics solely because an event occurs within 500 ms of a heavy completion.

---

# Resource-type tags

Observed ESO Logs `resourceChangeType` values in this work include `0`, `1`, and `2`.

Current evidence suggests the following **for the reviewed corpus only**:

| Raw resource type | Working interpretation | Confidence | Evidence |
|---:|---|---|---|
| `0` | Magicka-like primary resource in the reviewed healer HA-return events | STRONG OBSERVATION | `32760`, `60762`, and `60764` HA-return candidates all use type `0`; associated max-resource pools are in healer Magicka-like ranges. |
| `1` | Stamina-like resource | SUSPECTED / STRONG OBSERVATION | Often appears as paired small-resource events with much smaller max pools than type `0`. Verify before canonical mapping. |
| `2` | Other/special resource | SUSPECTED | Example: event `45146`, restore `4`, max resource `500`. Clearly not the same pool as standard healer Magicka. |

Do not hard-code these enum meanings from this file until verified against ESO Logs documentation or another authoritative mapping.

---

# Useful raw event fields

The semantic ESO Logs adapter preserves these resource-relevant raw fields:

- `resourceChange`
- `resourceChangeType`
- `otherResourceChange`
- `maxResourceAmount`
- `waste`
- full original `raw_event`

When a restore amount looks clipped or inconsistent, inspect these raw fields before deciding that the mechanic itself changed.

---

# Current open questions

1. Does ESO Logs `resourceChange` represent accepted/effective resource gain when the player is near cap, while `otherResourceChange`, `waste`, or another raw field preserves the attempted amount?
2. Is `4247` the fully modified ordinary Restoration Staff return for the reviewed healer configurations, with `8494` representing Off Balance doubling?
3. What exact pre-modifier base produces the observed Resto/Frost/Shock returns after current live passives/CP/gear are accounted for?
4. Verify the exact ESO Logs mapping for `resourceChangeType` values `0`, `1`, and `2`.
5. Identify the small nearby resource aliases listed above so future timing audits can reject them by meaning, not merely by exclusion.

---

# Evidence / tooling trail

Current research tools:

- `tools/audit_phase13_lokke_raw_heavy_restore.py`
- `tools/audit_phase13_cross_player_heavy_attack_candidates.py`
- `tools/audit_phase13_staff_heavy_attack_restore_corpus.py`
- `tools/audit_phase13_staff_heavy_restore_raw_resource_fields.py`

Primary raw corpus currently used:

- `research/raw/lokkestiiz_corpus.json`

Update this file whenever a raw id is identified, disproven, or materially reinterpreted. Prefer adding provenance/confidence over silently upgrading a guess to fact.
