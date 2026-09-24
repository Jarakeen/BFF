# Performance Mode U50 raid comp — shared FoundryDock preset

Status: working raid-comp draft captured 2026-09-24.

This document is the human-readable companion to `data/build_templates.json`.
The templates are intentionally shared rather than owned by one profile, so either
Jarakeen or Rylo can apply the relevant template to one of their characters from
Builds → Templates. Applying a template creates/updates the destination build only;
it does not replace `foundrydock.db`, player identity, character progression, team
membership, or unrelated builds.

## Raid-wide construction rules

- DD armor target: **1 Light / 6 Medium**.
- DD back bar: **Perfected Merciless Charge Greatsword**, driven by **Stampede**.
- One tank must own the **Infused Crusher Ice Staff** assignment.
- Major Vulnerability is intentionally owned by **Spithis / Glacial Colossus** after
  Rik moved from Archdruid to Roksa.
- Mastery names are preserved in template notes. Canonical Class Mastery ability IDs
  are not guessed into the shared template payload; the build should resolve/select
  them through the app's canonical mastery data before being marked raid-ready.

## Tanks

### Rik — Sorcerer Tank

**Gear:** Roksa the Warped / Xoryn's Masterpiece / Pearlescent Ward

**Class Mastery:** Calculated Defense / Sphere of Influence

**Front — Sword & Board**

Goading Throw | Bound Aegis | Boundless Storm | Resolving Vigor | Pierce Armor / Flex | Atronach

**Back — Frost Staff**

Chilling Trample | Elemental Blockade | Elemental Susceptibility | Leashing Soul | Hardened Ward | Aggressive Horn / Flex Ultimate

### Spithis — Necromancer Tank

**Gear:** Saxhleel Champion / Nazaray / Lucent Echoes

**Class Mastery:** Veil's Forfeit / Malevolent Promise

**Front — Sword & Board**

Pierce Armor | Ruinous Scythe | Spirit Guardian | Necrotic Potency | Agony Totem | Ravenous Goliath / Flex Defensive Ultimate

**Back — Frost Staff**

Destructive Clench | Elemental Blockade | Beckoning Armor | Resolving Vigor | Unnerving Boneyard | Glacial Colossus / Aggressive Horn

## Healers

### Mrs Poe — Arcanist Healer

**Gear:** Symphony of Blades / Pillager's Profit / Powerful Assault

**Class Mastery:** Ink-Scribe's Verve / Erudite's Rigor

**Front**

Combat Prayer | Illustrious Healing | Chakram Shields | Radiating Regeneration | Curative Surge | Glyphic of the Tides

**Back**

Elemental Blockade | Energy Orb | Echoing Vigor | Rune of the Colorless Pool | Zenas' Empowering Disc / Flex | Aggressive Horn

### Jarakeen — Warden Healer

**Gear:** Ozezan the Inferno / Serpent's Disdain / Master Architect

**Class Mastery:** Tundra's Maw / Bountiful Harvest

**Front**

Combat Prayer | Radiating Regeneration | Budding Seeds | Illustrious Healing | Energy Orb | Wild Guardian / Bear

**Back**

Elemental Blockade | Echoing Vigor | Flex / Winter's Revenge | Expansive Frost Cloak | Blood Altar | Aggressive Horn / Barrier / Flex Ultimate

## DDs

### Necromancer DD core — Rylo / Tunz / Clus

**Core gear:** Corpseburster / Perfected Slivers of the Null Arca

- Rylo also uses **Signet**.
- Tunz / Clus use the assigned **medium Slimecraw one-piece** where applicable.

**Class Mastery:** Nothing Wasted / Cycle Unending

**Front**

Blighted Blastbones | Avid Boneyard | Detonating Siphon | Venom Skull | Banner | Flawless Dawnbreaker

**Back**

Stampede | Carve | Trap Beast | Skeletal Archer | Banner | Onslaught

**Banner:** Shock / Class Mastery / Heroism

### Aces — Nightblade / Werewolf DD

**Gear:** Savage Werewolf / Perfected Slivers of the Null Arca

**Class Mastery:** An Eye for Exploitation / Above and Beyond

**Front**

Surprise Attack | Ambush | Killer's Blade | Reaper's Mark | Relentless Focus | Werewolf Berserker

**Back**

Stampede | Carve | Dark Shade | Debilitate | Siphoning Attacks | Soul Harvest

### Pippin — Nightblade DD

**Gear:** Perfected Slivers of the Null Arca / Aegis Caller / medium Slimecraw

**Class Mastery:** An Eye for Exploitation / Above and Beyond

**Front**

Surprise Attack | Relentless Focus | Killer's Blade | Debilitate | Shadowy Disguise | Incapacitating Strike

**Back**

Stampede | Siphoning Attacks | Dark Shade | Trap Beast | Simmering Frenzy | Onslaught

### Jaded — Arcanist DD

**Gear:** Morag Tong / War Machine / medium Slimecraw

**Class Mastery:** Abyssal Emergence / Unbound Potential

**Front**

Cephaliarch's Flail | Pragmatic Fatecarver | Camouflaged Hunter | Quick Cloak | Barbed Trap | Flawless Dawnbreaker

**Back**

Inspired Scholarship | Stampede | Carve | Fulminating Rune | Scalding Rune | The Languid Eye

### Cobbleston — Dragonknight Z'enKosh

**Gear:** Z'en's Redress / Roar of Alkosh / Spaulder of Ruin

**Class Mastery:** Lead from the Front / Wildfire Embers

**Front**

Molten Whip | Venomous Claw | Flames of Oblivion | Magma Fist | Sundering Knife | Flawless Dawnbreaker

**Back**

Stampede | Carve | Engulfing Flames | Eruption | Barbed Trap | Standard of Might

Magma Fist owns Heat Shock. Sundering Knife owns Off Balance.

**Coverage warning:** the current Cobble bar does not contain an obvious Draconic
Power cast. Do not mark the DK group **Minor Brutality** passive covered merely
because a Dragonknight is present; coverage requires the passive's activation
condition to be met in the actual bar/rotation.

### Templar DD

**Gear:** Aetheric Lancer / Perfected Slivers of the Null Arca / medium Slimecraw

**Class Mastery:** Judgment's Brand / Bright Harbinger

**Front**

Biting Jabs | Power of the Light | Radiant Glory | Barbed Trap | Camouflaged Hunter | Flawless Dawnbreaker

**Back**

Stampede | Restoring Focus | Solar Barrage | Blazing Spear | Ritual of Retribution | Onslaught

## Deliberate raid coverage

The working plan deliberately assigns or expects:

- Major Courage — Aces / Werewolf package
- Minor Courage — Mrs Poe / Zenas' Empowering Disc when slotted
- Major Berserk — Rik / Atronach synergy
- Minor Berserk — Combat Prayer
- Major Slayer — Jarakeen / Master Architect and Jaded / War Machine sides
- Major Force — Saxhleel, Ink-Scribe support, and Horn windows
- Minor Force — Trap Beast users
- Minor Savagery — Nightblade Hemorrhage passive
- Minor Prophecy — Sorcerer class passive
- Minor Sorcery — Templar class passive
- Minor Toughness — Warden healing
- Major Heroism — Jarakeen / Bountiful Harvest
- Major Vulnerability — Spithis / Glacial Colossus
- Minor Vulnerability — Rune of the Colorless Pool / Unnerving Boneyard coverage
- Major Brittle — Jarakeen / Tundra's Maw from Chilled
- Minor Brittle — Mrs Poe / Rune of the Colorless Pool
- Major Resolve — Jarakeen / Expansive Frost Cloak
- Major and Minor Breach — tank taunt/debuff package
- Alkosh — Cobble
- Z'en — Cobble
- Heat Shock — Cobble / Magma Fist
- Off Balance — Cobble / Sundering Knife
- Morag Tong — Jaded
- Pillager / Symphony / Powerful Assault — Mrs Poe
- Ozezan / Serpent's Disdain / Master Architect — Jarakeen
- Xoryn / Pearlescent Ward / Roksa — Rik
- Saxhleel / Nazaray / Lucent — Spithis

## Crit and penetration working state

For planning purposes, the shared raid-side Critical Damage package is:

- base 50%
- Major Force +20%
- Minor Force +10%
- Minor Brittle +10%
- Lucent Echoes +11%

That is **101% before personal DD sources**. During Major Brittle windows the
raid-side package reaches **121% before personal sources**, so individual DD
crit-damage bonuses must be checked against the cap rather than blindly adding
more group crit.

For penetration, the intended support package is Major Breach + Minor Breach +
Alkosh + one **Infused Crusher** tank, while every DD wears **one Light piece**.
Treat exact cap status as uptime-dependent: Alkosh, Crusher, Breach, and the
personal Light-armor contribution all have to be present in the actual combat
state before FoundryDock calls the target capped.

## App behavior

The bundled templates are shared catalog entries. They are not bound to Jarakeen
or Rylo. Either profile can:

1. open **Builds → Templates**;
2. choose the desired PM U50 template;
3. use **Use Template For…**;
4. select one of that profile's compatible characters.

The destination character keeps its own player/character identity and progression.
The template supplies the planned package and bars, then remains reviewable before
the build is marked raid-ready.
