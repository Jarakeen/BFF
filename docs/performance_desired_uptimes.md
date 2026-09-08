# BFF Working Uptime Targets

These are **working performance targets**, not canonical ESO mechanics and not universal encounter requirements. They are intended for the Capabilities / Performance Dashboard, Performance Focus, and later tank/DD grading.

The starting calibration comes from user-supplied BTVTools screenshots from a Lokkestiiz hard-mode fight. BFF deliberately converts those examples into rounded internal targets rather than reproducing another tool's presentation verbatim. Encounter mechanics, provider assignment, immunity/downtime, set limits, ultimate economy, target availability, and role responsibility can all change what a good number actually is.

## Initial calibrated targets

| Effect / support job | BFF desired uptime | How to use it |
| --- | ---: | --- |
| Major Berserk | 95% | High-coverage group-buff goal when the player's assignment/build can reasonably maintain it. |
| Major Slayer | 90% | Strong support target for Roaring Opportunist-style group coverage; do not grade an unassigned player. |
| Powerful Assault | 90–95% | Treat 90% as solid and 95% as an excellent sustained-support goal rather than demanding a single absolute threshold. |
| Minor Courage | 95% | High-coverage group-support target where the team composition actually provides it. |
| Major Vulnerability | 55% | Windowed/ultimate/set-limited target. Never interpret this like a permanent 95–100% aura. |
| Off Balance | ~30% practical ceiling | Cycle-limited effect. Grade against its realistic opportunity window, not against 100% of the encounter. |

## Important grading rules

1. **Responsibility first.** A player is only graded against an effect when their class, gear, slotted abilities, assignment, or explicit user tracking makes that effect plausibly their job.
2. **Boss-active denominator.** When Boss Immunity is enabled, uptime percentages and targets use boss-active/damageable time where the effect is relevant. When it is disabled, use the full fight.
3. **Windowed effects stay windowed.** Ultimate-driven, proc-limited, cooldown-limited, or cycle-limited effects must be judged against realistic availability rather than a fake 100% expectation.
4. **Observed evidence beats defaults.** Encounter-specific evidence, explicit assignment policy, or a user-defined custom goal overrides these working defaults.
5. **Do not infer missing targets.** Major Force, Major Brittle, Minor Brittle, Crusher, Breach, taunt, defensive buffs, class-specific self-buffs, DoT coverage, potion uptime, and similar metrics still need their own calibrated evidence before receiving authoritative defaults.

## Calibration provenance

The user-supplied BTVTools screenshot set showed, for one Lokkestiiz hard-mode example, reference targets around 96% Major Berserk, 90% Major Slayer, 95% Powerful Assault, 97% Minor Courage, 56% Major Vulnerability, and an Off Balance theoretical maximum near 31.8% for the displayed 7s / 22s cycle. BFF uses those only as calibration evidence and rounds/normalizes them into the working targets above.

## Next additions

As DPS and tank analysis is implemented, extend this note only when supported by reviewed evidence. Priority candidates are:

- taunt / boss-control uptime;
- Major and Minor Breach;
- Crusher;
- Minor Maim;
- Major Resolve and other defensive self-buffs;
- Major Force / War Horn;
- Major Brittle / Minor Brittle;
- class-specific self-buffs;
- DoT uptime and execute-phase coverage;
- potion and ultimate timing;
- incoming-damage / mitigation windows for tanks.
