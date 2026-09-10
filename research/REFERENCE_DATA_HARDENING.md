# Reference Data Hardening Pass

## Goal

Combat Reference should not use `Not modeled` as a generic final answer.

Every missing field should end in one of three useful states:

1. **Canonical value** — already carried by a shared FoundryDock mechanics/data authority.
2. **Reviewed research evidence** — a useful source-backed value exists, but has not yet been promoted into the owning canonical runtime/data contract.
3. **Specific unresolved gap** — the exact missing fact and review work are named rather than represented by a bare `Not modeled` label.

Reviewed research must never silently become combat-math authority.

## Source order

1. Existing FoundryDock canonical/reviewed data and runtime contracts.
2. Official ESO live/PTS patch notes for versioned mechanic changes.
3. ESOUI/client API evidence for what the client exposes at runtime.
4. UESP raw/exported records where available.
5. ESO-Hub for current readable tooltips, provider enumeration, status-effect pages, durations, targets, and corroboration.
6. Xynode and other established guide sources for encounter handling and actual-play explanation.
7. Broader web/search results for discovery; promote only after corroboration.

## Completed research family: core status effects

Update 41 is the primary change-history anchor for the modern status-effect behavior. The Reference research layer now carries reviewed U41+ facts for:

- Burning
- Chilled
- Concussion
- Diseased
- Hemorrhaging
- Overcharged
- Poisoned
- Sundered

The facts include delivery shape and important secondary behavior such as Minor Maim/Brittle, Minor Vulnerability, Minor Defile, Magicka restoration/Magickasteal, execute scaling, Hemorrhaging stacks, and Sundered's Weapon/Spell Damage grant.

The canonical `combat_effect` tables remain authoritative for fields they already store. Research enrichment is additive and provenance-bearing.

## Completed research family: non-status combat effects

The reviewed research layer also carries useful evidence for:

- **Off Balance** — official player-source duration, reapplication lockout, and non-consumption behavior from the Update 25-era combat changes.
- **Hindered** — Dreadsail Reef heavy-attack context, healing absorption behavior, duration, and purge restriction from Qcell's ESO-Hub guide corroborated by the original Update 34 PTS discussion.
- **Rattled** — Dreadsail Reef context, damage-done reduction, damage-taken increase, duration, and purge restriction.
- **Devitalized** — Dreadsail Reef context, resistance reduction, damage-taken increase, shield reduction, duration, and purge restriction.

The Dreadsail values are deliberately marked medium-high confidence rather than primary/canonical because the useful numerical detail comes from a respected endgame guide and PTS player evidence rather than a clean ZOS mechanic specification.

## Completed research family: shared passive providers

A shared passive-to-named-effect provider reference now exists for relationships already explicitly reviewed elsewhere in FoundryDock. Initial reviewed providers are:

- **Elder Dragon** -> Minor Brutality
- **Illuminate** -> Minor Sorcery (U50 version scope)
- **Sacred Ground** -> Minor Mending
- **Accelerated Growth** -> Major Mending
- **Maturation** -> Minor Toughness
- **Shadow Barrier** -> Major Resolve

The provider records retain class, skill line, activation condition, target, rank-dependent duration, version scope, and evidence. This prevents passive ownership from being mistaken for permanent uptime.

## Completed research family: component-owned named effects

Component-owned Major/Minor effects now receive human-readable standard-effect facts even when their numeric application remains owned by a downstream damage/healing/mitigation component instead of the standing stat sheet.

Covered values include:

- Minor / Major Berserk: +5% / +10% damage done
- Minor / Major Protection: -5% / -10% damage taken
- Minor / Major Vulnerability: +5% / +10% damage taken
- Minor / Major Slayer: +5% / +10% damage done to Dungeon, Trial, and Arena monsters
- Minor / Major Aegis: -5% / -10% damage taken from Dungeon, Trial, and Arena monsters
- Minor / Major Vitality: +6% / +12% healing received and damage shield strength
- Minor / Major Defile: -6% / -12% healing received and damage shield strength

Update 41 is the version boundary for the current Vitality/Defile semantics: those effects now modify damage shield strength and no longer use the older Defile Health Recovery wording.

## Completed encounter slice: Xalvakka

Xalvakka is the first encounter to use reviewed research as a direct replacement for unresolved display fields while leaving the canonical encounter record untouched.

Initial replacements and additions include:

- **Deadstar** — movement is required; the attack is three sequential player-location meteor impacts rather than one simple fixed target-count event.
- **Summon Wraiths** — failure severity is group-fatal when enough wraiths reach Xalvakka to create an unbreakable shield/wipe state.
- **Soul Resonance** — cleansing creates a persistent Corrupted Azureplasm hazard, so cleanse placement is also a positioning decision.
- **Split** — the flame-covered floor is a persistent hazard and requires movement through limited safe ground while identifying the real copy.
- **Corrupted Blast** — damage scales with absorbed wraith count while Xalvakka's shield is active.

The BFF canonical Xalvakka source record is the primary local evidence for these facts, with Xynode's Rockgrove guide used as gameplay/mechanic corroboration where appropriate. Ambiguous values such as a single integer `Target count` are deliberately left unresolved when the mechanic is actually sequential or pattern-based.

## Missing-value presentation rule

Bare `Not modeled` should not survive the normal Combat Reference loading path.

When reviewed research has a fact for the same field, the unresolved display value should be replaced directly while retaining an explicit `reviewed research` marker, update scope, confidence, and provenance. A canonical structured value always wins and is never overwritten by research.

Examples:

- `Requires movement: Yes ... [reviewed research; U30+; medium-high confidence]`
- `Damage type: Unknown — canonical encounter record has no reviewed damage type yet.`
- `Interruptible: Unknown — interruptibility has not yet been reviewed for this mechanic.`
- `Maximum stacks: No stack mechanic is recorded for this effect.`
- `Tick interval: No periodic tick cadence is recorded; this may be an instant effect or a remaining evidence gap.`

This wording is deliberately honest about what is known without pretending that every absent database cell represents the same kind of uncertainty.

## Next research families

1. Continue encounter mechanics, prioritizing Rockgrove, Dreadsail Reef, Sunspire, Kyne's Aegis, and other trials consumed by Comp Maker / Rotation Builder.
2. Named Major/Minor provider completeness across skills, sets, passives, potions, scribing, and class mastery sources.
3. Gear-set provider completeness beyond the currently reviewed registry.
4. Skill/passive reference entries and combat-rule terminology.
5. Promote repeatedly corroborated research facts into owning canonical contracts only when the runtime actually needs them.

For encounter research, gameplay handling belongs in Field Notes / gameplay-practice evidence unless it is a canonical mechanic fact.
