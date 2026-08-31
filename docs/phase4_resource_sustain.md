# Phase 4 Resource & Sustain Engine

## Status

- **4A Static resource foundation:** complete
- **4B Action costs:** complete for verified static cost behavior
- **4C Recovery timing:** active
- **4D Restoration events:** pending
- **4E Deterministic timeline:** pending
- **4F Sustain result:** pending

## 4B Action-cost closeout

Phase 4 now has a canonical per-resource action-cost path:

1. Resolve the exact saved ability rank/morph and `base_cost`.
2. Resolve the resource identity from `base_mechanic`, including compound costs.
3. Resolve eligible static modifiers with source/resource/skill-line scope intact.
4. Apply flat reductions before percentage reductions.
5. Round the final resource charge with nearest-half-up rounding.
6. Withhold the final result when a required cost source is unresolved.

Verified live behavior includes:

- Breton Magicka Mastery: 7% Magicka ability-cost reduction.
- Light Armor Evocation: current live Xbox/U50 observations are canonical only for the piece counts actually measured. Combat Prayer (base 4590) produced 4269 at 0 Light, 4223 at 1 Light, 4131 at 2 Light, and 3764 at 6 Light on the tested Breton configuration. Unmeasured positive Light counts remain explicit unresolved rather than extrapolated.
- Medium Armor Wind Walker: Echoing Vigor (base 2984) was measured at every 0-7 Medium piece count and exactly matches 2% Stamina ability-cost reduction per equipped Medium piece: 2984, 2924, 2865, 2805, 2745, 2686, 2626, 2566.
- CP160 Truly Superb jewelry cost glyphs feed the same modifier path.
- Live Magicka glyph tests verified flat-before-percentage ordering and nearest-half-up final rounding.
- Compound resource costs are resolved independently per resource.

### Deliberate 4B boundary

Percentage **cost increases** remain represented but are rejected by the final static-cost calculator because their ordering relative to reductions is not yet verified by current live evidence. Conditional, escalating, toggled, and combat-state cost behavior must not be guessed into the static path.

## 4C Recovery timing

The static resource state already carries displayed Health, Magicka, and Stamina Recovery without pretending those values are per-second gains.

The next canonical work is temporal recovery behavior:

1. Verify the current base recovery tick cadence from authoritative/current evidence or live observation.
2. Model tick occurrence separately from displayed recovery magnitude.
3. Model suppression/restriction state explicitly.
4. Verify ordinary Stamina Recovery suppression while blocking, sneaking, and sprinting, plus exceptions/remapping such as Stormweaver's Cavort, before applying those rules generically.
5. Keep flat restores, heavy-attack restores, and external restores out of recovery ticks; those belong to 4D restoration events.

No recovery interval should be hardcoded merely because historical ESO guides commonly state one.