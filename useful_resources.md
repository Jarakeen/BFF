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

---

## Calculators / independent cross-checks

### ESO Decoded tools
https://esodecoded.com/tools

**Use for:** Independent cross-checks of traits, glyphs, Mundus values, stats, foods, sets, Champion Points, arena sets, and other build/math references.

**Confidence:** Validation / corroboration.

**Notes:** Useful for finding discrepancies and sanity-checking results. Check the tool/data date before using numerical values as current-game truth.

### ESO-Hub Scribing Simulator
https://eso-hub.com/en/scribing-simulator

**Use for:** Scribing combination exploration and a practical UX/reference model for Grimoire + Focus + Signature + Affix selection.

**Confidence:** Validation / corroboration.

**Notes:** Useful for checking names and combinations against the UESP compatibility catalogue. Do not make it the sole source for hardcoded combat math.

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



https://www.btvtools.com/
https://www.esologs.com/
https://eso-hub.com/en/buffs-debuffs
https://game-icons.net/
