# ESO Numeric ID Reference

A shared, searchable registry for ESO numeric identifiers encountered while building BFF / FoundryDock.

This file exists so future chats and tools do **not** keep rediscovering, conflating, or silently reinterpreting the same ESO IDs.

## The big rule

**BFF canonical identity is semantic `lower_snake_case`. Numeric ESO IDs are aliases, observations, source handles, or evidence. They are never the canonical skill/effect identity.**

ESO can emit multiple numeric IDs for what players think of as the same skill/effect depending on morph, component, caster, target, combat bundle, display row, log event type, update, or source system. Preserve that ambiguity instead of forcing one magic number to rule them all.

When code needs stable identity, use the semantic ID. When evidence arrives with a numeric ID, map it to the semantic identity with provenance and context.

## How to search this file

Useful search patterns:

- skill name: `Budding Seeds`
- semantic ID: `budding_seeds`
- numeric ID: `129434`
- source type: `ESO Logs`, `ESOUI`, `UESP`, `MajorMinor.lua`
- confidence: `REVIEWED`, `STRONG OBSERVATION`, `SUSPECTED`, `UNKNOWN`
- ID role: `source ability`, `periodic effect`, `activation/action`, `resourcechange`, `display id`

## Confidence labels

- **REVIEWED**: supported by repeated evidence and/or an authoritative/reference source.
- **STRONG OBSERVATION**: repeated pattern is compelling, but the exact underlying ESO meaning is not fully verified.
- **SUSPECTED**: plausible interpretation that still needs corroboration.
- **UNKNOWN**: observed and retained so we do not waste time rediscovering it.
- **DISPROVEN FOR THIS USE**: the ID may be real, but an earlier interpretation/use was wrong.

---

# Healer / support skill and effect IDs

These rows are deliberately component-aware. A cast/action ID and a periodic-effect ID may differ for the same player-facing skill.

| Semantic ID | Player-facing name | Numeric ID | ID role / component | Confidence | Notes |
|---|---|---:|---|---|---|
| `budding_seeds` | Budding Seeds | `129434` | reviewed periodic healing effect, component 2 | REVIEWED | Used by the reviewed ESO Logs healer effect-alias mapping. |
| `radiating_regeneration` | Radiating Regeneration | `40079` | reviewed periodic healing effect, component 1 | REVIEWED | Reviewed ESO Logs effect alias. |
| `illustrious_healing` | Illustrious Healing | `40059` | reviewed periodic healing effect, component 1 | REVIEWED | Reviewed ESO Logs effect alias. |
| `energy_orb` | Energy Orb | `42039` | reviewed periodic healing effect, component 1 | REVIEWED | Reviewed ESO Logs effect alias. |
| `echoing_vigor` | Echoing Vigor | `61506` | reviewed periodic healing effect, component 1 | REVIEWED | Reviewed ESO Logs effect alias. |
| `budding_seeds` | Budding Seeds | `85840` | raw ESO Logs activation/action-side ID seen in healer corpus | STRONG OBSERVATION | Do not substitute for periodic effect `129434`. |
| `illustrious_healing` | Illustrious Healing | `40058` | raw ESO Logs activation/action-side ID seen in healer corpus | STRONG OBSERVATION | Distinct from reviewed periodic effect `40059`. |
| `energy_orb` | Energy Orb | `42038` | raw ESO Logs activation/action-side ID seen in healer corpus | STRONG OBSERVATION | Distinct from reviewed periodic effect `42039`. |
| `echoing_vigor` | Echoing Vigor | `61505` | raw ESO Logs activation/action-side ID seen in healer corpus | STRONG OBSERVATION | Distinct from reviewed periodic effect `61506`. |
| `budding_seeds` | Budding Seeds | `85841` | observed candidate / unresolved related ID | UNKNOWN | Retained explicitly; do not promote without review. |
| `elemental_susceptibility` | Elemental Susceptibility | `41556` | source ability ID | REVIEWED | Seen in canonical/source-ability lookup paths. |
| `expansive_frost_cloak` | Expansive Frost Cloak | `86129` | source ability ID | REVIEWED | Seen in canonical/source-ability lookup paths. |
| `overflowing_altar` | Overflowing Altar | `43287` | source ability ID | REVIEWED | Seen in canonical/source-ability lookup paths. |

### Important healer-ID lesson

A single player-facing skill can legitimately have several numeric IDs. Example:

- `illustrious_healing` cast/action-side observation: `40058`
- `illustrious_healing` reviewed periodic healing effect: `40059`

That is expected. Do not "fix" the database by collapsing these into one number.

---

# Staff heavy-attack raw IDs

## Heavy-attack action aliases

| Weapon | Raw ID | Confidence | Observed ESO Logs shape |
|---|---:|---|---|
| Flame Staff | `15383` | REVIEWED | charge/release: `begincast -> cast` |
| Shock Staff | `18396` | REVIEWED | channel: `cast -> damage tick(s) -> removedebuff` |
| Restoration Staff | `16212` | REVIEWED | channel: `cast -> damage tick(s) -> removedebuff` |
| Frost Staff | `16261` | REVIEWED | charge/release: `begincast -> cast` |

## Heavy-attack resource-return aliases

| Raw ID | Working meaning | Confidence | Notes |
|---:|---|---|---|
| `32760` | Restoration Staff heavy-attack resource return | STRONG OBSERVATION | Repeated at HA completion. Observed values include `4247`, exact double `8494`, and smaller effective/clipped-looking values. |
| `60762` | Frost Staff heavy-attack resource return | STRONG OBSERVATION | Observed `2425` in reviewed corpus. |
| `60764` | Shock Staff heavy-attack resource return | STRONG OBSERVATION | Observed `2970` in reviewed corpus. |

`4247` is an observed final return, **not** a verified pre-modifier base value. Never feed it into code expecting a base restore without proving the modifier chain first.

---

# Synergy / resource IDs that can be mistaken for heavy-attack returns

| Raw ID | Working meaning | Confidence | Status |
|---:|---|---|---|
| `95042` | Healing Combustion | REVIEWED | DISPROVEN FOR HA USE |
| `63507` | Healing Combustion / Orb-related synergy | REVIEWED | DISPROVEN FOR HA USE |
| `26832` | Blessed Shards | REVIEWED | DISPROVEN FOR HA USE |

Repeated `3960` resource gains from these events are not evidence for staff heavy-attack restoration.

---

# Nearby / unresolved self-resource IDs

These IDs have appeared near completed heavy attacks but are **not** currently treated as the weapon's own HA restore event.

| Raw ID | Common observation | Confidence | Current note |
|---:|---|---|---|
| `93072` | `250`, resource type `0` | UNKNOWN | recurrent self-resource event |
| `93073` | `250`, resource type `1` | UNKNOWN | often paired with `93072` |
| `99781` | `224`, resource type `1` | UNKNOWN | recurrent nearby event |
| `131489` | `224`, resource type `0` | UNKNOWN | sometimes paired with `99781` |
| `190584` | `225`, resource type `0` | UNKNOWN | recurrent nearby event |
| `190583` | `225`, resource type `1` | UNKNOWN | paired side event in some rows |
| `263829` | `125`, resource type `0` | UNKNOWN | nearby self-resource event |
| `263830` | `125`, resource type `1` | UNKNOWN | paired with `263829` |
| `215651` | `200`, resource type `0` | UNKNOWN | seen after Frost HA; not `60762` |
| `45050` | `635`, resource type `0` | UNKNOWN | seen after Frost HA |
| `45146` | `4`, resource type `2`, max `500` | UNKNOWN | likely a different resource system |
| `215726` | `65`, resource type `0` | UNKNOWN | nearby Resto event; not `32760` |

Do not infer identity merely because an event occurs within a few hundred milliseconds of another event.

---

# ESO Logs resourceChangeType observations

| Raw value | Working interpretation | Confidence |
|---:|---|---|
| `0` | Magicka-like primary resource in reviewed healer HA-return events | STRONG OBSERVATION |
| `1` | Stamina-like resource | SUSPECTED / STRONG OBSERVATION |
| `2` | other/special resource | SUSPECTED |

These are evidence notes, not a canonical enum contract until independently verified.

---

# Major / Minor effect IDs

The bulk Major/Minor effect-ID corpus extracted from `MajorMinor.lua` is maintained in:

`docs/major_minor_effect_ids.md`

That file is the large searchable list for Major/Minor effect aliases. This registry deliberately does not duplicate every row because duplicate giant lists drift. Use the semantic effect name here and the bulk file for all observed aliases.

Examples:

| Semantic identity | Effect | Numeric aliases | Source |
|---|---|---|---|
| `buff:major_brittle` | Major Brittle | `145977`, `167681` | `MajorMinor.lua` extraction |
| `buff:major_force` | Major Force | `120013`, `154830`, `176849`, `214424`, `221602`, `238550`, `242717`, `40225`, `61747`, `85154` | `MajorMinor.lua` extraction |

Again: `buff:major_force` is the stable BFF identity. The ten numbers are aliases/evidence handles.

---

# Historical / versioned data rule

Reference-history files may record update/year/change history for skills, passives, gear sets, Champion Points, and other game objects.

When a historical source provides or requires a numeric ID:

1. record the semantic identity first;
2. record the numeric ID with its exact role if known (`ability_id`, `display_id`, `effect_id`, ESO Logs raw ID, etc.);
3. record the update/year when the ID is version-sensitive;
4. preserve multiple IDs when evidence shows context-specific variants;
5. never rewrite current canonical mechanics merely because an old historical ID existed;
6. never guess an old numeric ID from a current one.

History is provenance/reference flavor unless separately promoted through the normal canonical mechanics review path.

---

# Other ID families

## Encounter IDs

Encounter identity in BFF is semantic, for example:

- `garvin_the_tracker`
- `ilambris_twins`
- `allene_pellingare_wayrest_sewers_i`

Raw actor IDs or numeric combat-log IDs may be attached as evidence, but the semantic encounter ID remains authoritative.

## Content IDs

Content identity is also semantic, for example:

- `lep_seclusa`
- `crypt_of_hearts_i`
- `dreadsail_reef`

Do not replace these with a numeric external-source ID unless a specific adapter requires it.

## Release/update IDs

Dungeon/trial/reference history uses explicit release metadata when known, such as `release_update: 34` / `U34` and `release_year: 2022`. Update IDs describe chronology; they are not skill/effect identities.

---

# Related durable sources

- `docs/major_minor_effect_ids.md` — bulk Major/Minor aliases from `MajorMinor.lua`.
- `ESO_LOGS_RAW_TAG_REFERENCE.md` — detailed raw ESO Logs event/ID research and unresolved resource-event observations.
- `services/rotation_healer_esologs_canonical_skill_alias_service.py` — reviewed healer periodic-effect alias mappings used by runtime evidence interpretation.
- `SYSTEM_ARCHITECTURE_RULES.md` — authority and architecture rules.

---

# How to add a new ID

When a chat discovers a useful numeric ID, add it here if it is likely to be reused across workstreams.

Minimum useful record:

```text
semantic identity | player-facing name | numeric ID | ID role/context | confidence | source/provenance
```

Preferred behavior:

- **Add**, do not silently replace, when a second numeric ID appears for the same semantic object.
- State whether the ID is a cast/action ID, effect ID, component ID, display ID, source ability ID, ESO Logs raw ID, actor ID, or something else.
- Include update/year when version-sensitive.
- Preserve contradictory observations with notes until resolved.
- Mark bad hypotheses `DISPROVEN FOR THIS USE` instead of deleting the evidence trail.
- Promote confidence only when evidence justifies it.
- If the meaning is unknown, keep the number and mark it `UNKNOWN` rather than inventing certainty.

The goal is not to make ESO's ID ecosystem look clean. It plainly is not. The goal is to make our handling of it clean.
