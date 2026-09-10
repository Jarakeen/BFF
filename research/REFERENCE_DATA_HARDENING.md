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

## First completed research family: core status effects

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

## Missing-value presentation rule

Bare `Not modeled` should not survive the normal Combat Reference loading path.

Examples:

- `Damage type: Unknown — canonical encounter record has no reviewed damage type yet.`
- `Interruptible: Unknown — interruptibility has not yet been reviewed for this mechanic.`
- `Maximum stacks: No stack mechanic is recorded for this effect.`
- `Tick interval: No periodic tick cadence is recorded; this may be an instant effect or a remaining evidence gap.`

This wording is deliberately honest about what is known without pretending that every absent database cell represents the same kind of uncertainty.

## Next research families

1. Shared passive -> named-effect provider authority.
2. Named Major/Minor effect provider completeness and current Update 50/51 version boundaries.
3. Off Balance and other non-status combat effects.
4. Gear-set provider completeness beyond the currently reviewed registry.
5. Encounter mechanics, prioritizing trials used by Comp Maker / Rotation Builder and fields that currently have explicit unresolved states.
6. Skill/passive reference entries and combat-rule terminology.

For encounter research, gameplay handling belongs in Field Notes / gameplay-practice evidence unless it is a canonical mechanic fact.
