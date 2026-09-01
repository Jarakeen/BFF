# Phase 5 · Real Build Resolution Closeout

**Status: Complete**

**Closeout date:** 2026-09-01

## Exit statement

Phase 5 is complete when an authoritative saved build can traverse the real ESO database, canonical character-owned progression, static build context, gear/skill/consumable repositories, and `EffectVariant` capability path without silently inventing unsupported mechanics.

That condition is now met.

## Authoritative production validation

The closeout build is **Magrat → DF Healer**.

The saved build resolves through:

- canonical character identity
- character-owned skill-line ownership
- character-owned passive ranks
- character-owned passive Champion Point allocations
- exact purchased racial passive ranks from canonical `skill` / `skill_rank` / `ability` rows
- active-bar gear-set piece counting
- verified gear-set `EffectVariant` mappings
- verified skill `EffectVariant` mappings
- canonical potion effect-family availability
- explicit conditional/temporal boundaries

Final authoritative resolution result:

- resolved `EffectVariant` identities: **11**
- genuine unresolved items: **0**
- full regression suite: **1619 passed**

## Canonical racial progression

The historical aggregate `race_stat` shortcut is no longer authoritative for Phase 5 canonical callers.

Purchased racial passive effects are resolved from the character's recorded passive rank and that exact canonical rank's ability description in `eso.db`.

For Breton validation this includes source-backed rank handling for:

- `Gift of Magnus`
- `Spell Attunement`
- `Magicka Mastery`
- `Opportunist`

Unconditional standing-stat portions are applied only when the passive rank is actually purchased. Conditional or unsupported portions remain explicit boundaries rather than being treated as permanently active.

## Champion Point resolution boundary

The Phase 5 audit no longer treats every unmapped Champion Point tooltip as a genuine build-resolution defect.

Purchased CP stars are separated into:

- standing/static math that the current stat model resolves
- non-combat utility outside the combat capability audit
- explicit deferred combat models such as typed mitigation, status-effect chance, movement, resurrection, Bash/Break Free/Sprint/Roll Dodge utility channels, and PvP detection

For the authoritative DF Healer sample, this classification leaves **0 genuinely unmapped Champion Point items**.

## Potion semantics

A selected potion proves **availability**, not activation or standing uptime.

The saved `spell power` legacy label resolves to the canonical U50 effect family:

- Restore Magicka
- Increase Spell Power
- Spell Critical

Two source-backed equivalent U50 reagent formulas are available for this family. Phase 5 does not choose one arbitrarily.

Potion `EffectVariant` entries remain `CONSUMABLE` effects with explicit `potion_use` trigger semantics.

## Gear / skill capability evidence

The authoritative real-build resolution matrix proves the current production path across both bars.

Examples include:

- `Spaulder of Ruin` → conditional group Weapon/Spell Damage proc
- `Serpent's Disdain` → status-effect duration increase
- `Master Architect` → conditional Major Slayer proc
- `Combat Prayer` → Berserk + Minor Resolve
- `Expansive Frost Cloak` → Major Resolve
- `Overflowing Altar` → conditional Minor Lifesteal
- `Aggressive Horn` → Force
- selected spell-power potion → three consumable availability effects

Skills or set piece counts with no verified support-effect mapping are reported as such and are not fabricated into effects.

## Explicit deferred mechanics

The following remain intentionally outside the Phase 5 standing capability model and are carried forward:

- potion activation / uptime scheduling
- conditional racial bonus activation, such as Spell Attunement's doubled resistance clause
- racial ability-cost reductions in the standing-stat capability layer
- status-effect chance modeling
- typed incoming-damage mitigation
- attacker-type mitigation
- attack-damage-type conditional offensive modifiers
- movement-speed and movement-state modifiers
- Bash / Break Free / Sprint / Roll Dodge utility cost channels
- incoming status-effect duration
- resurrection-state modifiers
- stealth-detection / PvP utility
- Charged status-effect chance behavior
- conditional proc timing / cooldown scheduling

These are not counted as genuine unresolved Phase 5 defects because the engine identifies their boundary explicitly and does not assume their value or uptime.

## Template/sample build policy

`YOUR TANK BUILD` remains a diagnostic/template row rather than authoritative closeout evidence.

It is excluded from the default `--all` Phase 5 closeout total because its persisted selections include stale/sample values that were not intentionally configured as a trusted production build.

The row is **not deleted or normalized automatically**. It remains available for deliberate stress testing with:

```powershell
python tools\audit_phase5_resolution_matrix.py --all --include-templates
```

This preserves evidence without allowing placeholder data to redefine production correctness.

## Closeout commands

Targeted template classifier test:

```powershell
pytest -q minmax/tests/test_phase5_resolution_matrix_templates.py
```

Authoritative roster audit:

```powershell
python tools\audit_phase5_resolution_matrix.py --all
```

Full regression suite:

```powershell
pytest -q
```

Final reported results:

- template classifier tests: **3 passed**
- full regression suite: **1619 passed**
- authoritative roster genuine unresolved: **0**
- excluded diagnostic/template builds: `YOUR TANK BUILD`

## Exit criteria

- [x] canonical saved Character → Build resolution works in production
- [x] character-owned progression is consumed directly
- [x] purchased racial passive ranks are honored instead of aggregate race assumptions
- [x] real gear, skill, and potion capability paths resolve through shared repositories / `EffectVariant`
- [x] conditional and temporal mechanics remain explicit
- [x] unsupported mechanics fail closed rather than being guessed
- [x] authoritative saved-build audit reports zero genuine unresolved items
- [x] template/sample rows are separated from production closeout evidence
- [x] full regression suite is green

**Phase 5 exit criteria met on 2026-09-01.**
