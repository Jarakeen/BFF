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

# DD periodic runtime / ESO Logs IDs

These rows capture numeric IDs encountered while researching Rotation Builder periodic runtime semantics. They are intentionally evidence-first: the semantic skill identity remains authoritative, while raw ESO Logs IDs may represent the cast, direct impact, periodic effect, pet hit, or an unrelated effect that merely occurred in the same cast window.

## Stampede

Canonical identity: `stampede`

Canonical/source crosswalk aliases observed from the skill-rank repository:

`28448`, `38788`, `39797`, `39802`, `39807`

| Numeric ID | Working role | Confidence | Evidence / note |
|---:|---|---|---|
| `126474` | ESO Logs secondary periodic-damage candidate | STRONG OBSERVATION | Seen in 784/807 Stampede cast windows in the Lokkestiiz runtime corpus; 9,020 tick-marked events, 8,989 cast-track-linked events, and 6,531 intervals matching the reviewed 1s cadence. Median first event offset from cast was ~1.221s. Do not yet encode as canonical periodic alias until impact-relative timing review is complete. |
| `38792` | ESO Logs direct-impact / arrival-side candidate | STRONG OBSERVATION | Seen in 804/807 Stampede cast windows with 1,076 cast-track-linked events, zero tick-marked events, and median first offset ~0.144s from cast. Strongly resembles the impact/arrival event rather than the residual ground DoT. |
| `26879` | secondary periodic candidate in Stampede windows | UNKNOWN | 1,633 tick-marked events and many ~1s intervals, but no cast-track linkage; may be another concurrent periodic effect. |
| `117809` | secondary periodic candidate in Stampede windows | UNKNOWN | 1,601 tick-marked events and many ~1s intervals, but no cast-track linkage. |
| `16499` | repeated secondary damage identity in Stampede windows | UNKNOWN | Many ~1s intervals but no tick flags/cast-track linkage sufficient to associate it with Stampede. |
| `17902` | repeated secondary damage identity in Stampede windows | UNKNOWN | Repeated event stream; cadence does not match the reviewed Stampede 1s cadence strongly enough for promotion. |
| `17895` | repeated secondary damage identity in Stampede windows | UNKNOWN | Repeated event stream; unresolved association. |
| `46746` | repeated secondary damage identity in Stampede windows | UNKNOWN | Repeated event stream; unresolved association. |

Working timing lesson: Stampede likely requires an **impact-relative activation anchor** rather than blindly measuring `first_tick_offset_seconds` from button/cast time. The strong `38792` impact-like candidate followed by the `126474` ~1s periodic stream is observational evidence only until the linkage is reviewed.

## Skeletal Archer

Canonical identity: `skeletal_archer`

Canonical/source crosswalk aliases observed from the skill-rank repository:

`114317`, `118680`, `20118680`, `30118680`, `40118680`

| Numeric ID | Working role | Confidence | Evidence / note |
|---:|---|---|---|
| `38747` | ESO Logs pet/periodic damage candidate | SUSPECTED | Strongest current 2s-cadence candidate: 860 tick-marked events, 535 reviewed-cadence matches, 158 cast windows. No cast-track linkage, so do not promote yet. |
| `21929` | ESO Logs pet/periodic damage candidate | SUSPECTED | 1,035 tick-marked events, 507 reviewed 2s-cadence matches, 176 cast windows; no cast-track linkage. |
| `18084` | ESO Logs pet/periodic damage candidate | SUSPECTED | 923 tick-marked events, 481 reviewed 2s-cadence matches, 176 cast windows; no cast-track linkage. |
| `40385` | ESO Logs pet/periodic damage candidate | SUSPECTED | 578 tick-marked events, 439 reviewed 2s-cadence matches, 108 cast windows; no cast-track linkage. |
| `148801` | ESO Logs pet/periodic damage candidate | SUSPECTED | 578 tick-marked events, 331 reviewed 2s-cadence matches, 139 cast windows; no cast-track linkage. |
| `21925` | secondary damage candidate in Skeletal Archer windows | UNKNOWN | Many events but weak 2s-cadence evidence and no tick/cast-track linkage. |
| `227072` | secondary damage candidate in Skeletal Archer windows | UNKNOWN | Repeated stream with limited 2s-cadence evidence; unresolved association. |
| `16499` | repeated secondary damage identity in Skeletal Archer windows | UNKNOWN | Limited 2s-cadence evidence; also appears in Stampede windows, so proximity alone is not identity evidence. |

Current rule: **none of the Skeletal Archer candidate IDs are promoted as the pet attack identity yet**. Cadence agreement alone is insufficient because several unrelated combat streams can repeat at approximately 2 seconds.

## Unnerving Boneyard

Canonical identity: `unnerving_boneyard`

| Numeric ID | Working role | Confidence | Evidence / note |
|---:|---|---|---|
| `117809` | ESO Logs repeated Boneyard damage component | STRONG OBSERVATION | Observed on 162/170 Boneyard cast tracks with 1,871 same-track events. First observed damage clustered near 0.3585s after cast, last near 9.3065s, and clustered same-track intervals concentrate around ~1.0s. Cast-track topology found no separate earlier same-track placement/impact component. In 37 consecutive replacement pairs, no old-track `117809` event occurred at or after the first new-track `117809` event. The corpus has no patch/version provenance and no stable-state magnitude controls, so activation anchor, executable first-tick offset, refresh policy name, and magnitude policy remain unresolved. |

Important identity lesson: `117809` also appears in unrelated Stampede windows without Stampede cast-track linkage. Window proximity alone is weak evidence; exact Boneyard cast-track ownership is what raises this ID to STRONG OBSERVATION for Boneyard.

### DD periodic-ID lesson

For periodic skills, preserve at least three roles separately when evidence supports them:

1. cast/action alias;
2. direct impact / activation alias;
3. periodic effect / repeated-damage alias.

A secondary effect ID can be extremely useful for log correlation without becoming canonical identity. Record it here, carry its confidence label, and only promote it into executable runtime semantics after the timing and component relationship are reviewed.

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
