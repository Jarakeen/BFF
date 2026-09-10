# BFF Canonical Endgame Play Practices

This document records how organized ESO endgame is **actually played**, separately from what the game engine merely permits.

It is a human-readable companion to `data/gameplay_policy/endgame_pve.json`. The structured registry is the executable source for BFF consumers; this document explains the intent in plain language.

## Why this layer exists

ESO mechanical truth and raid-practice truth are related, but they are not the same thing.

- **Mechanical truth** answers: *Can the game do this? What does it calculate?*
- **Gameplay-practice truth** answers: *Should this role normally do this in organized endgame?*
- **Encounter context** answers: *Does this specific assignment justify breaking the normal practice?*

BFF must not confuse those layers.

A mechanically legal choice can still be a poor raid recommendation. Conversely, a normally discouraged choice can become correct when an encounter assignment changes the player's range, incoming damage, responsibilities, or access to support.

## Standing rules

1. Gameplay-practice policy sits **above canonical ESO mechanics**. It must never rewrite coefficients, costs, durations, targeting, proc conditions, or other game-engine truth.
2. Practice rules are contextual defaults, not universal laws.
3. Exceptions must be explicit and explainable.
4. Encounter-specific evidence can override a generic role convention when the assignment genuinely changes the conditions that produced the convention.
5. Unknown or disputed practice remains explicit. Do not turn opinion into a hard optimizer constraint without enough confidence.
6. A recommendation should be able to explain whether it came from mechanical legality, normal role practice, encounter necessity, or an exception to normal practice.

## Confidence levels

- **canonical** — effectively universal for the stated organized-endgame context and suitable for strong constraints unless encounter evidence overrides it.
- **strong_practice** — common high-level raid practice and suitable for ranking/penalty behavior; exceptions are expected.
- **observed_practice** — supported by repeated real-play/log/reference evidence but not strong enough to assume universally.
- **experimental** — hypothesis or emerging practice; useful for audit/research, not hard recommendations.

## Initial policy set

### Damage Dealers: personal healing is normally a bar-space cost

In organized endgame trials, a DD normally relies on healer coverage and does **not** reserve a skill-bar slot for a personal heal merely because the skill exists or increases theoretical survivability.

A DD self-heal becomes appropriate when encounter or assignment context makes normal external healing unreliable, for example:

- portal or split-group duty;
- kite or runner duty;
- deliberate range separation from the healer stack;
- a mechanic that repeatedly removes the player from normal healing coverage;
- progression/survival requirements that specifically justify the damage opportunity cost.

**For BFF:** DD build and rotation generators should strongly disfavor redundant personal-heal slots under reliable group healing. They may allow or require one when encounter context establishes a real survival obligation. The explanation must identify the exception rather than pretending the heal is normal DD bar economy.

### Damage Dealers: bar space has opportunity cost

A DD skill slot is not free. Replacing a damage, execute, proc-enabling, buff, debuff, passive-enabling, or rotation-critical ability with utility changes the damage ceiling and sometimes the entire rotation.

**For BFF:** candidate ranking must score the opportunity cost of utility rather than treating every legal skill as an independent bonus.

### Light-attack weaving: LA and skill share the normal cadence window

Normal endgame rotations do not treat a light attack as a separate full one-second action between skill casts. Players weave: the light attack is fired and then animation-cancelled into the skill so the pair belongs to the same normal skill-cadence window.

That does **not** mean the light attack disappears from the combat model. It still matters as its own event for damage, enchant/proc triggers, Ultimate generation, sets, passives, and performance analysis.

**For BFF:** keep `LIGHT_ATTACK` as an explicit combat event, but associate a woven light attack with its skill window. A standard `light attack + skill` weave must not advance the rotation clock by two full one-second slots. Deliberately unpaired attacks, missed weaves, heavy attacks, channels, waits, mechanics, or other timing exceptions remain explicit.

### Healers: raw healing output is not the whole job

Organized endgame healers are not optimized by maximizing HPS or ending Magicka in isolation. Their job includes reliable healing coverage, support buffs/debuffs, set obligations, mechanic preparation, positioning/range, sustain reserve, and emergency response capacity.

**For BFF:** healer optimization should satisfy required healing and safety constraints while also valuing support contribution and mechanic readiness. Excess overhealing is not automatically better.

### Healers: the two healer assignments are not automatically interchangeable

Two healer slots in a trial can carry materially different gear, buff, debuff, positioning, group-coverage, and mechanic responsibilities.

**For BFF:** Team Builder and Rotation Builder should reason about healer assignments, not only the generic `healer` role label.

### Tanks: surviving is necessary but not sufficient

Organized endgame tanks are expected to survive while also maintaining encounter control, positioning, debuffs, support sets/effects, resource management, and assignment-specific utility.

**For BFF:** tank optimization must not rank a selfishly durable build above a sufficiently durable build that better satisfies required group-support and encounter obligations unless the encounter's survival threshold genuinely demands it.

### Encounter assignments can override generic role conventions

Role conventions describe the normal case. Encounter assignments can change the player's actual obligations.

Examples include isolation, portals, kiting, add control, interrupt duty, ranged positioning, special mitigation checks, burst-heal checks, or group splits.

**For BFF:** the decision order is:

1. establish canonical mechanical legality;
2. apply normal role/content practice;
3. apply encounter and assignment context;
4. permit an override only when the context changes the relevant obligation;
5. explain the override and its opportunity cost.

## Intended consumers

This policy layer is shared by:

- Extreme Builder;
- Rotation Builder;
- Comp Maker / Team Builder;
- Team Optimization;
- provider / workload evaluation;
- Performance / Raid Review;
- encounter assignment logic;
- future build recommendation surfaces.

Consumers may use a policy differently. For example, Extreme Builder may expose both unconstrained mechanical maxima and practice-constrained maxima, while Rotation Builder may use the same policy to remove or penalize inappropriate candidates. They must not invent parallel copies of the rule.

## Maintenance rule

When practical ESO knowledge materially affects what BFF should recommend, rank, penalize, require, or explain, add it here **and** to the structured registry when it is ready for executable use.

Good entries answer:

- What is normal in organized play?
- Why is it normal?
- What is the cost of ignoring it?
- What exceptions are legitimate?
- Which BFF systems should consume the rule?
- How confident are we?

Do not use this file for raw coefficients or game-engine mechanics. Those belong in canonical mechanics/data. Do not use `GAME_MECHANICS_FIELD_NOTES.md` as the executable policy registry; field notes preserve discoveries, while this layer governs recommendation behavior.
