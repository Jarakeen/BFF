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

### UESP ESO Log Collector source repository
https://github.com/uesp/uesp-esolog

**Use for:** Auditing how UESP derives and exports ESO Log Collector tables, including `minedItemSummary` field selection, version suffixes, raw-data provenance, and whether a field exists upstream before FoundryDock imports it.

**Confidence:** Primary / reference-grade for UESP's own export implementation; it is evidence about the UESP data pipeline, not direct proof of an ESO combat mechanic.

**Notes:** The current `createMinedItemSummary.php` implementation includes enchant name/description among summary fields and does not expose a weapon-enchantment cooldown field. Treat imported item/enchant identifiers as provenance/lookup data unless their game-mechanic meaning is separately proven; do not infer an internal cooldown from an item-link or default-enchant identifier.

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

**Notes:** Useful for confirming the visible passive roster and effect wording, but the site may expose PTS/future-update values before that update is live. On 2026-09-23, Update 51 was still scheduled for September 28 while current ESO-Hub weapon pages already reflected the U51-facing tooltip set. Always reconcile patch-sensitive values against the live update boundary and official notes before hardcoding combat math.

### UESP raw ESO Character Build Data
https://chat.uesp.net/esobuilddata/

**Use for:** Raw character-build snapshots containing skill/passive names, ranks, ability IDs, and rendered tooltip values that can corroborate current passive wording and rank-specific magnitudes.

**Confidence:** Validation / corroboration.

**Notes:** Useful for cross-checking a passive against FoundryDock's imported canonical data. Individual build records may be old, so compare multiple records and a current source before promoting patch-sensitive values. For Bow Accuracy, multiple UESP records show Rank 2 at 1314 Critical Chance rating and Rank 1 at 657; ESO-Hub currently reports the same values.

### UESP Lifesteal mechanics page
https://en.uesp.net/wiki/Online:Lifesteal

**Use for:** Readable Minor Lifesteal provider history, tooltip wording, affected-target semantics, and candidate cadence/ownership claims that can be tested against ESO Logs or live combat events.

**Confidence:** Validation / historical corroboration.

**Notes:** The page currently describes attackers receiving 600 Health every 1 second while damaging an affected enemy, but its revision and provider history cross multiple game updates. Use it to frame runtime-evidence questions, not to promote a cooldown, event owner, or numeric heal rule without current-version log/client validation.

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

## Hyperioxes — ESO Ultimate Generation Calculator (U50 snapshot)

- **Location:** `math/ESO Ultimate Generation Calculator _ U50 _ Hyperioxes.htm`
- **Useful for:** Discovering the candidate universe for Ultimate generation, including Class Masteries, passives, skills, gear, base combat generation, Heroism, and Decisive.
- **Confidence:** **Medium for source discovery; low for hardcoded combat math without corroboration.** Labels and displayed rates still require canonical tooltip, trigger, cooldown, recipient, proc-chance, and build-legality verification.
- **Version/provenance:** Saved U50 page snapshot reviewed 2026-09-13. Treat it as version-sensitive observational tooling rather than a replacement for canonical ESO mechanics data.


### ESO-Hub set tooltips
https://eso-hub.com/en/sets/

**Use for:** Current live-facing set tooltip wording, set locations, piece bonuses, proc triggers, duration/cooldown wording, and quickly identifying mechanics that need deeper canonical validation.

**Confidence:** Validation / corroboration.

**Notes:** Useful for spotting runtime-scaling obligations before hardcoding them. Example: the current Roar of Alkosh tooltip states that its resistance reduction equals the user's Weapon Damage at activation, capped at 6000. Treat ESO-Hub as corroboration rather than the sole authority for formulas; confirm critical math against primary data, official patch notes, or in-game/runtime evidence before promoting it to canonical engine math.


### ZOS Horns of the Reach v3.1.5 weapon-enchantment trait and Oblivion notes
https://forums.elderscrollsonline.com/en/discussion/365904

**Use for:** Primary historical ZOS evidence that Infused reduces weapon-enchantment cooldown, Torug's Pact modifies weapon-enchantment cooldown multiplicatively with Infused, and Damage Health (Oblivion) weapon-enchantment damage cannot critically strike. Also useful for the documented Oblivion/Prismatic Infused cooldown bug fixes in that patch.

**Confidence:** Primary / reference-grade for the explicitly documented mechanics in v3.1.5. Treat it as historical evidence; current exact numeric trait values or broader ordinary-enchantment critical rules still require current corroboration before hardcoding.

**Notes:** The developer comment specifically identifies Oblivion damage as non-critical. It does not establish that every other weapon-enchantment damage family can critically strike, nor which critical-stat family an ordinary glyph would use.

### ZOS Update 20 weapon-enchantment activation rules
https://forums.elderscrollsonline.com/en/discussion/435633/pts-patch-notes-v4-2-0

**Use for:** Authoritative weapon-enchantment activation topology. ZOS states that weapon enchantments proc 100% of the time when not on cooldown when a Light Attack, Heavy Attack, or weapon ability deals damage; Dual Wield weapon abilities may proc either weapon and favor an enchantment that is not on cooldown.

**Confidence:** Primary / reference-grade for the documented activation rule.

**Notes:** This closes activation-cause evidence, not the exact current base cooldown values, off-bar source persistence, poison replacement, or same-identity cooldown sharing. Those remain separately gated until current-version authoritative evidence is available.


### ZOS Update 21 weapon-enchantment cooldown example
https://forums.elderscrollsonline.com/en/discussion/463161/playstation-4-patch-notes-v1-45-wrathstone-update-21

**Use for:** Primary-source evidence that a normal direct-damage weapon enchantment uses a 4-second cooldown. ZOS's one-handed enchantment balance example explicitly preserves a 4-second cooldown while halving enchantment potency.

**Confidence:** Primary / reference-grade for the documented direct-damage cooldown example.

**Notes:** Do not generalize the 4-second value to Crusher, Weakening, Hardening, or other buff/debuff enchantments. Their family cooldown still needs its own authoritative evidence.

### ZOS Dark Brotherhood poison/enchantment suppression rule
https://forums.elderscrollsonline.com/en/discussion/261799/pts-patch-notes-v2-4-0

**Use for:** Primary-source topology for poison-equipped weapon sets. ZOS states that while a weapon set has a poison equipped, weapon enchantments on that set are temporarily suppressed.

**Confidence:** Primary / reference-grade for the documented suppression rule.

**Notes:** This establishes replacement/suppression topology, not poison proc cadence or current enchantment cooldown values.


### ZOS v4.2.6 one-damage-instance weapon-enchantment rule
https://forums.elderscrollsonline.com/en/discussion/443312/pc-mac-patch-notes-v4-2-6

**Use for:** Authoritative per-damage-instance weapon-enchantment exclusivity. ZOS fixed Dual Wield weapon enchantments both proccing from one isolated damage instance and clarified that separate hits from a multi-hit ability can proc separate enchantments.

**Confidence:** Primary / reference-grade for the documented exclusivity rule.

**Notes:** This proves that one isolated damage occurrence cannot activate two weapon enchantments simultaneously. It does not by itself establish same-identity shared cooldown behavior or the exact source-selection algorithm beyond the separately documented Update 20 off-cooldown preference.


### ZOS Update 19 weapon-source persistence rule
https://forums.elderscrollsonline.com/en/discussion/428092/pts-patch-notes-v4-1-3

**Use for:** Primary-source weapon-enchantment source ownership across weapon swaps. ZOS clarified that enchantments remember the weapon from which an ability was fired; if the ability deals damage after a bar swap, the enchantment on that original weapon fires.

**Confidence:** Primary / reference-grade for source-weapon ownership across a swap.

**Notes:** This promotes off-bar/source-weapon persistence independently from cooldown-sharing rules. It does not prove that duplicate enchantment identities share one cooldown or establish the buff/debuff-family base cooldown.


### ZOS Combat Team: single-target DoTs do not trigger weapon enchants
https://forums.elderscrollsonline.com/en/discussion/443598/adjustments-to-how-weapon-enchants-and-poisons-trigger

**Use for:** Primary-source weapon-enchantment occurrence eligibility. ZOS Combat Team staff explicitly narrowed the Update 20 trigger model so single-target Damage over Time abilities, and abilities that apply a single-target DoT, do not repeatedly fire weapon enchantments; direct damage and ground-targeted/AoE effects remain outside that exclusion.

**Confidence:** Primary / reference-grade for the documented trigger-family exception.

**Notes:** This is the authority for classifying exact weapon-skill damage occurrences by component shape instead of treating every tick owned by a weapon ability as enchant-eligible. It does not establish current cooldown duration or duplicate-enchantment cooldown scope.


### ESO forum community testing: duplicate weapon-enchantment cooldown sharing
https://forums.elderscrollsonline.com/en/discussion/460533/clarification-on-enchants-unnecessarily-over-complicated

**Use for:** Corroborative community evidence that identical weapon enchantments share a cooldown across weapon sources/bars. The thread also points back to the ZOS Wolfhunter activation-rule patch notes.

**Confidence:** Community / corroborative only. Useful for shaping the research hypothesis, not sufficient to promote exact combat math.

**Notes:** Keep `same_effect_identity_shares_cooldown` provisional until a ZOS-authored or equivalent current authoritative source directly establishes the shared-timer rule.

### ESO forum community testing: distinct enchant identities use independent cooldowns
https://forums.elderscrollsonline.com/en/discussion/363984/glyphs-cooldown-sharing

**Use for:** Corroborative community evidence that different enchant identities can proc on their own cooldown timers while identical glyph identities share one timer.

**Confidence:** Community / corroborative only. Useful for distinguishing duplicate-identity sharing from distinct-identity independence, but not sufficient for Objective #32 theoretical closure.

**Notes:** This source supports keeping a separate provisional `distinct_effect_identities_have_independent_cooldowns` proof field rather than hiding both topology claims behind one generic cooldown-scope label.


### ESO Forums — “Clarification on enchants: Unnecessarily over-complicated?”
https://forums.elderscrollsonline.com/en/discussion/460533/clarification-on-enchants-unnecessarily-over-complicated

**Use for:** Community corroboration of weapon-enchantment cooldown topology after the Wolfhunter/Update 20 trigger changes. The thread explicitly distinguishes identical enchant identities sharing a cooldown from different enchant identities retaining separate cooldowns, and ties the discussion back to ZOS Update 20 plus Gilliam’s trigger clarification.

**Confidence:** Community / corroborating only. Useful for narrowing the research target and validating that BFF’s provisional topology matches long-running player testing, but **not sufficient to promote same-identity sharing or distinct-identity independence to authoritative Objective #32 combat math** without primary/current proof.


### ESO-Hub — Infused Weapon Trait
https://eso-hub.com/en/traits/weapon/infused

**Use for:** Current-live corroboration of the weapon Infused trait split: enchantment effect strength scales by item quality while enchantment cooldown reduction remains 50%. Useful for checking the imported trait semantics and the Gold/Legendary quality path used by saved builds.

**Confidence:** Current community/reference-grade, not primary ZOS mechanics proof. Use to corroborate the canonical imported trait description and detect data-routing mistakes; prefer primary/client-derived evidence before introducing new hardcoded combat constants.


### ZOS Update 23 PC/Mac Patch Notes v5.1.5 — Oblivion Damage / Decrease Health
https://forums.elderscrollsonline.com/en/discussion/491043/pc-mac-patch-notes-v5-1-5-scalebreaker-update-23

**Use for:** Primary ZOS evidence for the Update 23 player-sourced Oblivion Damage model and Decrease Health weapon enchantment: target-Max-Health scaling, quality-scaled percentage with the documented Legendary CP160 ceiling, maximum damage cap, and the special bypass/non-critical behavior described for player-sourced Oblivion Damage.

**Confidence:** Primary / reference-grade for the documented Update 23 mechanic. Current imported enchant descriptions should still be checked for present-version scaling metadata before exact U50 damage is applied; do not infer glyph quality from weapon quality.


### ESO Support — What is poison-making in The Elder Scrolls Online?
https://help.elderscrollsonline.com/app/answers/detail/a_id/34326/

**Use for:** Current first-party support evidence that poisons are equipped alongside wielded weapon sets and that a poison suppresses the weapon enchantments on that specific weapon set.

**Confidence:** Primary / reference-grade for poison-to-weapon-set ownership and enchantment suppression. This source does not establish current poison proc chance, cooldown, effect duration, or the complete poison formula catalog.


### ZOS PC/Mac Patch Notes v4.2.5 — poison 20% activation
https://forums.elderscrollsonline.com/en/discussion/comment/5552032

**Use for:** Primary ZOS live Update 20 evidence that all poisons proc 20% of the time when a Light Attack, Heavy Attack, or weapon ability deals damage.

**Confidence:** Primary / reference-grade for poison proc chance and qualifying damaging attack families.


### ZOS PC/Mac Patch Notes v4.2.7 — poison single-target DoT exclusion
https://forums.elderscrollsonline.com/en/discussion/444322/pc-mac-patch-notes-v4-2-7

**Use for:** Primary ZOS evidence that weapon enchantments and poisons no longer proc from single-target weapon-ability Damage over Time effects, with specific excluded examples.

**Confidence:** Primary / reference-grade for the single-target DoT exclusion.


### ZOS Update 13 Sneak Peek — global poison cooldown
https://forums.elderscrollsonline.com/en/discussion/310623/update-13-sneak-peak-notes

**Use for:** Primary developer evidence from ESO Creative Director Rich Lambert that all poisons share one global cooldown, no longer have individual cooldowns, and cannot proc more than once every 10 seconds.

**Confidence:** Primary / reference-grade for the introduced global 10-second poison cooldown rule. Later poison fixes found during review do not document a replacement cadence; future contrary ZOS evidence should supersede this field rather than being blended with it.


### ESO Forums — Official Feedback Thread for Poison-Making (ZOS Systems Team)
https://forums.elderscrollsonline.com/en/discussion/261818/official-feedback-thread-for-poison-making/p5

**Use for:** Primary-source design intent for crafted poison cadence and consequence shape. ZOS Systems Team staff explicitly described the move to a 10-second poison cooldown, converting instant poison effects into over-time effects, and drain poisons carrying paired positive/negative effects.

**Confidence:** High for the documented mechanic shape and historical design change because the relevant post is from ZOS staff. Do **not** use the 2016-era numeric tooltip values as current hardcoded magnitudes without a modern canonical data source or current in-game/log validation.

**BFF rule:** Safe evidence for poison runtime topology and consequence structure. Not sufficient by itself for 2026 poison damage/healing/resource magnitudes, dilution, tick interval, or current named-effect values.
