# Useful ESO Resources

A working source registry for BFF / FoundryDock research and combat-math validation.

The purpose of this file is not merely to collect links. Each source should say what it is useful for and how much confidence we should place in it before turning information into hardcoded game math.

## Source confidence guide

- **Primary / reference-grade** — suitable for establishing raw IDs, client/API behavior, canonical exported data, or other facts that can anchor implementation.
- **Validation / corroboration** — useful for independently checking an interpretation or finding mechanics/data, but should normally be confirmed against a primary source or in-game observation before hardcoding.
- **Historical / contextual** — useful for understanding mechanics and formulas, but patch age must be checked before using numerical values.

---

## Primary / reference-grade

### ESOUI source mirror
https://github.com/esoui/esoui

**Use for:** ESO client UI source, Lua/API usage, events, constants/enums, skill-bar behavior, crafted/scribed ability handling, equipment state, character-stat presentation, and other client-facing behavior.

**Notes:** Default branch is `live`. Prefer this when the question is "how does the ESO client/UI expose or represent this?"

### ESOUI API / developer discussions
https://www.esoui.com/forums/

**Use for:** Client API behavior that is not obvious from signatures alone, especially `GetUnitBuffInfo`, `EVENT_EFFECT_CHANGED`, effect type, status-effect type, ability IDs, stack counts, timing, and known API naming quirks.

**Confidence:** Primary / reference-grade when the explanation comes from ZOS staff; otherwise validation / corroboration.

**Notes:** `GetUnitBuffInfo` / `EVENT_EFFECT_CHANGED` expose timing, stacks, effect type, ability type, status-effect type, and ability ID. Do not assume the legacy `buffType` string is a real `BuffType` enum; ZOS staff documented that it is a poorly named legacy/debug value. Use the actual typed returns and live source definitions instead.

### Official ESO patch notes archive
https://forums.elderscrollsonline.com/en/categories/patch-notes

**Use for:** Versioned skill/passive changes, named-buff changes, rank-dependent durations, developer-stated mechanic changes, and establishing when a rule entered or left the live game.

**Confidence:** Primary / reference-grade for the documented change history. Pair with current live data or in-game validation when proving that an old rule still survives unchanged in the active update.

**Notes:** Especially useful when a current third-party tooltip has already moved to PTS/future-patch data. Record the exact patch/update being cited instead of treating the newest visible wording as timeless truth. Update 51 is a critical version boundary for named effects and Alchemy: Brutality absorbs Sorcery, Savagery absorbs Prophecy, and Vexation is introduced as Mending's healing-done reduction counterpart.

### UESP ESO Log Collector
https://esoitem.uesp.net/viewlog.php

**Use for:** UESP datamined / ESO Log Collector data exploration, IDs, game-data records, and provenance checks.

**Notes:** Prefer exported/raw records over manually transcribed values when available. Record game update/API version/retrieval date whenever the export provides them.

### UESP skill coefficient export
https://esolog.uesp.net/exportJson.php?table=skillCoef

**Use for:** Canonical raw skill coefficient records used by the Phase 3 tooltip/effect pipeline.

**Notes:** Coefficients are raw inputs, not complete tooltip formulas. Preserve coefficient provenance and do not treat regression metadata as a gameplay multiplier.

### UESP Scribing
https://en.uesp.net/wiki/Online:Scribing

**Use for:** Grimoires, Focus/Signature/Affix script catalogues, Grimoire compatibility, scribing-system rules, resulting-skill naming behavior, and character/archive behavior.

**Notes:** Particularly useful for the Scribed Skills builder. Compatibility between a script and a Grimoire does not by itself prove every three-script combination is legal; some combinations have additional exclusions.

---

## Runtime / combat-event validation

### LibCombat API
https://github.com/Solinur/LibCombat/blob/master/docs/API.md

**Use for:** Runtime combat-event semantics, damage/healing events, buffs/effects, resources, combat state, weapon swaps, skill timing, and ability IDs exposed during combat.

**Confidence:** Validation / corroboration.

**Notes:** Excellent for checking whether BFF's combat-state/proc/uptime model corresponds to observable game events. It is an addon library built on ESO APIs, so use ESOUI/client APIs as the more foundational source when the two layers need to be distinguished.

### ESO Logs
https://www.esologs.com/

**Use for:** Real-run encounter timelines, cast/event ordering, target patterns, mechanic cadence, add timing, role behavior, and checking whether a proposed strategy description matches what successful groups actually do.

**Confidence:** Validation / runtime corroboration.

**Notes:** Excellent for filling or validating Encounter-page timelines after mechanic identity is known. Logs show what happened in a run, not necessarily the complete game rule. Use multiple representative logs before treating cadence or target patterns as general, and reconcile patch/version differences.

### BTV Tools
https://www.btvtools.com/

**Use for:** ESO Logs analysis, buff/debuff uptime, crit and penetration analysis, Z'en/Heat Shock stack tracking, roster planning, top-log player-meta comparisons, calculators, and searchable ESO skills/sets/buff data.

**Confidence:** Validation / runtime and build-practice corroboration.

**Notes:** Particularly useful for comparing FoundryDock's Performance, Comp Maker, Rotation, and support-coverage outputs against an independent player-facing implementation. BTV Tools can import specific ESO Logs fights, exclude boss downtime, inspect group coverage over time, and build trial rosters from logged clears. Treat its derived calculations and provider relationships as corroboration rather than shared canonical truth until reconciled against primary data, official patch history, or FoundryDock's reviewed mechanics layer.

---

## Calculators / independent cross-checks

### ESO Decoded tools
https://esodecoded.com/tools

**Use for:** Independent cross-checks of traits, glyphs, Mundus values, stats, foods, sets, Champion Points, arena sets, and other build/math references.

**Confidence:** Validation / corroboration.

**Notes:** Useful for finding discrepancies and sanity-checking results. Check the tool/data date before using numerical values as current-game truth.

### ESO-Hub skill pages
https://eso-hub.com/en/skills

**Use for:** Current readable skill-line rosters and tooltip wording when reviewing class, weapon, guild, and world skill/passive families.

**Confidence:** Validation / corroboration.

**Notes:** Useful for confirming the current visible passive roster and effect wording. Versioned numerical changes should still be reconciled against official patch notes or canonical game data before hardcoding combat math.

### ESO-Hub Buffs & Debuffs
https://eso-hub.com/en/buffs-debuffs

**Use for:** Enumerating current named-effect providers across skills and sets, checking readable Major/Minor effect values, durations, targets, and provider relationships.

**Confidence:** Validation / corroboration.

**Notes:** Particularly useful for discovering missing provider relationships for Combat Reference. Treat provider enumeration as research candidates until reconciled against official patch history, canonical game data, or reviewed BFF relationships. Do not copy current provider lists directly into canonical registries without review.

### ESO-Hub Status Effects
https://eso-hub.com/en/status-effects

**Use for:** Status-effect families, associated damage types, proc-chance categories, readable status-effect behavior, and candidate values/durations that need canonical review.

**Confidence:** Validation / corroboration.

**Notes:** Useful for driving the `Not modeled` gap queue. Current page lists Burning, Chilled, Concussed, Diseased, Hemorrhaging, Overcharged, Poisoned, and Sundered with their associated damage types and proc-chance categories. Cross-check numerical/status behavior against patch notes, client data, or combat evidence before promoting it to canonical truth.

### ESO-Hub set pages
https://eso-hub.com/en/sets

**Use for:** Current readable gear-set tooltip wording, including set-trigger conditions, cooldown/lockout wording, target descriptions, and duration modifiers such as Jorvuld's Guidance.

**Confidence:** Validation / corroboration.

**Notes:** For U50 Jorvuld's Guidance, the five-piece tooltip was rechecked 2026-09-10 and states a 40% duration increase to Major buffs, Minor buffs, and damage shields applied by the wearer to self/allies while in combat. Preserve patch/version provenance and reconcile against primary game data before broadening hardcoded semantics.

### ESO-Hub trial guides
https://eso-hub.com/en/guides

**Use for:** Boss-by-boss trial strategy, health-percentage transitions, hardmode differences, target counts, common handling, role responsibilities, add priority, portal/side-team mechanics, and raid-lead callouts for Encounter-page strategy/timeline backfill.

**Confidence:** Validation / gameplay-practice corroboration.

**Notes:** Prefer authored long-form trial guides over generic zone pages. These are particularly useful for filling reviewed Encounter-page strategy when canonical structural data is sparse. Do not treat every numerical statement as immutable game truth: reconcile defensive properties, exact target counts, and patch-sensitive timings against official patch notes, UESP/client data, Combat Alerts, or logs. Dreadsail Reef already demonstrates why: current guide prose and official patch history disagree on Rapid Deluge blockability.

### ESO-Hub Scribing Simulator
https://eso-hub.com/en/scribing-simulator

**Use for:** Scribing combination exploration and a practical UX/reference model for Grimoire + Focus + Signature + Affix selection.

**Confidence:** Validation / corroboration.

**Notes:** Useful for checking names and combinations against the UESP compatibility catalogue. Do not make it the sole source for hardcoded combat math.

---

## Gameplay / raid-practice references

### Xynode Gaming
https://xynodegaming.com/

**Use for:** Gameplay explanations, encounter handling, role expectations, build context, and organized-player practice that can help distinguish game-engine possibility from how experienced groups actually play.

**Confidence:** Validation / gameplay-practice context.

**Notes:** Useful for Encounter-page strategy, Field Notes, and practice corroboration, not as sole authority for canonical combat math. Search results may be less indexable than ESO-Hub or official sources, so use targeted page retrieval when a specific mechanic or encounter is under review.

### The Tank Club
https://thetankclub.com/game/the-elder-scrolls-online/

**Use for:** Tank-specific trial and dungeon strategy, main-tank/off-tank role division, boss positioning and facing, add ownership, taunt swaps, mitigation choices, survivability, support-set context, and practical organized-group tank play.

**Confidence:** Validation / gameplay-practice corroboration.

**Notes:** Particularly useful when Encounter-page research needs to answer who tanks what, where an enemy should be positioned, when tanks swap, or how experienced tanks handle a mechanic in Veteran/Hard Mode. The site is actively maintained and includes current 2026 tank builds plus dedicated trial tank guides. Treat tank strategy and role practice as corroboration rather than canonical mechanic math; reconcile exact timings, target counts, damage types, and patch-sensitive mechanic properties against official notes, UESP/client data, or logs before promoting them to shared mechanics truth.

### Ninja Pulls
https://www.youtube.com/@NinjaPulls

**Use for:** Current ESO trial guides, boss/mechanic breakdowns, trial preparation, DPS and support practice, class/system explanations, and organized-group gameplay examples.

**Confidence:** Validation / gameplay-practice corroboration.

**Notes:** Especially useful for newer encounter guides and for comparing FoundryDock's raid-lead explanations against concise player-facing mechanic breakdowns. Recent material includes dedicated trial-guide, trial-prep, and mechanic-focused videos. Video publication date and game update matter; corroborate exact numerical properties against official notes, UESP/client data, or logs.

### SeaUnicorn
https://www.youtube.com/@SeaUnicorn

**Use for:** ESO gameplay footage, raid/trial demonstrations, positioning examples, mechanic execution, and player-practice corroboration when a visual example is more useful than written prose.

**Confidence:** Validation / gameplay-practice corroboration.

**Notes:** Use encounter-specific videos as visual evidence of how groups execute mechanics, not as sole authority for exact combat rules or patch-sensitive numbers. Record the video date/update when using it as encounter evidence.

### FaceheadMcGee
https://www.youtube.com/@FaceheadMcGee

**Use for:** ESO raid/trial gameplay, mechanic demonstrations, positioning and role execution, and visual cross-checks for Encounter-page strategy and Raid Map research.

**Confidence:** Validation / gameplay-practice corroboration.

**Notes:** Treat footage as observed player practice. It is particularly useful for checking what a mechanic looks like and how a successful group handles space, movement, stack positions, and role assignments. Pair exact mechanic claims with primary or reviewed textual evidence.

### Temfoolery
https://www.youtube.com/@Temfoolery

**Use for:** ESO dungeon and trial strategy videos, mechanic demonstrations, positioning, role execution, and organized-group gameplay examples that can help corroborate Encounter-page strategy research.

**Confidence:** Validation / gameplay-practice corroboration.

**Notes:** Use encounter-specific videos as observed player practice, especially when researching Veteran/Hard Mode execution and spatial handling. Record the video date/update and corroborate exact timings, target counts, damage properties, and other patch-sensitive mechanics against official notes, UESP/client data, or logs before promoting them to shared mechanics truth.

### Game-Maps.com ESO maps and walkthroughs
https://game-maps.com/ESO/The-Elder-Scrolls-Online.asp

**Use for:** Zone and dungeon geography, entrances, landmarks, boss-room context, route planning, and visual positioning references that can help build or validate Encounters-page Raid Maps.

**Confidence:** Validation / positioning corroboration.

**Notes:** Use this for spatial context, map labels, and route/layout research rather than combat-math authority. Pair encounter-specific positioning claims with reviewed strategy sources or in-game/log evidence before treating them as required raid handling. The site maintains broad ESO map coverage and links current and legacy content maps.

---

## Visual / UI asset references

### Game-icons.net
https://game-icons.net/

**Use for:** Generic game/UI iconography and visual-reference ideas for non-proprietary FoundryDock interface symbols, mechanic categories, status markers, and prototype/mockup concepts.

**Confidence:** Visual-reference source only; not a gameplay or mechanic authority.

**Notes:** Check the license/attribution requirements for any individual icon before shipping it. Do not treat icon names or categories as ESO terminology or mechanics data.

---

## Historical / mechanics references

These can be extremely useful for deriving or understanding ESO formulas, but numerical claims must be reconciled against the current patch before implementation.

### UESP ESO Build Editor
https://en.uesp.net/wiki/Special:EsoBuildData

**Use for:** Formula archaeology, build-stat relationships, and comparison against UESP's implementation.

**Confidence:** Historical / contextual unless independently verified for the current update.

---

## BFF source-use rule

Before a mechanic enters the shared stat/combat pipeline:

1. Establish the formula or raw data source.
2. Verify its activation/eligibility rule.
3. Add a deterministic test.
4. Route it through the correct standing, active-bar, combat-state, target, or attack-family layer.
5. Validate against a live character sheet, tooltip, combat log, or another appropriate observable result.

A convenient calculator matching our expected number is evidence, not proof. ESO already provides enough opportunities for accidental folklore without us manufacturing more.
